"""
Analizador de color dominante usando K-Means.
Clasifica el color dominante de una región de imagen.
"""

import cv2
import numpy as np
from sklearn.cluster import KMeans

from capa_logs import obtener_logger

logger = obtener_logger("color")


# ═══════════════════════════════════════════════════════════════
# Rangos HSV para clasificación de colores
# ═══════════════════════════════════════════════════════════════

# Formato: (nombre, h_min, s_min, v_min, h_max, s_max, v_max)
_RANGOS_COLORES = [
    ("Rojo",      0,   70, 50,   10, 255, 255),
    ("Rojo",      170, 70, 50,   180, 255, 255),   # Rojo wraps around 0
    ("Naranja",   10,  70, 50,   25,  255, 255),
    ("Amarillo",  25,  70, 50,   35,  255, 255),
    ("Verde",     35,  40, 40,   85,  255, 255),
    ("Cyan",      85,  40, 40,   100, 255, 255),
    ("Azul",      100, 40, 40,   130, 255, 255),
    ("Morado",    130, 40, 40,   170, 255, 255),
    ("Blanco",    0,   0,  200,  180, 40,  255),
    ("Negro",     0,   0,  0,    180, 255, 50),
    ("Gris",      0,   0,  50,   180, 40,  200),
]


class AnalizadorColor:
    """
    Determina el color dominante de una región de imagen usando K-Means clustering.
    Clasifica el resultado en nombre de color legible.
    """

    def __init__(self, n_clusters: int = 3):
        self._n_clusters = n_clusters
        self._kmeans = KMeans(
            n_clusters=n_clusters,
            n_init=5,
            max_iter=100,
            random_state=42,
        )

    def color_dominante(
        self,
        frame: np.ndarray,
        bbox: tuple[int, int, int, int],
    ) -> tuple[str, tuple[int, int, int]]:
        """
        Calcula el color dominante dentro de un bounding box.

        Args:
            frame: Imagen BGR completa.
            bbox: (x1, y1, x2, y2) del objeto.

        Returns:
            (nombre_color, (r, g, b))
        """
        x1, y1, x2, y2 = bbox

        # Validar bbox
        h, w = frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        if x2 - x1 < 5 or y2 - y1 < 5:
            return ("desconocido", (128, 128, 128))

        # Recortar región
        region = frame[y1:y2, x1:x2]

        # Reducir resolución para performance (máx 50x50)
        if region.shape[0] > 50 or region.shape[1] > 50:
            region = cv2.resize(region, (50, 50))

        # Reshape para K-Means: (N, 3)
        pixeles = region.reshape(-1, 3).astype(np.float32)

        try:
            self._kmeans.fit(pixeles)
            centros = self._kmeans.cluster_centers_
            etiquetas = self._kmeans.labels_
            conteo = np.bincount(etiquetas)
            dominante_idx = np.argmax(conteo)
            bgr_dominante = centros[dominante_idx].astype(int)
        except Exception as e:
            logger.debug(f"Error en K-Means: {e}")
            # Fallback: promedio simple
            bgr_dominante = np.mean(pixeles, axis=0).astype(int)

        # Convertir BGR → RGB
        rgb = (int(bgr_dominante[2]), int(bgr_dominante[1]), int(bgr_dominante[0]))

        # Clasificar nombre del color usando HSV
        nombre = self._clasificar_color_hsv(bgr_dominante)

        return (nombre, rgb)

    def _clasificar_color_hsv(self, bgr: np.ndarray) -> str:
        """Clasifica un color BGR en un nombre legible usando rangos HSV."""
        pixel = np.uint8([[bgr]])
        hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
        h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])

        for nombre, h_min, s_min, v_min, h_max, s_max, v_max in _RANGOS_COLORES:
            if h_min <= h <= h_max and s_min <= s <= s_max and v_min <= v <= v_max:
                return nombre

        return "Indefinido"
