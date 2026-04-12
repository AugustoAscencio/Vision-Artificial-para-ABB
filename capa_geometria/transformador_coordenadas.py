"""
Transformador de coordenadas píxeles ↔ mundo real.
Integra la homografía con estimación de altura y validación de rango.
"""

from typing import Optional

from capa_logs import obtener_logger
from capa_geometria.homografia import CalculadorHomografia
from nucleo.modelos import DeteccionObjeto

logger = obtener_logger("coordenadas")


class TransformadorCoordenadas:
    """
    Convierte coordenadas de detecciones de píxeles a mundo real (mm).

    Usa la homografía para X,Y y una tabla de alturas para Z.
    Valida que los puntos estén dentro del espacio de trabajo.
    """

    def __init__(
        self,
        calculador_homografia: CalculadorHomografia,
        alturas_por_tipo: dict[str, float] = None,
        limites_espacio_mm: Optional[dict] = None,
    ):
        self._homografia = calculador_homografia
        self._alturas = alturas_por_tipo or {
            "caja_pequena": 30.0,
            "caja_mediana": 50.0,
            "caja_grande": 80.0,
            "desconocido": 20.0,
        }
        # Límites del espacio de trabajo en mm
        self._limites = limites_espacio_mm or {
            "x_min": -50.0, "x_max": 400.0,
            "y_min": -50.0, "y_max": 300.0,
        }

    def transformar_deteccion(self, deteccion: DeteccionObjeto) -> DeteccionObjeto:
        """
        Enriquece una DeteccionObjeto con coordenadas del mundo real.

        Modifica in-place y retorna la detección.
        """
        if not self._homografia.esta_calibrada:
            return deteccion

        # Transformar centroide de píxeles a mm
        resultado = self._homografia.pixel_a_mundo(
            deteccion.centroide_px[0],
            deteccion.centroide_px[1],
        )

        if resultado is not None:
            x_mm, y_mm = resultado
            deteccion.centroide_mm = (round(x_mm, 1), round(y_mm, 1))

            # Verificar si está dentro del espacio de trabajo
            deteccion.fuera_de_rango = not self._dentro_de_limites(x_mm, y_mm)
            if deteccion.fuera_de_rango:
                logger.debug(
                    f"Objeto '{deteccion.etiqueta}' fuera de rango: "
                    f"({x_mm:.1f}, {y_mm:.1f}) mm"
                )

        # Estimar altura según tamaño del objeto
        deteccion.altura_estimada_mm = self._estimar_altura(deteccion)

        # Clasificar tamaño
        deteccion.tamano_clase = self._clasificar_tamano(deteccion)

        return deteccion

    def transformar_lote(self, detecciones: list[DeteccionObjeto]) -> list[DeteccionObjeto]:
        """Transforma un lote de detecciones."""
        return [self.transformar_deteccion(d) for d in detecciones]

    def _dentro_de_limites(self, x_mm: float, y_mm: float) -> bool:
        """Verifica si un punto está dentro del espacio de trabajo."""
        return (
            self._limites["x_min"] <= x_mm <= self._limites["x_max"]
            and self._limites["y_min"] <= y_mm <= self._limites["y_max"]
        )

    def _estimar_altura(self, deteccion: DeteccionObjeto) -> float:
        """
        Estima la altura Z del objeto basándose en:
        1. El tamaño del bounding box (proporcional a la escala del objeto)
        2. Tabla de alturas por tipo/tamaño
        """
        tamano = self._clasificar_tamano(deteccion)
        return self._alturas.get(tamano, self._alturas.get("desconocido", 20.0))

    def _clasificar_tamano(self, deteccion: DeteccionObjeto) -> str:
        """
        Clasifica el tamaño del objeto basándose en el área del bbox.
        Umbrales en píxeles² (ajustables).
        """
        area = deteccion.area_px
        if area < 5000:
            return "caja_pequena"
        elif area < 20000:
            return "caja_mediana"
        else:
            return "caja_grande"
