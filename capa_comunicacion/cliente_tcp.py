"""
Cliente TCP no-bloqueante para comunicación con robot ABB.
Maneja reconexión automática, cola de envío y recepción en hilo dedicado.
"""

import socket
import time
import queue

from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from capa_logs import obtener_logger
from nucleo.modelos import EstadoConexion

logger = obtener_logger("tcp")


class ClienteTCP(QThread):
    """
    Cliente TCP en hilo Qt dedicado.

    Señales:
        conexion_cambiada(EstadoConexion): Cambio de estado de conexión.
        mensaje_enviado(str): Dato enviado exitosamente.
        mensaje_recibido(str): Respuesta recibida del robot.
        error_conexion(str): Error de comunicación.
    """

    conexion_cambiada = pyqtSignal(object)
    mensaje_enviado = pyqtSignal(str)
    mensaje_recibido = pyqtSignal(str)
    error_conexion = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._socket: socket.socket | None = None
        self._mutex = QMutex()
        self._ejecutando = False
        self._conectado = False
        self._ip = ""
        self._puerto = 0
        self._cola_envio: queue.Queue = queue.Queue()
        self._reconexion_auto = True
        self._timeout_s = 5
        self._estado = EstadoConexion.DESCONECTADO

        # Backoff para reconexión
        self._backoff_base = 1.0
        self._backoff_max = 30.0
        self._backoff_actual = 1.0

    # ───────────────────────────────────────────────────────
    # Propiedades
    # ───────────────────────────────────────────────────────

    @property
    def esta_conectado(self) -> bool:
        return self._conectado

    @property
    def estado(self) -> EstadoConexion:
        return self._estado

    @property
    def direccion(self) -> str:
        return f"{self._ip}:{self._puerto}" if self._ip else "N/A"

    # ───────────────────────────────────────────────────────
    # Control
    # ───────────────────────────────────────────────────────

    def configurar(self, ip: str, puerto: int, reconexion: bool = True, timeout: int = 5):
        """Configura los parámetros de conexión."""
        self._ip = ip
        self._puerto = puerto
        self._reconexion_auto = reconexion
        self._timeout_s = timeout

    def conectar(self, ip: str = None, puerto: int = None):
        """Inicia la conexión en el hilo."""
        if ip:
            self._ip = ip
        if puerto:
            self._puerto = puerto

        if not self._ip or not self._puerto:
            self.error_conexion.emit("IP o puerto no configurados")
            return

        if self.isRunning():
            logger.warning("El hilo TCP ya está corriendo")
            return

        self._ejecutando = True
        self._backoff_actual = self._backoff_base
        self.start()

    def desconectar(self):
        """Solicita desconexión limpia."""
        self._ejecutando = False
        self._reconexion_auto = False
        self._cerrar_socket()

    def enviar(self, datos: str):
        """Encola datos para envío (thread-safe)."""
        if not self._conectado:
            logger.warning("No conectado — datos descartados")
            return
        self._cola_envio.put(datos)

    def enviar_inmediato(self, datos: str) -> bool:
        """Envía datos inmediatamente (bypass de cola)."""
        return self._enviar_raw(datos)

    # ───────────────────────────────────────────────────────
    # Hilo principal
    # ───────────────────────────────────────────────────────

    def run(self):
        """Bucle principal del hilo TCP."""
        logger.info(f"Hilo TCP iniciado — destino: {self._ip}:{self._puerto}")

        while self._ejecutando:
            # Fase 1: Conectar
            if not self._conectado:
                exito = self._intentar_conexion()
                if not exito:
                    if not self._reconexion_auto or not self._ejecutando:
                        break
                    logger.info(f"Reintentando en {self._backoff_actual:.0f}s...")
                    self._cambiar_estado(EstadoConexion.RECONECTANDO)
                    # Esperar con verificación de cancelación
                    for _ in range(int(self._backoff_actual * 10)):
                        if not self._ejecutando:
                            break
                        time.sleep(0.1)
                    self._backoff_actual = min(self._backoff_actual * 2, self._backoff_max)
                    continue

            # Fase 2: Procesar cola de envío y recepción
            self._procesar_comunicacion()

        self._cerrar_socket()
        self._cambiar_estado(EstadoConexion.DESCONECTADO)
        logger.info("Hilo TCP terminado")

    def _intentar_conexion(self) -> bool:
        """Intenta establecer conexión TCP."""
        self._cambiar_estado(EstadoConexion.CONECTANDO)
        logger.info(f"Conectando a {self._ip}:{self._puerto}...")

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self._timeout_s)
            self._socket.connect((self._ip, self._puerto))

            # Recibir saludo inicial del ABB (si existe)
            try:
                self._socket.settimeout(2.0)
                saludo = self._socket.recv(1024)
                if saludo:
                    mensaje = saludo.decode("utf-8", errors="replace").strip()
                    logger.info(f"Saludo del robot: '{mensaje}'")
                    self.mensaje_recibido.emit(mensaje)
            except socket.timeout:
                pass  # No hay saludo, es normal

            # Poner socket en modo no-bloqueante para recv
            self._socket.settimeout(0.1)

            self._conectado = True
            self._backoff_actual = self._backoff_base
            self._cambiar_estado(EstadoConexion.CONECTADO)
            logger.info(f"Conectado exitosamente a {self._ip}:{self._puerto}")
            return True

        except Exception as e:
            error = f"Error de conexión: {e}"
            logger.warning(error)
            self.error_conexion.emit(error)
            self._cambiar_estado(EstadoConexion.ERROR)
            self._cerrar_socket()
            return False

    def _procesar_comunicacion(self):
        """Procesa envíos pendientes y recibe datos."""
        # Enviar datos de la cola
        while not self._cola_envio.empty() and self._conectado:
            try:
                datos = self._cola_envio.get_nowait()
                if not self._enviar_raw(datos):
                    break
            except queue.Empty:
                break

        # Recibir datos
        if self._conectado:
            self._recibir()

        # Pequeña pausa para no saturar CPU
        time.sleep(0.01)

    def _enviar_raw(self, datos: str) -> bool:
        """Envía datos raw por el socket."""
        with QMutexLocker(self._mutex):
            if self._socket is None or not self._conectado:
                return False
            try:
                self._socket.sendall(datos.encode("utf-8"))
                logger.debug(f"Enviado → {datos.strip()}")
                self.mensaje_enviado.emit(datos)
                return True
            except Exception as e:
                logger.error(f"Error al enviar: {e}")
                self._conectado = False
                self.error_conexion.emit(str(e))
                return False

    def _recibir(self):
        """Intenta recibir datos del robot."""
        with QMutexLocker(self._mutex):
            if self._socket is None:
                return
            try:
                datos = self._socket.recv(1024)
                if datos:
                    mensaje = datos.decode("utf-8", errors="replace").strip()
                    if mensaje:
                        logger.debug(f"Recibido ← {mensaje}")
                        self.mensaje_recibido.emit(mensaje)
                elif datos == b"":
                    # Conexión cerrada por el otro lado
                    logger.warning("El robot cerró la conexión")
                    self._conectado = False
            except socket.timeout:
                pass  # Normal, no hay datos
            except Exception as e:
                if self._ejecutando:
                    logger.error(f"Error al recibir: {e}")
                    self._conectado = False

    def _cerrar_socket(self):
        """Cierra el socket de forma segura."""
        with QMutexLocker(self._mutex):
            self._conectado = False
            if self._socket is not None:
                try:
                    self._socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None

    def _cambiar_estado(self, nuevo: EstadoConexion):
        """Actualiza y emite el estado de conexión."""
        self._estado = nuevo
        self.conexion_cambiada.emit(nuevo)
