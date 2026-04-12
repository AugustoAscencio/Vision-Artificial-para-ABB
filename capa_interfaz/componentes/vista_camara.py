"""
Vista de cámara — muestra el feed en vivo con overlays de detección.
Compacta — limitada en alto para dar espacio a otros paneles.
"""

import cv2
import numpy as np
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from capa_interfaz.tema import Colores


class VistaCamara(QWidget):
    """
    Widget que muestra el feed de cámara en vivo.
    Escala automáticamente manteniendo el aspect ratio.
    Muestra un placeholder cuando no hay feed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ultimo_pixmap: QPixmap | None = None
        self._fps = 0.0
        self._n_objetos = 0
        self._calibrada = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label_imagen = QLabel()
        self._label_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_imagen.setMinimumSize(250, 180)
        self._label_imagen.setStyleSheet(f"""
            QLabel {{
                background-color: {Colores.FONDO_TARJETA};
                border: 2px solid {Colores.BORDE};
                border-radius: 8px;
                color: {Colores.TEXTO_SECUNDARIO};
                font-size: 14px;
            }}
        """)

        # Placeholder
        self._label_imagen.setText(
            "Camara no iniciada\n\n"
            "Presiona 'Iniciar' para comenzar"
        )

        layout.addWidget(self._label_imagen)

    @pyqtSlot(object)
    def actualizar_frame(self, frame: np.ndarray):
        """
        Actualiza la imagen con un nuevo frame BGR de OpenCV.
        Dibuja información de estado directamente en el frame.
        """
        if frame is None:
            return

        try:
            # Dibujar HUD de información sobre el frame
            frame_hud = self._dibujar_hud(frame)

            # BGR -> RGB
            frame_rgb = cv2.cvtColor(frame_hud, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_por_linea = ch * w

            # Crear QImage
            imagen_qt = QImage(
                frame_rgb.data,
                w, h,
                bytes_por_linea,
                QImage.Format.Format_RGB888,
            )

            # Escalar al tamaño del label manteniendo aspect ratio
            pixmap = QPixmap.fromImage(imagen_qt)
            tamanio_label = self._label_imagen.size()
            pixmap_escalado = pixmap.scaled(
                tamanio_label,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            self._label_imagen.setPixmap(pixmap_escalado)
            self._ultimo_pixmap = pixmap_escalado

        except Exception:
            pass  # No bloquear la UI

    def _dibujar_hud(self, frame: np.ndarray) -> np.ndarray:
        """Dibuja información de estado (FPS, calibración, objetos) sobre el frame."""
        vis = frame.copy()
        h, w = vis.shape[:2]

        # Barra semi-transparente arriba
        overlay = vis.copy()
        cv2.rectangle(overlay, (0, 0), (w, 32), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, vis, 0.4, 0, vis)

        # FPS
        cv2.putText(vis, f"FPS: {self._fps:.1f}", (8, 22),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 200), 1)

        # Estado calibración
        if self._calibrada:
            cv2.putText(vis, "CALIBRADO", (w - 140, 22),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        else:
            cv2.putText(vis, "SIN CALIBRAR", (w - 160, 22),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 150, 255), 1)

        # Objetos detectados
        cv2.putText(vis, f"Objetos: {self._n_objetos}", (w // 2 - 50, 22),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1)

        return vis

    @pyqtSlot(float)
    def actualizar_fps(self, fps: float):
        """Almacena el FPS actual para el HUD."""
        self._fps = fps

    def actualizar_estado(self, n_objetos: int = 0, calibrada: bool = False):
        """Actualiza datos del HUD."""
        self._n_objetos = n_objetos
        self._calibrada = calibrada

    def limpiar(self):
        """Limpia la vista y muestra el placeholder."""
        self._label_imagen.clear()
        self._label_imagen.setText(
            "Camara detenida\n\n"
            "Presiona 'Iniciar' para reanudar"
        )
        self._ultimo_pixmap = None
