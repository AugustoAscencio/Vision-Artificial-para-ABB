"""Núcleo del sistema — bus de eventos y modelos de dominio."""

from .eventos import BusEventos
from .modelos import (
    DeteccionObjeto,
    ResultadoFrame,
    MarcadorAruco,
    ComandoRobot,
    EstadoConexion,
)

__all__ = [
    "BusEventos",
    "DeteccionObjeto",
    "ResultadoFrame",
    "MarcadorAruco",
    "ComandoRobot",
    "EstadoConexion",
]
