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
        self._indice_camara = 0
        self._resolucion = (1280, 720)
        self._reintentos_max = 5

        # Métricas FPS
        self._contador_frames = 0
        self._tiempo_inicio_fps = 0.0
        self._fps_actual = 0.0

    # ───────────────────────────────────────────────────────
    # Configuración
    # ───────────────────────────────────────────────────────

    def configurar(self, indice: int, resolucion: tuple[int, int] = (1280, 720)):
        """Configura la cámara antes de iniciar."""
        self._indice_camara = indice
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
        logger.info(f"Iniciando cámara [índice={self._indice_camara}, "
                     f"resolución={self._resolucion}]")

        # Abrir cámara
        if not self._abrir_camara():
            self._ejecutando = False
            self.camara_detenida.emit()
            return

        self._tiempo_inicio_fps = time.perf_counter()
        self._contador_frames = 0
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
                time.sleep(0.1)
                continue

            reintentos = 0
            self._contador_frames += 1
            self._actualizar_fps()

            # Emitir frame
            self.frame_listo.emit(frame)

        # Limpiar
        self._cerrar_camara()
        self._ejecutando = False
        self.camara_detenida.emit()
        logger.info("Cámara detenida")

    # ───────────────────────────────────────────────────────
    # Métodos internos
    # ───────────────────────────────────────────────────────

    def _abrir_camara(self) -> bool:
        """Abre la cámara y configura resolución."""
        try:
            self._captura = cv2.VideoCapture(self._indice_camara, cv2.CAP_DSHOW)
            if not self._captura.isOpened():
                # Reintentar sin DirectShow
                self._captura = cv2.VideoCapture(self._indice_camara)

            if not self._captura.isOpened():
                error = f"No se pudo abrir la cámara {self._indice_camara}"
                logger.error(error)
                self.error_camara.emit(error)
                return False

            # Configurar resolución
            self._captura.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolucion[0])
            self._captura.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolucion[1])
            self._captura.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            ancho_real = int(self._captura.get(cv2.CAP_PROP_FRAME_WIDTH))
            alto_real = int(self._captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"Cámara abierta: {ancho_real}x{alto_real}")
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
