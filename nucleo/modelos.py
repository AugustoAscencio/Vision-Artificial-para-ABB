"""
Modelos de dominio del sistema de visión artificial.
Dataclasses tipadas para todas las estructuras de datos.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import numpy as np


# ═══════════════════════════════════════════════════════════════
# Enumeraciones
# ═══════════════════════════════════════════════════════════════

class EstadoConexion(Enum):
    """Estados posibles de la conexión TCP con el robot."""
    DESCONECTADO = auto()
    CONECTANDO = auto()
    CONECTADO = auto()
    ERROR = auto()
    RECONECTANDO = auto()


# ═══════════════════════════════════════════════════════════════
# Marcadores ArUco
# ═══════════════════════════════════════════════════════════════

@dataclass
class MarcadorAruco:
    """Marcador ArUco detectado en un frame."""
    id: int
    esquinas_px: np.ndarray          # Shape (4, 2) — 4 esquinas en píxeles
    centro_px: tuple[int, int]       # Centro del marcador en píxeles
    posicion_mundo_mm: Optional[tuple[float, float]] = None  # (x, y) en mm si está mapeado


# ═══════════════════════════════════════════════════════════════
# Detecciones de objetos
# ═══════════════════════════════════════════════════════════════

@dataclass
class DeteccionObjeto:
    """Objeto detectado por YOLO con metadatos completos."""

    # Identificación
    etiqueta: str                                  # Nombre de la clase YOLO
    confianza: float                               # 0.0 — 1.0

    # Geometría en píxeles
    bbox: tuple[int, int, int, int]                # (x1, y1, x2, y2)
    centroide_px: tuple[int, int]                  # Centro del bbox

    # Geometría en mundo real (mm) — None si no hay homografía
    centroide_mm: Optional[tuple[float, float]] = None   # (x_mm, y_mm)
    altura_estimada_mm: float = 0.0                       # Z estimado
    fuera_de_rango: bool = False                         # True si cae fuera del espacio de trabajo

    # Color
    color_dominante: str = "desconocido"
    color_rgb: tuple[int, int, int] = (128, 128, 128)

    # Clasificación de tamaño
    tamano_clase: str = "desconocido"              # "caja_pequena", "caja_mediana", "caja_grande"

    # Metadatos
    timestamp: float = field(default_factory=time.time)

    @property
    def ancho_px(self) -> int:
        """Ancho del bounding box en píxeles."""
        return self.bbox[2] - self.bbox[0]

    @property
    def alto_px(self) -> int:
        """Alto del bounding box en píxeles."""
        return self.bbox[3] - self.bbox[1]

    @property
    def area_px(self) -> int:
        """Área del bounding box en píxeles."""
        return self.ancho_px * self.alto_px


# ═══════════════════════════════════════════════════════════════
# Resultado completo de un frame procesado
# ═══════════════════════════════════════════════════════════════

@dataclass
class ResultadoFrame:
    """Resultado completo del procesamiento de un frame."""
    frame_original: np.ndarray
    frame_procesado: np.ndarray                # Frame con overlays dibujados
    detecciones: list[DeteccionObjeto] = field(default_factory=list)
    marcadores_aruco: list[MarcadorAruco] = field(default_factory=list)
    homografia_activa: bool = False
    fps: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# Comando para el robot ABB
# ═══════════════════════════════════════════════════════════════

@dataclass
class ComandoRobot:
    """Datos estructurados listos para enviar al controlador ABB."""
    x_mm: float
    y_mm: float
    z_mm: float
    color: str
    tipo: str
    confianza: float = 0.0

    def a_cadena(self) -> str:
        """
        Formatea el comando como cadena parseable por RAPID.
        Formato: "X:120.5,Y:85.3,Z:10.0,C:Rojo,T:Caja"
        Si Z es desconocido (0.0), se envía como Z:NULL.
        """
        z_str = f"{self.z_mm:.1f}" if self.z_mm > 0 else "NULL"
        return (
            f"X:{self.x_mm:.1f},"
            f"Y:{self.y_mm:.1f},"
            f"Z:{z_str},"
            f"C:{self.color},"
            f"T:{self.tipo}"
        )

    @staticmethod
    def desde_deteccion(
        deteccion: DeteccionObjeto,
        usar_pixeles: bool = False,
    ) -> Optional["ComandoRobot"]:
        """
        Crea un ComandoRobot desde una DeteccionObjeto.

        Args:
            deteccion: Objeto detectado por YOLO.
            usar_pixeles: Si True y no hay coordenadas mm, usa
                         centroide_px como fallback (modo simulación).

        Returns:
            ComandoRobot o None si no hay coordenadas disponibles.
        """
        # Prioridad 1: coordenadas mundo real (mm)
        if deteccion.centroide_mm is not None and not deteccion.fuera_de_rango:
            return ComandoRobot(
                x_mm=round(deteccion.centroide_mm[0], 1),
                y_mm=round(deteccion.centroide_mm[1], 1),
                z_mm=round(deteccion.altura_estimada_mm, 1),
                color=deteccion.color_dominante,
                tipo=deteccion.etiqueta,
                confianza=round(deteccion.confianza, 2),
            )

        # Prioridad 2: coordenadas píxel (fallback para simulación)
        if usar_pixeles and deteccion.centroide_px is not None:
            return ComandoRobot(
                x_mm=float(deteccion.centroide_px[0]),
                y_mm=float(deteccion.centroide_px[1]),
                z_mm=0.0,  # Z desconocido → se enviará como NULL
                color=deteccion.color_dominante,
                tipo=f"SIM:{deteccion.etiqueta}",
                confianza=round(deteccion.confianza, 2),
            )

        return None

    def __str__(self) -> str:
        return self.a_cadena()
