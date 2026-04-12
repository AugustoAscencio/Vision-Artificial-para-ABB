"""
Simulador de robot ABB para pruebas sin hardware real.
Servidor TCP que imita el comportamiento básico del controlador ABB.
"""

import socket
import threading
import time

from capa_logs import obtener_logger

logger = obtener_logger("simulador")


class SimuladorRobot:
    """
    Servidor TCP que simula un controlador ABB.

    - Acepta una conexión entrante
    - Envía un saludo inicial (como hace ABB)
    - Imprime los datos recibidos en el log
    - Envía ACK tras cada recepción

    Útil para desarrollo y pruebas sin robot físico.
    """

    def __init__(self, ip: str = "127.0.0.1", puerto: int = 8000):
        self._ip = ip
        self._puerto = puerto
        self._servidor: socket.socket | None = None
        self._cliente: socket.socket | None = None
        self._hilo: threading.Thread | None = None
        self._ejecutando = False
        self._mensajes_recibidos: list[str] = []

    @property
    def esta_activo(self) -> bool:
        return self._ejecutando

    @property
    def mensajes(self) -> list[str]:
        return self._mensajes_recibidos.copy()

    def iniciar(self):
        """Inicia el servidor simulador en un hilo."""
        if self._ejecutando:
            logger.warning("Simulador ya está corriendo")
            return

        self._ejecutando = True
        self._hilo = threading.Thread(target=self._bucle_servidor, daemon=True)
        self._hilo.start()
        logger.info(f"Simulador ABB iniciado en {self._ip}:{self._puerto}")

    def detener(self):
        """Detiene el servidor simulador."""
        self._ejecutando = False
        # Cerrar cliente
        if self._cliente:
            try:
                self._cliente.close()
            except Exception:
                pass
        # Cerrar servidor
        if self._servidor:
            try:
                self._servidor.close()
            except Exception:
                pass
        logger.info("Simulador ABB detenido")

    def _bucle_servidor(self):
        """Bucle principal del servidor simulado."""
        try:
            self._servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._servidor.settimeout(1.0)
            self._servidor.bind((self._ip, self._puerto))
            self._servidor.listen(1)
            logger.info(f"Simulador escuchando en {self._ip}:{self._puerto}")

            while self._ejecutando:
                try:
                    self._cliente, addr = self._servidor.accept()
                    logger.info(f"Simulador: cliente conectado desde {addr}")

                    # Enviar saludo (como hace el ABB real)
                    self._cliente.send(b" ")
                    self._cliente.settimeout(0.5)

                    self._atender_cliente()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self._ejecutando:
                        logger.error(f"Simulador — error aceptando: {e}")

        except Exception as e:
            logger.error(f"Simulador — error servidor: {e}")
        finally:
            if self._servidor:
                try:
                    self._servidor.close()
                except Exception:
                    pass

    def _atender_cliente(self):
        """Recibe datos del cliente y responde con ACK."""
        while self._ejecutando and self._cliente:
            try:
                datos = self._cliente.recv(1024)
                if not datos:
                    logger.info("Simulador: cliente desconectado")
                    break

                mensaje = datos.decode("utf-8", errors="replace").strip()
                if mensaje:
                    self._mensajes_recibidos.append(mensaje)
                    logger.info(f"Simulador recibió: '{mensaje}'")

                    # Parsear y mostrar las coordenadas
                    self._mostrar_datos_parseados(mensaje)

                    # Enviar ACK
                    try:
                        self._cliente.send(b"ACK\n")
                    except Exception:
                        break

            except socket.timeout:
                continue
            except Exception as e:
                if self._ejecutando:
                    logger.warning(f"Simulador — error recv: {e}")
                break

    def _mostrar_datos_parseados(self, mensaje: str):
        """Parsea e imprime los datos recibidos de manera legible."""
        if mensaje.startswith("N:"):
            # Múltiples objetos
            partes = mensaje.split("|")
            n = partes[0].split(":")[1] if ":" in partes[0] else "?"
            logger.info(f"  → {n} objetos recibidos:")
            for parte in partes[1:]:
                logger.info(f"    {parte}")
        elif mensaje.startswith("X:"):
            # Un solo objeto
            logger.info(f"  → Objeto: {mensaje}")
        else:
            logger.info(f"  → Datos: {mensaje}")
