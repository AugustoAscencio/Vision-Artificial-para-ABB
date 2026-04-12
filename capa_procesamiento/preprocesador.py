"""
Pipeline de preprocesamiento configurable.
Encadena correcciones de imagen en orden definido.
"""

import time

import numpy as np

from capa_logs import obtener_logger
from capa_procesamiento.calibracion import CalibradorCamara
from capa_procesamiento.correccion import CorrectorImagen

logger = obtener_logger("preprocesador")


class Preprocesador:
    """
    Pipeline de preprocesamiento de imágenes.

    Aplica en orden:
    1. Corrección de distorsión (si hay calibración)
    2. Mejora de contraste (CLAHE)
    3. Reducción de ruido (bilateral)

    Cada etapa se activa/desactiva individualmente.
    """

    def __init__(
        self,
        calibrador: CalibradorCamara,
        corregir_distorsion: bool = True,
        mejorar_contraste: bool = False,
        reducir_ruido: bool = False,
    ):
        self._calibrador = calibrador
        self._corrector = CorrectorImagen()
        self.corregir_distorsion = corregir_distorsion
        self.mejorar_contraste = mejorar_contraste
        self.reducir_ruido = reducir_ruido

        # Métricas
        self._tiempo_ultimo_ms = 0.0

    @property
    def tiempo_procesamiento_ms(self) -> float:
        """Tiempo del último preprocesamiento en ms."""
        return self._tiempo_ultimo_ms

    def procesar(self, frame: np.ndarray) -> np.ndarray:
        """
        Aplica el pipeline de preprocesamiento al frame.

        Args:
            frame: Frame BGR de la cámara.

        Returns:
            Frame preprocesado.
        """
        inicio = time.perf_counter()
        resultado = frame.copy()

        # 1. Corrección de distorsión
        if self.corregir_distorsion and self._calibrador.esta_calibrada:
            resultado = self._corrector.corregir_distorsion(
                resultado,
                self._calibrador.camera_matrix,
                self._calibrador.dist_coeffs,
            )

        # 2. Mejora de contraste
        if self.mejorar_contraste:
            resultado = self._corrector.mejorar_contraste(resultado)

        # 3. Reducción de ruido
        if self.reducir_ruido:
            resultado = self._corrector.reducir_ruido(resultado)

        self._tiempo_ultimo_ms = (time.perf_counter() - inicio) * 1000
        return resultado
