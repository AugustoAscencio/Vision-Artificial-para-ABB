"""Capa de inteligencia artificial — detección YOLO, gestión de modelos y análisis de color."""

from .detector_yolo import DetectorYOLO
from .gestor_modelos import GestorModelos
from .analizador_color import AnalizadorColor

__all__ = ["DetectorYOLO", "GestorModelos", "AnalizadorColor"]
