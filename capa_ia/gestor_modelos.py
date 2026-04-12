"""
Gestión de modelos YOLO disponibles en el directorio local.
"""

from pathlib import Path

from capa_logs import obtener_logger

logger = obtener_logger("modelos")

_DIRECTORIO_MODELOS = Path(__file__).parent.parent / "modelos"


class GestorModelos:
    """
    Gestiona modelos YOLO (.pt) disponibles en el directorio modelos/.

    Se asegura de que el directorio exista y lista los modelos disponibles.
    """

    def __init__(self, directorio: str | Path = None):
        self._directorio = Path(directorio) if directorio else _DIRECTORIO_MODELOS
        self._directorio.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directorio de modelos: {self._directorio}")

    @property
    def directorio(self) -> Path:
        return self._directorio

    def listar_modelos(self) -> list[dict]:
        """
        Lista todos los modelos .pt disponibles.

        Retorna:
            [{"nombre": "yolov8n.pt", "ruta": "...", "tamano_mb": 6.2}, ...]
        """
        modelos = []
        for archivo in sorted(self._directorio.glob("*.pt")):
            tamano_mb = archivo.stat().st_size / (1024 * 1024)
            modelos.append({
                "nombre": archivo.name,
                "ruta": str(archivo),
                "tamano_mb": round(tamano_mb, 1),
            })

        logger.debug(f"Modelos disponibles: {[m['nombre'] for m in modelos]}")
        return modelos

    def modelo_existe(self, nombre: str) -> bool:
        """Verifica si un modelo existe en el directorio."""
        return (self._directorio / nombre).exists()

    def ruta_modelo(self, nombre: str) -> str:
        """Retorna la ruta completa de un modelo."""
        ruta = self._directorio / nombre
        if ruta.exists():
            return str(ruta)
        # Si no existe localmente, retorna el nombre tal cual
        # (ultralytics lo descargará automáticamente)
        return nombre

    def recargar(self) -> list[dict]:
        """Recarga la lista de modelos."""
        return self.listar_modelos()
