"""
Calibración intrínseca de cámara usando patrón de tablero de ajedrez.
Calcula la matriz de cámara y coeficientes de distorsión.
"""

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from capa_logs import obtener_logger

logger = obtener_logger("calibracion")


class CalibradorCamara:
    """
    Calibración intrínseca de cámara con tablero de ajedrez.

    Calcula y almacena:
    - Matriz de cámara (camera_matrix)
    - Coeficientes de distorsión (dist_coeffs)
    """

    def __init__(self):
        self.camera_matrix: Optional[np.ndarray] = None
        self.dist_coeffs: Optional[np.ndarray] = None
        self._calibrada = False

    @property
    def esta_calibrada(self) -> bool:
        """Indica si la calibración intrínseca está disponible."""
        return self._calibrada

    def calibrar_con_imagenes(
        self,
        rutas_imagenes: list[str],
        tamano_tablero: tuple[int, int] = (9, 6),
        tamano_cuadro_mm: float = 25.0,
    ) -> bool:
        """
        Calibra la cámara con un conjunto de imágenes de un tablero de ajedrez.

        Args:
            rutas_imagenes: Lista de rutas a imágenes del tablero.
            tamano_tablero: Esquinas internas del tablero (columnas, filas).
            tamano_cuadro_mm: Tamaño de cada cuadro en mm.

        Returns:
            True si la calibración fue exitosa.
        """
        if len(rutas_imagenes) < 5:
            logger.warning("Se necesitan al menos 5 imágenes para calibración confiable")

        # Puntos 3D del tablero en el espacio objeto
        puntos_obj = np.zeros((tamano_tablero[0] * tamano_tablero[1], 3), np.float32)
        puntos_obj[:, :2] = np.mgrid[
            0:tamano_tablero[0], 0:tamano_tablero[1]
        ].T.reshape(-1, 2) * tamano_cuadro_mm

        puntos_objeto = []  # Puntos 3D en el mundo
        puntos_imagen = []  # Puntos 2D en la imagen
        tamano_imagen = None

        criterio = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        for ruta in rutas_imagenes:
            img = cv2.imread(str(ruta))
            if img is None:
                logger.warning(f"No se pudo leer: {ruta}")
                continue

            gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            tamano_imagen = gris.shape[::-1]

            encontrado, esquinas = cv2.findChessboardCorners(gris, tamano_tablero, None)
            if encontrado:
                esquinas_refinadas = cv2.cornerSubPix(
                    gris, esquinas, (11, 11), (-1, -1), criterio
                )
                puntos_objeto.append(puntos_obj)
                puntos_imagen.append(esquinas_refinadas)
                logger.debug(f"Tablero encontrado en: {ruta}")
            else:
                logger.debug(f"Tablero NO encontrado en: {ruta}")

        if len(puntos_objeto) < 3:
            logger.error(f"Solo {len(puntos_objeto)} imágenes válidas — insuficientes")
            return False

        # Calibrar
        ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            puntos_objeto, puntos_imagen, tamano_imagen, None, None
        )

        if ret:
            self.camera_matrix = camera_matrix
            self.dist_coeffs = dist_coeffs
            self._calibrada = True
            logger.info(f"Calibración exitosa — Error RMS: {ret:.4f}")
            logger.info(f"Imágenes usadas: {len(puntos_objeto)}")
            return True
        else:
            logger.error("La calibración falló")
            return False

    def guardar_calibracion(self, ruta: str = "calibracion/calibracion_camara.npz"):
        """Guarda los parámetros de calibración en archivo .npz."""
        if not self._calibrada:
            logger.warning("No hay calibración para guardar")
            return

        ruta_path = Path(ruta)
        ruta_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            str(ruta_path),
            camera_matrix=self.camera_matrix,
            dist_coeffs=self.dist_coeffs,
        )
        logger.info(f"Calibración guardada en: {ruta}")

    def cargar_calibracion(self, ruta: str = "calibracion/calibracion_camara.npz") -> bool:
        """Carga los parámetros de calibración desde archivo .npz."""
        ruta_path = Path(ruta)
        if not ruta_path.exists():
            logger.info("No existe archivo de calibración — operando sin corrección de distorsión")
            return False

        try:
            datos = np.load(str(ruta_path))
            self.camera_matrix = datos["camera_matrix"]
            self.dist_coeffs = datos["dist_coeffs"]
            self._calibrada = True
            logger.info(f"Calibración cargada desde: {ruta}")
            return True
        except Exception as e:
            logger.error(f"Error al cargar calibración: {e}")
            return False
