"""Capa de adquisición — captura de imagen desde cámaras."""

from .camara import ServicioCamara
from .gestor_camaras import enumerar_camaras, verificar_camara

__all__ = ["ServicioCamara", "enumerar_camaras", "verificar_camara"]
