"""
Utilidad para exportar datos capturados (snapshots) a diferentes formatos.
"""

import csv
import json
import time
from pathlib import Path

from nucleo.modelos import DeteccionObjeto
from capa_logs import obtener_logger

logger = obtener_logger("exportador")


def exportar_a_csv(detecciones: list[DeteccionObjeto], ruta_destino: str) -> bool:
    """
    Exporta una lista de detecciones a un archivo CSV.
    """
    try:
        Path(ruta_destino).parent.mkdir(parents=True, exist_ok=True)
        with open(ruta_destino, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Cabecera
            writer.writerow([
                "Timestamp", "Etiqueta", "Confianza",
                "X_px", "Y_px", "X_mm", "Y_mm", "Z_mm",
                "Color", "Fuera_Rango"
            ])
            # Filas
            for det in detecciones:
                # Timestamp legible
                t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(det.timestamp))
                
                # Coordenadas
                cx_px, cy_px = det.centroide_px if det.centroide_px else (0, 0)
                cx_mm, cy_mm = det.centroide_mm if det.centroide_mm else (0.0, 0.0)
                
                writer.writerow([
                    t_str,
                    det.etiqueta,
                    f"{det.confianza:.2f}",
                    cx_px, cy_px,
                    f"{cx_mm:.1f}", f"{cy_mm:.1f}", f"{det.altura_estimada_mm:.1f}",
                    det.color_dominante,
                    "Si" if det.fuera_de_rango else "No"
                ])
        logger.info(f"Datos exportados a CSV: {ruta_destino}")
        return True
    except Exception as e:
        logger.error(f"Error exportando a CSV: {e}")
        return False


def exportar_a_json(detecciones: list[DeteccionObjeto], ruta_destino: str) -> bool:
    """
    Exporta una lista de detecciones a un archivo JSON.
    """
    try:
        Path(ruta_destino).parent.mkdir(parents=True, exist_ok=True)
        datos = []
        for det in detecciones:
            t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(det.timestamp))
            cx_px, cy_px = det.centroide_px if det.centroide_px else (0, 0)
            cx_mm, cy_mm = det.centroide_mm if det.centroide_mm else (0.0, 0.0)
            
            datos.append({
                "timestamp": t_str,
                "etiqueta": det.etiqueta,
                "confianza": round(det.confianza, 2),
                "pixeles": {"x": cx_px, "y": cy_px},
                "mundo_mm": {"x": round(cx_mm, 1), "y": round(cy_mm, 1), "z": round(det.altura_estimada_mm, 1)},
                "color": det.color_dominante,
                "rgb": det.color_rgb,
                "fuera_rango": det.fuera_de_rango
            })
            
        with open(ruta_destino, mode="w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Datos exportados a JSON: {ruta_destino}")
        return True
    except Exception as e:
        logger.error(f"Error exportando a JSON: {e}")
        return False
