"""
Servicio de captura de cámara en hilo dedicado Qt.
Emite frames como señales para no bloquear la interfaz.
"""

import time

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from capa_logs import obtener_logger

logger = obtener_logger("camara")


class ServicioCamara(QThread):
    """
    Captura frames de cámara en un hilo Qt dedicado.

    Señales:
        frame_listo(np.ndarray): Frame BGR capturado.
        fps_actualizado(float): FPS actual de captura.
        error_camara(str): Error de cámara.
        camara_detenida(): La cámara se detuvo.
    """

    frame_listo = pyqtSignal(object)
    fps_actualizado = pyqtSignal(float)
    error_camara = pyqtSignal(str)
    camara_detenida = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._captura: cv2.VideoCapture | None = None
        self._mutex = QMutex()
        self._ejecutando = False
        self._fuente_camara: int | str = 0  # Índice local o URL IP Webcam
        self._resolucion = (1280, 720)
        self._reintentos_max = 5

        # Métricas FPS
        self._contador_frames = 0
        self._tiempo_inicio_fps = 0.0
        self._fps_actual = 0.0

    # ───────────────────────────────────────────────────────
    # Configuración
    # ───────────────────────────────────────────────────────

    def configurar(self, fuente: int | str, resolucion: tuple[int, int] = (1280, 720)):
        """Configura la cámara antes de iniciar.

        Args:
            fuente: Índice entero para cámara local, o URL string para IP Webcam
                    (ej: 'http://192.168.1.11:8080/video').
            resolucion: Resolución deseada (solo aplica a cámaras locales).
        """
        self._fuente_camara = fuente
        self._resolucion = resolucion

    # ───────────────────────────────────────────────────────
    # Control
    # ───────────────────────────────────────────────────────

    def iniciar_captura(self):
        """Inicia la captura de cámara."""
        if self.isRunning():
            logger.warning("La cámara ya está en ejecución")
            return
        self._ejecutando = True
        self.start()

    def detener_captura(self):
        """Solicita detener la captura de forma segura."""
        self._ejecutando = False

    @property
    def esta_activa(self) -> bool:
        """Retorna True si la cámara está capturando."""
        return self._ejecutando and self.isRunning()

    @property
    def fps(self) -> float:
        """FPS actual de captura."""
        return self._fps_actual

    # ───────────────────────────────────────────────────────
    # Hilo principal
    # ───────────────────────────────────────────────────────

    def run(self):
        """Bucle principal de captura (ejecuta en hilo)."""
        es_url = isinstance(self._fuente_camara, str)
        etiqueta = self._fuente_camara if es_url else f"índice={self._fuente_camara}"
        logger.info(f"Iniciando cámara [{etiqueta}, resolución={self._resolucion}]")

        self._tiempo_inicio_fps = time.perf_counter()
        self._contador_frames = 0

        if es_url:
            self._capturar_stream_mjpeg(self._fuente_camara)
        else:
            if not self._abrir_camara():
                self._ejecutando = False
                self.camara_detenida.emit()
                return
            self._capturar_local()

        self._ejecutando = False
        self.camara_detenida.emit()
        logger.info("Cámara detenida")

    def _capturar_stream_mjpeg(self, url: str):
        import urllib.request
        import numpy as np

        logger.info(f"Conectando a stream MJPEG nativo: {url}")
        try:
            req = urllib.request.Request(url)
            stream = urllib.request.urlopen(req, timeout=5)
            bytes_buffer = b''
            while self._ejecutando:
                try:
                    chunk = stream.read(4096)
                    if not chunk:
                        break
                    bytes_buffer += chunk
                    
                    # Buscar marcadores JPEG (Inicio: FF D8, Fin: FF D9)
                    a = bytes_buffer.find(b'\xff\xd8')
                    b = bytes_buffer.find(b'\xff\xd9')
                    
                    if a != -1 and b != -1:
                        jpg = bytes_buffer[a:b+2]
                        bytes_buffer = bytes_buffer[b+2:]
                        
                        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            self._contador_frames += 1
                            self._actualizar_fps()
                            self.frame_listo.emit(frame)
                except Exception as e:
                    logger.warning(f"Error leyendo frame MJPEG: {e}")
                    break
        except Exception as e:
            error_msg = f"Error conectando al stream IP: {e}"
            logger.error(error_msg)
            self.error_camara.emit(error_msg)

    def _capturar_local(self):
        reintentos = 0
        while self._ejecutando:
            with QMutexLocker(self._mutex):
                if self._captura is None or not self._captura.isOpened():
                    break
                ret, frame = self._captura.read()

            if not ret or frame is None:
                reintentos += 1
                logger.warning(f"Frame fallido (reintento {reintentos}/{self._reintentos_max})")
                if reintentos >= self._reintentos_max:
                    self.error_camara.emit("Cámara desconectada — demasiados frames fallidos")
                    break
                import time
                time.sleep(0.1)
                continue

            reintentos = 0
            self._contador_frames += 1
            self._actualizar_fps()
            self.frame_listo.emit(frame)

        self._cerrar_camara()

    # ───────────────────────────────────────────────────────
    # Métodos internos
    # ───────────────────────────────────────────────────────

    def _abrir_camara(self) -> bool:
        """Abre la cámara local y configura resolución."""
        try:
            fuente = self._fuente_camara

            # Cámara local — intentar DirectShow primero
            self._captura = cv2.VideoCapture(fuente, cv2.CAP_DSHOW)
            if not self._captura.isOpened():
                # Reintentar sin DirectShow
                self._captura = cv2.VideoCapture(fuente)

            if not self._captura.isOpened():
                error = f"No se pudo abrir la cámara {fuente}"
                logger.error(error)
                self.error_camara.emit(error)
                return False

            # Buffer mínimo para reducir latencia en local
            self._captura.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Configurar resolución para cámara local
            self._captura.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolucion[0])
            self._captura.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolucion[1])
            ancho_real = int(self._captura.get(cv2.CAP_PROP_FRAME_WIDTH))
            alto_real = int(self._captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"Cámara local abierta: {ancho_real}x{alto_real}")

            return True

        except Exception as e:
            error = f"Error al abrir cámara: {e}"
            logger.error(error)
            self.error_camara.emit(error)
            return False

    def _cerrar_camara(self):
        """Libera la cámara de forma segura."""
        with QMutexLocker(self._mutex):
            if self._captura is not None:
                try:
                    self._captura.release()
                except Exception:
                    pass
                self._captura = None
                logger.info("Recurso de cámara liberado")

    def _actualizar_fps(self):
        """Calcula y emite FPS cada segundo."""
        ahora = time.perf_counter()
        delta = ahora - self._tiempo_inicio_fps
        if delta >= 1.0:
            self._fps_actual = self._contador_frames / delta
            self.fps_actualizado.emit(self._fps_actual)
            self._contador_frames = 0
            self._tiempo_inicio_fps = ahora
