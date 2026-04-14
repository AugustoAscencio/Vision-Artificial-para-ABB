"""
Gestión de modelos YOLO disponibles en múltiples directorios.
Busca en: modelos/, raíz del proyecto, y rutas absolutas del config.
"""

from pathlib import Path
from typing import Optional

from capa_logs import obtener_logger

logger = obtener_logger("modelos")

_DIRECTORIO_MODELOS = Path(__file__).parent.parent / "modelos"
_DIRECTORIO_RAIZ = Path(__file__).parent.parent


class GestorModelos:
    """
    Gestiona modelos YOLO (.pt) disponibles en múltiples ubicaciones.

    Busca en:
      1. Carpeta modelos/ (directorio dedicado)
      2. Raíz del proyecto (donde viven best.pt, yolov8n.pt, etc.)
      3. Rutas absolutas registradas manualmente
    """

    def __init__(self, directorio: str | Path = None):
        self._directorio = Path(directorio) if directorio else _DIRECTORIO_MODELOS
        self._directorio.mkdir(parents=True, exist_ok=True)
        self._directorio_raiz = _DIRECTORIO_RAIZ
        self._rutas_extra: list[Path] = []  # Rutas absolutas adicionales
        logger.info(f"Directorio de modelos: {self._directorio}")
        logger.info(f"Directorio raíz del proyecto: {self._directorio_raiz}")

    @property
    def directorio(self) -> Path:
        return self._directorio

    def registrar_ruta(self, ruta: str | Path):
        """Registra una ruta absoluta adicional para incluir en la lista."""
        ruta_p = Path(ruta)
        if ruta_p.exists() and ruta_p.suffix == ".pt" and ruta_p not in self._rutas_extra:
            self._rutas_extra.append(ruta_p)
            logger.debug(f"Ruta extra registrada: {ruta_p}")

    def listar_modelos(self) -> list[dict]:
        """
        Lista todos los modelos .pt disponibles de todas las fuentes.

        Retorna:
            [{"nombre": "yolov8n.pt", "ruta": "...", "tamano_mb": 6.2, "origen": "..."}, ...]
        """
        modelos_dict: dict[str, dict] = {}  # clave: ruta absoluta para evitar duplicados

        # 1. Buscar en directorio modelos/
        self._buscar_en_directorio(self._directorio, "modelos/", modelos_dict)

        # 2. Buscar en raíz del proyecto
        self._buscar_en_directorio(self._directorio_raiz, "raíz", modelos_dict)

        # 3. Rutas extra registradas
        for ruta in self._rutas_extra:
            clave = str(ruta.resolve())
            if clave not in modelos_dict and ruta.exists():
                tamano_mb = ruta.stat().st_size / (1024 * 1024)
                modelos_dict[clave] = {
                    "nombre": ruta.name,
                    "ruta": str(ruta),
                    "tamano_mb": round(tamano_mb, 1),
                    "origen": "externo",
                }

        modelos = sorted(modelos_dict.values(), key=lambda m: m["nombre"])
        logger.debug(f"Modelos disponibles: {[m['nombre'] for m in modelos]}")
        return modelos

    def _buscar_en_directorio(self, directorio: Path, origen: str, destino: dict):
        """Busca archivos .pt en un directorio y los agrega al diccionario."""
        if not directorio.exists():
            return
        for archivo in sorted(directorio.glob("*.pt")):
            clave = str(archivo.resolve())
            if clave not in destino:
                tamano_mb = archivo.stat().st_size / (1024 * 1024)
                destino[clave] = {
                    "nombre": archivo.name,
                    "ruta": str(archivo),
                    "tamano_mb": round(tamano_mb, 1),
                    "origen": origen,
                }

    def modelo_existe(self, nombre_o_ruta: str) -> bool:
        """Verifica si un modelo existe por nombre o ruta."""
        # Verificar como ruta absoluta
        if Path(nombre_o_ruta).exists():
            return True
        # Verificar en directorio modelos/
        if (self._directorio / nombre_o_ruta).exists():
            return True
        # Verificar en raíz
        if (self._directorio_raiz / nombre_o_ruta).exists():
            return True
        return False

    def ruta_modelo(self, nombre_o_ruta: str) -> str:
        """
        Resuelve la ruta completa de un modelo.
        Busca en: ruta absoluta → modelos/ → raíz → nombre original (descarga auto).
        """
        # Si es ruta absoluta y existe
        ruta_abs = Path(nombre_o_ruta)
        if ruta_abs.is_absolute() and ruta_abs.exists():
            return str(ruta_abs)

        # En directorio modelos/
        ruta_modelos = self._directorio / nombre_o_ruta
        if ruta_modelos.exists():
            return str(ruta_modelos)

        # En raíz del proyecto
        ruta_raiz = self._directorio_raiz / nombre_o_ruta
        if ruta_raiz.exists():
            return str(ruta_raiz)

        # No encontrado — retornar nombre tal cual para descarga auto
        logger.debug(f"Modelo '{nombre_o_ruta}' no encontrado localmente — descarga automática")
        return nombre_o_ruta

    def recargar(self) -> list[dict]:
        """Recarga la lista de modelos desde todas las fuentes."""
        return self.listar_modelos()
