"""
Gestor centralizado de logging.
Configura handlers para archivo rotativo y para la interfaz gráfica.
"""

import logging
import atexit
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal


# ═══════════════════════════════════════════════════════════════
# Handler personalizado para la UI
# ═══════════════════════════════════════════════════════════════

class ManejadorUI(QObject, logging.Handler):
    """
    Handler de logging que emite señales Qt para actualizar la UI.
    Hereda de QObject para tener pyqtSignal y de logging.Handler
    para integrarse al sistema de logging estándar.
    """
    log_emitido = pyqtSignal(str, str)  # (nivel, mensaje formateado)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        ))
        self._cerrado = False

    def emit(self, record: logging.LogRecord) -> None:
        """Emite el registro como señal Qt."""
        if self._cerrado:
            return
        try:
            mensaje = self.format(record)
            self.log_emitido.emit(record.levelname, mensaje)
        except (RuntimeError, AttributeError):
            # QObject ya fue destruido por Qt — ignorar silenciosamente
            self._cerrado = True
        except Exception:
            self.handleError(record)

    def close(self):
        """Cierra el handler marcándolo como cerrado para evitar errores atexit."""
        self._cerrado = True
        super().close()


# ═══════════════════════════════════════════════════════════════
# Instancia global del handler UI
# ═══════════════════════════════════════════════════════════════

_manejador_ui: Optional[ManejadorUI] = None


def obtener_manejador_ui() -> ManejadorUI:
    """Retorna el singleton del manejador UI."""
    global _manejador_ui
    if _manejador_ui is None:
        _manejador_ui = ManejadorUI()
    return _manejador_ui


# ═══════════════════════════════════════════════════════════════
# Configuración
# ═══════════════════════════════════════════════════════════════

_configurado = False


def _limpiar_al_salir():
    """Remueve el ManejadorUI del logger antes del shutdown de Python."""
    global _manejador_ui
    if _manejador_ui is not None:
        logger_raiz = logging.getLogger("vision_abb")
        try:
            logger_raiz.removeHandler(_manejador_ui)
            _manejador_ui._cerrado = True
        except Exception:
            pass


def configurar_logging(
    nivel: str = "INFO",
    archivo: str = "logs/vision_abb.log",
    max_bytes: int = 5_242_880,
    backups: int = 3,
) -> ManejadorUI:
    """
    Configura el sistema de logging con:
    - Handler de consola
    - Handler de archivo rotativo
    - Handler de UI (PyQt6)

    Retorna el ManejadorUI para conectar a la interfaz.
    """
    global _configurado
    if _configurado:
        return obtener_manejador_ui()

    nivel_log = getattr(logging, nivel.upper(), logging.INFO)

    # Logger raíz del proyecto
    logger_raiz = logging.getLogger("vision_abb")
    logger_raiz.setLevel(nivel_log)
    logger_raiz.propagate = False

    # Limpiar handlers previos
    logger_raiz.handlers.clear()

    # Formato detallado
    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    formato_corto = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )

    # Handler de consola
    handler_consola = logging.StreamHandler()
    handler_consola.setLevel(nivel_log)
    handler_consola.setFormatter(formato_corto)
    logger_raiz.addHandler(handler_consola)

    # Handler de archivo rotativo
    ruta_archivo = Path(archivo)
    ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
    handler_archivo = RotatingFileHandler(
        str(ruta_archivo),
        maxBytes=max_bytes,
        backupCount=backups,
        encoding="utf-8",
    )
    handler_archivo.setLevel(logging.DEBUG)
    handler_archivo.setFormatter(formato)
    logger_raiz.addHandler(handler_archivo)

    # Handler de UI
    manejador_ui = obtener_manejador_ui()
    manejador_ui.setLevel(nivel_log)
    logger_raiz.addHandler(manejador_ui)

    # Registrar limpieza antes del shutdown de Python
    atexit.register(_limpiar_al_salir)

    _configurado = True
    logger_raiz.info("=" * 60)
    logger_raiz.info("Sistema de Vision Artificial ABB -- Inicio de sesion")
    logger_raiz.info("=" * 60)

    return manejador_ui


def obtener_logger(nombre: str) -> logging.Logger:
    """
    Obtiene un logger hijo del logger raíz del proyecto.
    Ejemplo: obtener_logger("camara") -> logger "vision_abb.camara"
    """
    return logging.getLogger(f"vision_abb.{nombre}")
