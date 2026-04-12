"""
Gestión de cámaras disponibles en el sistema.
Enumera y verifica cámaras conectadas.
"""

import cv2

from capa_logs import obtener_logger

logger = obtener_logger("gestor_camaras")


def enumerar_camaras(max_indice: int = 10) -> list[dict]:
    """
    Escanea cámaras disponibles del índice 0 al max_indice.

    Retorna lista de diccionarios:
        [{"indice": 0, "nombre": "Cámara 0", "resolucion": (1280, 720)}, ...]
    """
    camaras = []
    for i in range(max_indice):
        try:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                camaras.append({
                    "indice": i,
                    "nombre": f"Cámara {i}",
                    "resolucion": (ancho, alto),
                })
                logger.debug(f"Cámara encontrada: índice={i}, {ancho}x{alto}")
                cap.release()
        except Exception:
            continue

    logger.info(f"Cámaras disponibles: {len(camaras)}")
    return camaras


def verificar_camara(indice: int) -> bool:
    """Verifica si una cámara en el índice dado está accesible."""
    try:
        cap = cv2.VideoCapture(indice, cv2.CAP_DSHOW)
        abierta = cap.isOpened()
        if abierta:
            cap.release()
        return abierta
    except Exception:
        return False
