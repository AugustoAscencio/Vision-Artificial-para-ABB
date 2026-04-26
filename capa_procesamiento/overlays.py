"""
Motor de overlays visuales para la capa de procesamiento.
Dibuja elementos AR sobre el frame sin modificar datos reales.

Incluye:
- Crosshair dinámico (punto de referencia)
- Zona calibrada (polígono ArUco)
- Rejilla AR con líneas cada N mm
"""

import cv2
import numpy as np
from typing import Optional

from capa_logs import obtener_logger
from nucleo.modelos import MarcadorAruco

logger = obtener_logger("overlays")


def calcular_limites_desde_puntos(puntos_mundo) -> dict:
    """
    Calcula los límites min/max en mm a partir de los puntos mundo ArUco.
    Los límites cubren exactamente el perímetro sin margen extra.

    Args:
        puntos_mundo: Lista de PuntoMundoAruco (con x_mm, y_mm).

    Returns:
        Dict con x_min, x_max, y_min, y_max.
    """
    if not puntos_mundo:
        return {"x_min": 0.0, "x_max": 500.0, "y_min": 0.0, "y_max": 300.0}

    xs = [p.x_mm for p in puntos_mundo]
    ys = [p.y_mm for p in puntos_mundo]
    return {
        "x_min": min(xs),
        "x_max": max(xs),
        "y_min": min(ys),
        "y_max": max(ys),
    }


class MotorOverlays:
    """
    Dibuja overlays visuales sobre frames de cámara.
    Solo visualización — no modifica datos ni coordenadas.
    """

    def __init__(self):
        self.mostrar_crosshair = False
        self.mostrar_rejilla = False
        self._color_crosshair = (0, 255, 200)    # Cyan-verde
        self._color_zona = (0, 255, 0)            # Verde
        self._color_rejilla = (60, 60, 60)        # Gris tenue
        self._color_ejes = (100, 200, 255)        # Azul claro
        self._espaciado_mm = 50.0                  # mm entre líneas de rejilla
        self._limites_mm: Optional[dict] = None    # Límites dinámicos del perímetro ArUco

    def actualizar_limites(self, puntos_mundo) -> None:
        """Actualiza los límites de la rejilla desde los puntos mundo ArUco."""
        self._limites_mm = calcular_limites_desde_puntos(puntos_mundo)
        logger.debug(f"Límites rejilla actualizados: {self._limites_mm}")

    @property
    def espaciado_mm(self) -> float:
        return self._espaciado_mm

    @espaciado_mm.setter
    def espaciado_mm(self, valor: float):
        self._espaciado_mm = max(10.0, min(500.0, valor))

    # ═══════════════════════════════════════════════════════
    # Crosshair
    # ═══════════════════════════════════════════════════════

    def dibujar_crosshair(
        self,
        frame: np.ndarray,
        punto_px: Optional[tuple[int, int]] = None,
    ) -> np.ndarray:
        """
        Dibuja una cruz de referencia en el frame.

        Args:
            frame: Imagen BGR.
            punto_px: Centro de la cruz en pixeles.
                      Si es None, usa el centro del frame.
        """
        h, w = frame.shape[:2]
        if punto_px is None:
            cx, cy = w // 2, h // 2
        else:
            cx, cy = punto_px

        color = self._color_crosshair
        long_linea = 30
        grosor = 1

        # Cruz principal
        cv2.line(frame, (cx - long_linea, cy), (cx + long_linea, cy),
                 color, grosor, cv2.LINE_AA)
        cv2.line(frame, (cx, cy - long_linea), (cx, cy + long_linea),
                 color, grosor, cv2.LINE_AA)

        # Circulo central
        cv2.circle(frame, (cx, cy), 5, color, 1, cv2.LINE_AA)

        # Etiqueta
        cv2.putText(frame, "REF", (cx + 8, cy - 10),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

        return frame

    # ═══════════════════════════════════════════════════════
    # Zona calibrada
    # ═══════════════════════════════════════════════════════

    def dibujar_zona_calibrada(
        self,
        frame: np.ndarray,
        marcadores: list[MarcadorAruco],
    ) -> np.ndarray:
        """
        Dibuja un poligono semi-transparente conectando los marcadores ArUco.
        Solo se dibuja si hay al menos 3 marcadores.
        """
        if len(marcadores) < 3:
            return frame

        # Ordenar marcadores por ID para consistencia
        marcadores_ord = sorted(marcadores, key=lambda m: m.id)
        centros = np.array([m.centro_px for m in marcadores_ord], dtype=np.int32)

        # Ordenar puntos en sentido horario para formar un poligono coherente
        centros_ordenados = self._ordenar_puntos_horario(centros)

        # Dibujar poligono semi-transparente
        overlay = frame.copy()
        cv2.fillPoly(overlay, [centros_ordenados], (0, 180, 0))
        cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)

        # Borde del poligono
        cv2.polylines(frame, [centros_ordenados], isClosed=True,
                      color=self._color_zona, thickness=2)

        # Etiqueta "ZONA CALIBRADA"
        cx = int(np.mean(centros_ordenados[:, 0]))
        cy = int(np.mean(centros_ordenados[:, 1]))
        cv2.putText(frame, "ZONA CALIBRADA", (cx - 70, cy),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

        return frame

    # ═══════════════════════════════════════════════════════
    # Rejilla AR
    # ═══════════════════════════════════════════════════════

    def dibujar_rejilla(
        self,
        frame: np.ndarray,
        homografia,
        limites_mm: Optional[dict] = None,
    ) -> np.ndarray:
        """
        Dibuja una rejilla AR sobre el frame usando la homografia inversa.
        Convierte puntos de rejilla en mm -> pixeles y dibuja lineas.

        Los límites se determinan en este orden de prioridad:
        1. Parámetro `limites_mm` explícito.
        2. Límites almacenados internamente (desde `actualizar_limites()`).
        3. Fallback por defecto.

        Args:
            frame: Imagen BGR.
            homografia: Instancia de CalculadorHomografia (con mundo_a_pixel()).
            limites_mm: Dict con x_min, x_max, y_min, y_max en mm.
        """
        if not homografia.esta_calibrada:
            return frame

        # Prioridad: parámetro > almacenado > fallback
        if limites_mm is None:
            limites_mm = self._limites_mm
        if limites_mm is None:
            limites_mm = {
                "x_min": 0.0, "x_max": 500.0,
                "y_min": 0.0, "y_max": 300.0,
            }

        paso = self._espaciado_mm
        x_min = limites_mm["x_min"]
        x_max = limites_mm["x_max"]
        y_min = limites_mm["y_min"]
        y_max = limites_mm["y_max"]

        # ── Lineas verticales (X constante) ──
        x = x_min
        while x <= x_max + 0.01:  # +epsilon para incluir borde
            p1 = homografia.mundo_a_pixel(x, y_min)
            p2 = homografia.mundo_a_pixel(x, y_max)
            if p1 is not None and p2 is not None:
                es_borde = abs(x - x_min) < 0.01 or abs(x - x_max) < 0.01
                color = self._color_ejes if es_borde else self._color_rejilla
                grosor = 2 if es_borde else 1
                cv2.line(frame, p1, p2, color, grosor, cv2.LINE_AA)

                # Etiqueta cada 2 pasos o en los bordes
                paso_etiqueta = max(paso * 2, 1.0)
                if es_borde or (paso_etiqueta > 0 and abs(round(x / paso_etiqueta) * paso_etiqueta - x) < 0.01):
                    cv2.putText(frame, f"{x:.0f}", (p2[0] + 3, p2[1]),
                                 cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                                 (150, 150, 150), 1, cv2.LINE_AA)
            x += paso

        # ── Lineas horizontales (Y constante) ──
        y = y_min
        while y <= y_max + 0.01:  # +epsilon para incluir borde
            p1 = homografia.mundo_a_pixel(x_min, y)
            p2 = homografia.mundo_a_pixel(x_max, y)
            if p1 is not None and p2 is not None:
                es_borde = abs(y - y_min) < 0.01 or abs(y - y_max) < 0.01
                color = self._color_ejes if es_borde else self._color_rejilla
                grosor = 2 if es_borde else 1
                cv2.line(frame, p1, p2, color, grosor, cv2.LINE_AA)

                paso_etiqueta = max(paso * 2, 1.0)
                if es_borde or (paso_etiqueta > 0 and abs(round(y / paso_etiqueta) * paso_etiqueta - y) < 0.01):
                    cv2.putText(frame, f"{y:.0f}", (p1[0] - 40, p1[1] - 3),
                                 cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                                 (150, 150, 150), 1, cv2.LINE_AA)
            y += paso

        return frame

    # ═══════════════════════════════════════════════════════
    # Utilidades
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _ordenar_puntos_horario(puntos: np.ndarray) -> np.ndarray:
        """Ordena puntos 2D en sentido horario desde arriba-izquierda."""
        # Calcular centroide
        cx = np.mean(puntos[:, 0])
        cy = np.mean(puntos[:, 1])

        # Calcular angulos respecto al centroide
        angulos = np.arctan2(puntos[:, 1] - cy, puntos[:, 0] - cx)
        indices = np.argsort(angulos)

        return puntos[indices]
