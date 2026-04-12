"""
Modelo de configuración del sistema.
Carga y persiste ajustes desde/hacia archivo YAML.
"""

import os
import re
import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# ═══════════════════════════════════════════════════════════════
# Constantes
# ═══════════════════════════════════════════════════════════════

_RUTA_CONFIG_DEFECTO = Path(__file__).parent / "config_defecto.yaml"
_RUTA_CONFIG_USUARIO = Path(__file__).parent.parent / "config_usuario.yaml"
_PATRON_IP = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)


# ═══════════════════════════════════════════════════════════════
# Dataclass de configuración
# ═══════════════════════════════════════════════════════════════

@dataclass
class PuntoMundoAruco:
    """Posición real de un marcador ArUco en mm."""
    id: int
    x_mm: float
    y_mm: float


@dataclass
class Ajustes:
    """Configuración completa del sistema de visión."""

    # — Cámara —
    camara_indice: int = 0
    camara_resolucion: tuple[int, int] = (1280, 720)
    camara_fps_objetivo: int = 30

    # — Robot ABB —
    robot_ip: str = "172.18.9.27"
    robot_puerto: int = 8000
    reconexion_automatica: bool = True
    intervalo_envio_ms: int = 200
    timeout_conexion_s: int = 5

    # — YOLO —
    yolo_modelo: str = "yolov8n.pt"
    yolo_confianza: float = 0.5
    yolo_iou: float = 0.45
    yolo_dispositivo: str = "auto"

    # — ArUco —
    aruco_diccionario: str = "DICT_4X4_50"
    aruco_tamano_marcador_mm: float = 50.0
    aruco_puntos_mundo: list[PuntoMundoAruco] = field(default_factory=list)

    # — Preprocesamiento —
    corregir_distorsion: bool = True
    mejorar_contraste: bool = False
    reducir_ruido: bool = False

    # — Alturas por defecto —
    alturas_objetos: dict[str, float] = field(default_factory=lambda: {
        "caja_pequena": 30.0,
        "caja_mediana": 50.0,
        "caja_grande": 80.0,
        "desconocido": 20.0,
    })

    # — General —
    modo_simulacion: bool = False
    envio_automatico: bool = False

    # — Logging —
    log_nivel: str = "INFO"
    log_archivo: str = "logs/vision_abb.log"
    log_max_bytes: int = 5_242_880
    log_backups: int = 3

    # ───────────────────────────────────────────────────────
    # Validación
    # ───────────────────────────────────────────────────────

    def validar_ip(self) -> bool:
        """Valida que la IP del robot sea una dirección IPv4 válida."""
        return bool(_PATRON_IP.match(self.robot_ip))

    def validar_puerto(self) -> bool:
        """Valida que el puerto esté en rango válido."""
        return 1 <= self.robot_puerto <= 65535

    def validar(self) -> list[str]:
        """Ejecuta todas las validaciones. Retorna lista de errores."""
        errores = []
        if not self.validar_ip():
            errores.append(f"IP inválida: {self.robot_ip}")
        if not self.validar_puerto():
            errores.append(f"Puerto inválido: {self.robot_puerto}")
        if self.yolo_confianza < 0.05 or self.yolo_confianza > 1.0:
            errores.append(f"Confianza YOLO fuera de rango: {self.yolo_confianza}")
        if self.aruco_tamano_marcador_mm <= 0:
            errores.append("El tamaño del marcador ArUco debe ser > 0")
        return errores


# ═══════════════════════════════════════════════════════════════
# Funciones de carga y guardado
# ═══════════════════════════════════════════════════════════════

def _yaml_a_ajustes(datos: dict) -> Ajustes:
    """Convierte un diccionario YAML a un objeto Ajustes."""
    cam = datos.get("camara", {})
    rob = datos.get("robot", {})
    yol = datos.get("yolo", {})
    aru = datos.get("aruco", {})
    pre = datos.get("preprocesamiento", {})
    alt = datos.get("alturas_objetos", {})
    log = datos.get("logging", {})

    puntos = []
    for p in aru.get("puntos_mundo", []):
        puntos.append(PuntoMundoAruco(
            id=p.get("id", 0),
            x_mm=p.get("x_mm", 0.0),
            y_mm=p.get("y_mm", 0.0),
        ))

    resolucion = cam.get("resolucion", [1280, 720])

    return Ajustes(
        camara_indice=cam.get("indice", 0),
        camara_resolucion=tuple(resolucion),
        camara_fps_objetivo=cam.get("fps_objetivo", 30),
        robot_ip=rob.get("ip", "172.18.9.27"),
        robot_puerto=rob.get("puerto", 8000),
        reconexion_automatica=rob.get("reconexion_automatica", True),
        intervalo_envio_ms=rob.get("intervalo_envio_ms", 200),
        timeout_conexion_s=rob.get("timeout_conexion_s", 5),
        yolo_modelo=yol.get("modelo", "yolov8n.pt"),
        yolo_confianza=yol.get("confianza", 0.5),
        yolo_iou=yol.get("iou", 0.45),
        yolo_dispositivo=yol.get("dispositivo", "auto"),
        aruco_diccionario=aru.get("diccionario", "DICT_4X4_50"),
        aruco_tamano_marcador_mm=aru.get("tamano_marcador_mm", 50.0),
        aruco_puntos_mundo=puntos,
        corregir_distorsion=pre.get("corregir_distorsion", True),
        mejorar_contraste=pre.get("mejorar_contraste", False),
        reducir_ruido=pre.get("reducir_ruido", False),
        alturas_objetos=alt if alt else {
            "caja_pequena": 30.0,
            "caja_mediana": 50.0,
            "caja_grande": 80.0,
            "desconocido": 20.0,
        },
        modo_simulacion=datos.get("modo_simulacion", False),
        envio_automatico=datos.get("envio_automatico", False),
        log_nivel=log.get("nivel", "INFO"),
        log_archivo=log.get("archivo", "logs/vision_abb.log"),
        log_max_bytes=log.get("max_bytes", 5_242_880),
        log_backups=log.get("backups", 3),
    )


def _ajustes_a_yaml(ajustes: Ajustes) -> dict:
    """Convierte un objeto Ajustes a diccionario para YAML."""
    return {
        "camara": {
            "indice": ajustes.camara_indice,
            "resolucion": list(ajustes.camara_resolucion),
            "fps_objetivo": ajustes.camara_fps_objetivo,
        },
        "robot": {
            "ip": ajustes.robot_ip,
            "puerto": ajustes.robot_puerto,
            "reconexion_automatica": ajustes.reconexion_automatica,
            "intervalo_envio_ms": ajustes.intervalo_envio_ms,
            "timeout_conexion_s": ajustes.timeout_conexion_s,
        },
        "yolo": {
            "modelo": ajustes.yolo_modelo,
            "confianza": ajustes.yolo_confianza,
            "iou": ajustes.yolo_iou,
            "dispositivo": ajustes.yolo_dispositivo,
        },
        "aruco": {
            "diccionario": ajustes.aruco_diccionario,
            "tamano_marcador_mm": ajustes.aruco_tamano_marcador_mm,
            "puntos_mundo": [
                {"id": p.id, "x_mm": p.x_mm, "y_mm": p.y_mm}
                for p in ajustes.aruco_puntos_mundo
            ],
        },
        "preprocesamiento": {
            "corregir_distorsion": ajustes.corregir_distorsion,
            "mejorar_contraste": ajustes.mejorar_contraste,
            "reducir_ruido": ajustes.reducir_ruido,
        },
        "alturas_objetos": copy.deepcopy(ajustes.alturas_objetos),
        "modo_simulacion": ajustes.modo_simulacion,
        "envio_automatico": ajustes.envio_automatico,
        "logging": {
            "nivel": ajustes.log_nivel,
            "archivo": ajustes.log_archivo,
            "max_bytes": ajustes.log_max_bytes,
            "backups": ajustes.log_backups,
        },
    }


def cargar_ajustes(ruta: Optional[str] = None) -> Ajustes:
    """
    Carga la configuración desde YAML.
    Prioridad: ruta dada → config_usuario.yaml → config_defecto.yaml
    """
    ruta_final = None
    if ruta and Path(ruta).exists():
        ruta_final = Path(ruta)
    elif _RUTA_CONFIG_USUARIO.exists():
        ruta_final = _RUTA_CONFIG_USUARIO
    elif _RUTA_CONFIG_DEFECTO.exists():
        ruta_final = _RUTA_CONFIG_DEFECTO

    if ruta_final is None:
        return Ajustes()  # Valores por defecto del dataclass

    with open(ruta_final, "r", encoding="utf-8") as f:
        datos = yaml.safe_load(f) or {}

    return _yaml_a_ajustes(datos)


def guardar_ajustes(ajustes: Ajustes, ruta: Optional[str] = None) -> None:
    """Guarda la configuración actual como YAML."""
    ruta_final = Path(ruta) if ruta else _RUTA_CONFIG_USUARIO
    ruta_final.parent.mkdir(parents=True, exist_ok=True)
    datos = _ajustes_a_yaml(ajustes)

    with open(ruta_final, "w", encoding="utf-8") as f:
        yaml.dump(datos, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
