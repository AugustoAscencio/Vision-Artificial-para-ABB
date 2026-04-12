"""Capa de procesamiento — corrección y mejora de imágenes."""

from .calibracion import CalibradorCamara
from .correccion import CorrectorImagen
from .preprocesador import Preprocesador

__all__ = ["CalibradorCamara", "CorrectorImagen", "Preprocesador"]
