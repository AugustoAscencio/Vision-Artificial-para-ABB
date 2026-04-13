"""
Detector de objetos basado en YOLO (ultralytics).
Soporta cambio de modelo en caliente y selección automática de dispositivo.
"""

import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch

from capa_logs import obtener_logger
from nucleo.modelos import DeteccionObjeto

logger = obtener_logger("yolo")


class DetectorYOLO:
    """
    Detector de objetos usando modelos YOLO de ultralytics.

    Características:
    - Carga de modelos .pt (yolov8n, yolov8s, custom, etc.)
    - Selección automática CPU/CUDA
    - Cambio de modelo sin reiniciar la app
    - Métricas de rendimiento
    """

    def __init__(
        self,
        ruta_modelo: str = "yolov8n.pt",
        confianza: float = 0.5,
        iou: float = 0.45,
        dispositivo: str = "auto",
    ):
        self._ruta_modelo = ruta_modelo
        self._confianza = confianza
        self._iou = iou
        self._modelo = None
        self._tiempo_inferencia_ms = 0.0
        self._dispositivo = self._resolver_dispositivo(dispositivo)

        self._cargar_modelo(ruta_modelo)

    # ───────────────────────────────────────────────────────
    # Propiedades
    # ───────────────────────────────────────────────────────

    @property
    def modelo_cargado(self) -> bool:
        """Indica si hay un modelo YOLO cargado."""
        return self._modelo is not None

    @property
    def nombre_modelo(self) -> str:
        """Nombre del modelo actual."""
        return Path(self._ruta_modelo).name

    @property
    def tiempo_inferencia_ms(self) -> float:
        """Tiempo de la última inferencia en milisegundos."""
        return self._tiempo_inferencia_ms

    @property
    def confianza(self) -> float:
        return self._confianza

    @confianza.setter
    def confianza(self, valor: float):
        self._confianza = max(0.05, min(1.0, valor))

    # ───────────────────────────────────────────────────────
    # Carga de modelos
    # ───────────────────────────────────────────────────────

    def _resolver_dispositivo(self, dispositivo: str) -> str:
        """Determina el dispositivo óptimo para inferencia."""
        if dispositivo == "auto":
            if torch.cuda.is_available():
                nombre_gpu = torch.cuda.get_device_name(0)
                logger.info(f"CUDA disponible: {nombre_gpu}")
                return "cuda"
            else:
                logger.info("CUDA no disponible — usando CPU")
                return "cpu"
        return dispositivo

    def _cargar_modelo(self, ruta: str):
        """Carga un modelo YOLO."""
        try:
            from ultralytics import YOLO

            logger.info(f"Cargando modelo YOLO: {ruta} → dispositivo: {self._dispositivo}")
            self._modelo = YOLO(ruta)
            self._ruta_modelo = ruta
            logger.info(f"Modelo '{Path(ruta).name}' cargado exitosamente")

        except Exception as e:
            logger.error(f"Error al cargar modelo YOLO '{ruta}': {e}")
            self._modelo = None

    def cambiar_modelo(self, ruta: str) -> bool:
        """
        Cambia el modelo YOLO en caliente.

        Returns:
            True si el cambio fue exitoso.
        """
        logger.info(f"Cambiando modelo: {self._ruta_modelo} → {ruta}")
        modelo_anterior = self._modelo
        ruta_anterior = self._ruta_modelo

        self._cargar_modelo(ruta)

        if self._modelo is None:
            # Revertir al anterior
            self._modelo = modelo_anterior
            self._ruta_modelo = ruta_anterior
            logger.warning("Cambio de modelo fallido — se mantuvo el anterior")
            return False

        return True

    # ───────────────────────────────────────────────────────
    # Detección
    # ───────────────────────────────────────────────────────

    def detectar(self, frame: np.ndarray) -> list[DeteccionObjeto]:
        """
        Ejecuta detección de objetos en el frame.

        Args:
            frame: Imagen BGR.

        Returns:
            Lista de DeteccionObjeto con bbox, centroide, etiqueta y confianza.
            Las coordenadas están en píxeles (sin transformación al mundo real).
        """
        if self._modelo is None:
            return []

        inicio = time.perf_counter()

        try:
            resultados = self._modelo(
                frame,
                conf=self._confianza,
                iou=self._iou,
                device=self._dispositivo,
                verbose=False,
            )
        except Exception as e:
            logger.error(f"Error en inferencia YOLO: {e}")
            return []

        self._tiempo_inferencia_ms = (time.perf_counter() - inicio) * 1000

        detecciones = []
        for resultado in resultados:
            if resultado.boxes is None:
                continue

            for i, box in enumerate(resultado.boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                clase_id = int(box.cls[0].cpu().numpy())
                etiqueta = resultado.names.get(clase_id, f"clase_{clase_id}")

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                deteccion = DeteccionObjeto(
                    etiqueta=etiqueta,
                    confianza=round(conf, 3),
                    bbox=(x1, y1, x2, y2),
                    centroide_px=(cx, cy),
                )
                detecciones.append(deteccion)

        logger.debug(
            f"YOLO: {len(detecciones)} objetos en {self._tiempo_inferencia_ms:.1f}ms"
        )
        return detecciones

    def dibujar_detecciones(
        self,
        frame: np.ndarray,
        detecciones: list[DeteccionObjeto],
    ) -> np.ndarray:
        """Dibuja bounding boxes profesionales con etiquetas completas sobre el frame."""
        import cv2

        frame_vis = frame.copy()

        for det in detecciones:
            x1, y1, x2, y2 = det.bbox
            color_bbox = det.color_rgb[::-1]  # RGB → BGR

            # Bounding box semi-transparente
            overlay = frame_vis.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color_bbox, -1)
            cv2.addWeighted(overlay, 0.15, frame_vis, 0.85, 0, frame_vis)

            # Borde del bounding box
            cv2.rectangle(frame_vis, (x1, y1), (x2, y2), color_bbox, 2)

            # ── Etiqueta superior: Clase + Confianza ──
            texto_clase = f"{det.etiqueta} {det.confianza:.0%}"
            (tw, th), _ = cv2.getTextSize(texto_clase, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(frame_vis, (x1, y1 - th - 10), (x1 + tw + 8, y1), color_bbox, -1)
            cv2.putText(
                frame_vis, texto_clase,
                (x1 + 4, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA,
            )

            # ── Centroide con cruz ──
            cx, cy = det.centroide_px
            cv2.drawMarker(
                frame_vis, (cx, cy),
                (0, 255, 255), cv2.MARKER_CROSS, 18, 2, cv2.LINE_AA,
            )

            # ── Etiqueta inferior: Color + Coordenadas ──
            partes_info = []
            if det.color_dominante != "desconocido":
                partes_info.append(f"C:{det.color_dominante}")
            if det.centroide_mm is not None:
                partes_info.append(f"({det.centroide_mm[0]:.0f}, {det.centroide_mm[1]:.0f}) mm")
            if det.altura_estimada_mm > 0:
                partes_info.append(f"Z:{det.altura_estimada_mm:.0f}")

            if partes_info:
                texto_info = " | ".join(partes_info)
                (tw2, th2), _ = cv2.getTextSize(texto_info, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
                # Fondo semi-transparente para la info
                overlay2 = frame_vis.copy()
                cv2.rectangle(overlay2, (x1, y2), (x1 + tw2 + 8, y2 + th2 + 10), (0, 0, 0), -1)
                cv2.addWeighted(overlay2, 0.6, frame_vis, 0.4, 0, frame_vis)
                cv2.putText(
                    frame_vis, texto_info,
                    (x1 + 4, y2 + th2 + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 255, 200), 1, cv2.LINE_AA,
                )

            # Marcar fuera de rango con X roja
            if det.fuera_de_rango:
                cv2.line(frame_vis, (x1, y1), (x2, y2), (0, 0, 255), 2, cv2.LINE_AA)
                cv2.line(frame_vis, (x2, y1), (x1, y2), (0, 0, 255), 2, cv2.LINE_AA)
                cv2.putText(
                    frame_vis, "FUERA DE RANGO",
                    (x1, y1 - th - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA,
                )

        return frame_vis

