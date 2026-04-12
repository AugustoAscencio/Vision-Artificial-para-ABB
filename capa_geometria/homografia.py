"""
Cálculo de homografía para transformación de perspectiva.
Convierte correspondencias ArUco (píxeles ↔ mundo real) en matriz de transformación.
"""

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from capa_logs import obtener_logger
from capa_configuracion.ajustes import PuntoMundoAruco
from nucleo.modelos import MarcadorAruco

logger = obtener_logger("homografia")


class CalculadorHomografia:
    """
    Calcula y mantiene la matriz de homografía H.

    La homografía mapea puntos del plano de la imagen (píxeles)
    al plano del mundo real (mm) de la superficie de trabajo.

    Requisito mínimo: 4 correspondencias (píxel ↔ mundo).
    """

    def __init__(self):
        self._H: Optional[np.ndarray] = None          # Homografía píxel → mundo
        self._H_inv: Optional[np.ndarray] = None      # Homografía mundo → píxel
        self._calibrada = False
        self._error_reproyeccion = float("inf")

    @property
    def esta_calibrada(self) -> bool:
        """Indica si hay una homografía válida calculada."""
        return self._calibrada

    @property
    def matriz_H(self) -> Optional[np.ndarray]:
        """Retorna la matriz de homografía (3x3)."""
        return self._H

    @property
    def error_reproyeccion(self) -> float:
        """Error de reproyección RMS en píxeles."""
        return self._error_reproyeccion

    def recalcular(
        self,
        marcadores: list[MarcadorAruco],
        puntos_mundo_config: list[PuntoMundoAruco],
    ) -> bool:
        """
        Calcula la homografía usando marcadores ArUco detectados y
        sus posiciones conocidas en el mundo real.

        Args:
            marcadores: Marcadores ArUco detectados en el frame actual.
            puntos_mundo_config: Posiciones reales (mm) de cada marcador por ID.

        Returns:
            True si la homografía se calculó exitosamente.
        """
        # Construir mapa de posiciones mundo por ID
        mapa_mundo = {p.id: (p.x_mm, p.y_mm) for p in puntos_mundo_config}

        # Emparejar marcadores detectados con sus posiciones mundo
        puntos_px = []
        puntos_mundo = []

        for marcador in marcadores:
            if marcador.id in mapa_mundo:
                puntos_px.append(marcador.centro_px)
                puntos_mundo.append(mapa_mundo[marcador.id])
                # Asignar posición mundo al marcador
                marcador.posicion_mundo_mm = mapa_mundo[marcador.id]

        if len(puntos_px) < 4:
            logger.warning(
                f"Solo {len(puntos_px)} marcadores emparejados — se necesitan mínimo 4"
            )
            return False

        # Convertir a arrays numpy
        pts_px = np.array(puntos_px, dtype=np.float32)
        pts_mundo = np.array(puntos_mundo, dtype=np.float32)

        # Calcular homografía
        H, mascara = cv2.findHomography(pts_px, pts_mundo, cv2.RANSAC, 5.0)
        if H is None:
            logger.error("cv2.findHomography retornó None")
            return False

        # Calcular error de reproyección
        self._error_reproyeccion = self._calcular_error_reproyeccion(pts_px, pts_mundo, H)

        # Guardar homografía y su inversa
        self._H = H
        try:
            self._H_inv = np.linalg.inv(H)
        except np.linalg.LinAlgError:
            logger.warning("No se pudo invertir H — transformación mundo→píxel no disponible")
            self._H_inv = None

        self._calibrada = True
        logger.info(
            f"Homografía calculada — {len(puntos_px)} marcadores, "
            f"error RMS: {self._error_reproyeccion:.2f} px"
        )
        return True

    def pixel_a_mundo(self, px: int, py: int) -> Optional[tuple[float, float]]:
        """
        Transforma un punto de píxeles a coordenadas del mundo (mm).

        Args:
            px, py: Coordenadas en la imagen (píxeles).

        Returns:
            (x_mm, y_mm) o None si no hay homografía.
        """
        if not self._calibrada or self._H is None:
            return None

        punto = np.array([[[px, py]]], dtype=np.float32)
        transformado = cv2.perspectiveTransform(punto, self._H)
        x_mm = float(transformado[0][0][0])
        y_mm = float(transformado[0][0][1])
        return (x_mm, y_mm)

    def mundo_a_pixel(self, x_mm: float, y_mm: float) -> Optional[tuple[int, int]]:
        """
        Transforma un punto del mundo (mm) a píxeles.
        Útil para debug y visualización de grilla.
        """
        if self._H_inv is None:
            return None

        punto = np.array([[[x_mm, y_mm]]], dtype=np.float32)
        transformado = cv2.perspectiveTransform(punto, self._H_inv)
        px = int(round(transformado[0][0][0]))
        py = int(round(transformado[0][0][1]))
        return (px, py)

    def guardar(self, ruta: str = "calibracion/homografia.npz"):
        """Guarda la matriz de homografía en disco."""
        if not self._calibrada:
            logger.warning("No hay homografía para guardar")
            return

        ruta_path = Path(ruta)
        ruta_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(str(ruta_path), H=self._H)
        logger.info(f"Homografía guardada en: {ruta}")

    def cargar(self, ruta: str = "calibracion/homografia.npz") -> bool:
        """Carga la matriz de homografía desde disco."""
        ruta_path = Path(ruta)
        if not ruta_path.exists():
            logger.info("No existe archivo de homografía guardada")
            return False

        try:
            datos = np.load(str(ruta_path))
            self._H = datos["H"]
            self._H_inv = np.linalg.inv(self._H)
            self._calibrada = True
            logger.info(f"Homografía cargada desde: {ruta}")
            return True
        except Exception as e:
            logger.error(f"Error al cargar homografía: {e}")
            return False

    def _calcular_error_reproyeccion(
        self,
        pts_px: np.ndarray,
        pts_mundo: np.ndarray,
        H: np.ndarray,
    ) -> float:
        """Calcula el error RMS de reproyección en píxeles."""
        pts_transformados = cv2.perspectiveTransform(
            pts_px.reshape(-1, 1, 2), H
        ).reshape(-1, 2)
        errores = np.sqrt(np.sum((pts_transformados - pts_mundo) ** 2, axis=1))
        return float(np.mean(errores))
