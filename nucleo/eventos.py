"""
Bus de eventos centralizado basado en señales PyQt6.
Proporciona comunicación desacoplada y thread-safe entre capas.
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal


class BusEventos(QObject):
    """
    Bus de eventos singleton usando pyqtSignal.

    Cada señal transporta datos específicos entre capas sin que
    estas se conozcan directamente. Qt garantiza la entrega
    thread-safe cuando se usan conexiones Qt::QueuedConnection
    (automático entre hilos distintos).
    """

    # ─── Adquisición ──────────────────────────────────────
    frame_capturado = pyqtSignal(object)           # np.ndarray (frame BGR)
    fps_camara_actualizado = pyqtSignal(float)     # FPS de captura

    # ─── Procesamiento ────────────────────────────────────
    frame_preprocesado = pyqtSignal(object)        # np.ndarray (frame corregido)

    # ─── Geometría ────────────────────────────────────────
    aruco_detectado = pyqtSignal(object)           # list[MarcadorAruco]
    homografia_calculada = pyqtSignal(bool)        # True si se calculó con éxito
    calibracion_estado = pyqtSignal(str)           # Mensaje de estado de calibración

    # ─── IA / Detección ───────────────────────────────────
    objetos_detectados = pyqtSignal(object)        # list[DeteccionObjeto]
    resultado_frame = pyqtSignal(object)           # ResultadoFrame completo

    # ─── Comunicación ─────────────────────────────────────
    conexion_cambiada = pyqtSignal(object)         # EstadoConexion
    mensaje_enviado = pyqtSignal(str)              # Dato enviado al robot
    mensaje_recibido = pyqtSignal(str)             # Respuesta del robot
    error_comunicacion = pyqtSignal(str)           # Error de socket

    # ─── Datos listos para robot ──────────────────────────
    comandos_robot_listos = pyqtSignal(object)     # list[ComandoRobot]

    # ─── Sistema ──────────────────────────────────────────
    error_sistema = pyqtSignal(str, str)           # (módulo, mensaje)
    info_sistema = pyqtSignal(str, str)              # (módulo, mensaje)

    def __init__(self):
        super().__init__()


# ═══════════════════════════════════════════════════════════════
# Instancia global (singleton)
# ═══════════════════════════════════════════════════════════════

_instancia_bus: BusEventos | None = None


def obtener_bus() -> BusEventos:
    """Retorna la instancia singleton del bus de eventos."""
    global _instancia_bus
    if _instancia_bus is None:
        _instancia_bus = BusEventos()
    return _instancia_bus
