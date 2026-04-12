"""
Corrección y mejora de imágenes.
Incluye undistort, mejora de contraste (CLAHE) y reducción de ruido.
"""

from typing import Optional

import cv2
import numpy as np

from capa_logs import obtener_logger

logger = obtener_logger("correccion")


class CorrectorImagen:
    """Aplica correcciones de imagen configurables."""

    def __init__(self):
        # CLAHE para mejora de contraste
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def corregir_distorsion(
        self,
        frame: np.ndarray,
        camera_matrix: np.ndarray,
        dist_coeffs: np.ndarray,
    ) -> np.ndarray:
        """
        Corrige la distorsión de lente usando parámetros de calibración.
        """
        h, w = frame.shape[:2]
        nueva_matrix, roi = cv2.getOptimalNewCameraMatrix(
            camera_matrix, dist_coeffs, (w, h), 1, (w, h)
        )
        frame_corregido = cv2.undistort(frame, camera_matrix, dist_coeffs, None, nueva_matrix)

        # Recortar a la región válida
        x, y, w_roi, h_roi = roi
        if w_roi > 0 and h_roi > 0:
            frame_corregido = frame_corregido[y:y + h_roi, x:x + w_roi]

        return frame_corregido

    def mejorar_contraste(self, frame: np.ndarray) -> np.ndarray:
        """
        Mejora el contraste usando CLAHE en el canal de luminosidad (LAB).
        """
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        canales = list(cv2.split(lab))
        canales[0] = self._clahe.apply(canales[0])
        lab_mejorado = cv2.merge(canales)
        return cv2.cvtColor(lab_mejorado, cv2.COLOR_LAB2BGR)

    def reducir_ruido(self, frame: np.ndarray) -> np.ndarray:
        """
        Reduce ruido con filtro bilateral (preserva bordes).
        """
        return cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)
