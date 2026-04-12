"""
Detección de marcadores ArUco en frames de cámara.
Identifica marcadores, calcula sus centros y dibuja overlays.
"""

from typing import Optional

import cv2
import numpy as np

from capa_logs import obtener_logger
from nucleo.modelos import MarcadorAruco

logger = obtener_logger("aruco")

# Mapeo de nombres de diccionario a objetos OpenCV
_DICCIONARIOS = {
    "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
    "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
    "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
    "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
    "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
    "DICT_5X5_250": cv2.aruco.DICT_5X5_250,
    "DICT_5X5_1000": cv2.aruco.DICT_5X5_1000,
    "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
    "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
    "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
    "DICT_7X7_50": cv2.aruco.DICT_7X7_50,
    "DICT_7X7_100": cv2.aruco.DICT_7X7_100,
    "DICT_7X7_250": cv2.aruco.DICT_7X7_250,
}


class DetectorAruco:
    """
    Detecta marcadores ArUco en un frame.

    Configurable por diccionario y parámetros de detección.
    """

    def __init__(self, nombre_diccionario: str = "DICT_4X4_50"):
        self._nombre_diccionario = nombre_diccionario
        self._diccionario = None
        self._parametros = None
        self._detector = None
        self._inicializar_detector(nombre_diccionario)

    def _inicializar_detector(self, nombre: str):
        """Inicializa el detector ArUco con el diccionario dado."""
        clave = _DICCIONARIOS.get(nombre)
        if clave is None:
            logger.error(f"Diccionario ArUco desconocido: {nombre}. Usando DICT_4X4_50")
            clave = cv2.aruco.DICT_4X4_50

        self._diccionario = cv2.aruco.getPredefinedDictionary(clave)
        self._parametros = cv2.aruco.DetectorParameters()

        # Optimizaciones para detección robusta
        self._parametros.adaptiveThreshWinSizeMin = 3
        self._parametros.adaptiveThreshWinSizeMax = 23
        self._parametros.adaptiveThreshWinSizeStep = 10
        self._parametros.minMarkerPerimeterRate = 0.03
        self._parametros.maxMarkerPerimeterRate = 4.0
        self._parametros.polygonalApproxAccuracyRate = 0.05
        self._parametros.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX

        self._detector = cv2.aruco.ArucoDetector(self._diccionario, self._parametros)
        logger.info(f"Detector ArUco inicializado: {nombre}")

    def cambiar_diccionario(self, nombre: str):
        """Cambia el diccionario ArUco en caliente."""
        self._inicializar_detector(nombre)
        self._nombre_diccionario = nombre

    def detectar(self, frame: np.ndarray) -> list[MarcadorAruco]:
        """
        Detecta marcadores ArUco en el frame.

        Args:
            frame: Imagen BGR.

        Returns:
            Lista de MarcadorAruco detectados.
        """
        if self._detector is None:
            return []

        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        esquinas, ids, rechazados = self._detector.detectMarkers(gris)

        if ids is None or len(ids) == 0:
            return []

        marcadores = []
        for i, id_marcador in enumerate(ids.flatten()):
            puntos = esquinas[i][0]  # Shape (4, 2)
            centro = np.mean(puntos, axis=0).astype(int)

            marcador = MarcadorAruco(
                id=int(id_marcador),
                esquinas_px=puntos,
                centro_px=(int(centro[0]), int(centro[1])),
            )
            marcadores.append(marcador)

        logger.debug(f"ArUco detectados: {len(marcadores)} — IDs: {[m.id for m in marcadores]}")
        return marcadores

    def dibujar_marcadores(
        self,
        frame: np.ndarray,
        marcadores: list[MarcadorAruco],
        color_borde: tuple[int, int, int] = (0, 255, 0),
        color_centro: tuple[int, int, int] = (0, 0, 255),
        grosor: int = 2,
    ) -> np.ndarray:
        """
        Dibuja los marcadores detectados sobre el frame.

        Dibuja:
        - Contorno del marcador
        - ID en el centro
        - Punto central
        """
        frame_vis = frame.copy()

        for marcador in marcadores:
            esquinas = marcador.esquinas_px.astype(int)

            # Contorno
            cv2.polylines(
                frame_vis,
                [esquinas.reshape(-1, 1, 2)],
                isClosed=True,
                color=color_borde,
                thickness=grosor,
            )

            # Centro
            cx, cy = marcador.centro_px
            cv2.circle(frame_vis, (cx, cy), 5, color_centro, -1)

            # ID
            cv2.putText(
                frame_vis,
                f"ID:{marcador.id}",
                (cx - 20, cy - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                2,
            )

            # Posición mundo si existe
            if marcador.posicion_mundo_mm is not None:
                texto_mm = f"({marcador.posicion_mundo_mm[0]:.0f}, {marcador.posicion_mundo_mm[1]:.0f}) mm"
                cv2.putText(
                    frame_vis,
                    texto_mm,
                    (cx - 40, cy + 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (200, 200, 200),
                    1,
                )

        return frame_vis
