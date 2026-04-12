"""Capa de geometría — ArUco, homografía y transformación de coordenadas."""

from .detector_aruco import DetectorAruco
from .homografia import CalculadorHomografia
from .transformador_coordenadas import TransformadorCoordenadas

__all__ = ["DetectorAruco", "CalculadorHomografia", "TransformadorCoordenadas"]
