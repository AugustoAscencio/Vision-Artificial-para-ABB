"""
Selector de modelo YOLO — permite elegir modelos .pt del directorio o desde archivo.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QFileDialog,
)

from capa_interfaz.tema import Colores


class SelectorModelo(QGroupBox):
    """
    Selector de modelo YOLO con lista de modelos .pt disponibles
    y botón para cargar modelos desde cualquier ubicación.

    Señales:
        modelo_seleccionado(str): Ruta del modelo seleccionado.
        recargar_modelos(): Solicita recargar lista de modelos.
    """

    modelo_seleccionado = pyqtSignal(str)
    recargar_modelos = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Modelo de Detección (IA)", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── ComboBox de modelos ──
        self._combo_modelos = QComboBox()
        layout.addWidget(self._combo_modelos)

        # ── Botones ──
        layout_btns = QHBoxLayout()

        self._btn_aplicar = QPushButton("Aplicar")
        self._btn_aplicar.setProperty("clase", "verde")
        self._btn_aplicar.setToolTip("Cargar el modelo seleccionado en el combo")
        self._btn_aplicar.clicked.connect(self._al_aplicar)

        self._btn_recargar = QPushButton("Recargar")
        self._btn_recargar.setToolTip("Recargar lista de modelos del directorio modelos/")
        self._btn_recargar.clicked.connect(lambda: self.recargar_modelos.emit())

        layout_btns.addWidget(self._btn_aplicar)
        layout_btns.addWidget(self._btn_recargar)
        layout.addLayout(layout_btns)

        # ── Botón examinar (cargar desde cualquier ruta) ──
        self._btn_examinar = QPushButton("Examinar archivo .pt ...")
        self._btn_examinar.setToolTip("Cargar un modelo .pt desde cualquier ubicacion")
        self._btn_examinar.clicked.connect(self._al_examinar)
        layout.addWidget(self._btn_examinar)

        # ── Modelo activo ──
        self._lbl_activo = QLabel("Activo: --")
        self._lbl_activo.setStyleSheet(f"color: {Colores.VERDE}; font-size: 12px; font-weight: bold;")
        self._lbl_activo.setWordWrap(True)
        layout.addWidget(self._lbl_activo)

        # ── Info ──
        self._lbl_info = QLabel("")
        self._lbl_info.setStyleSheet(f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px;")
        self._lbl_info.setWordWrap(True)
        layout.addWidget(self._lbl_info)

    def establecer_modelos(self, modelos: list[dict]):
        """
        Puebla el combo con modelos disponibles.
        Cada modelo: {"nombre": "yolov8n.pt", "ruta": "...", "tamano_mb": 6.2}
        """
        self._combo_modelos.blockSignals(True)
        self._combo_modelos.clear()

        # Siempre agregar opción de descarga automática
        self._combo_modelos.addItem("yolov8n.pt (descarga auto)", "yolov8n.pt")

        if modelos:
            for m in modelos:
                texto = f"{m['nombre']} ({m['tamano_mb']:.1f} MB)"
                self._combo_modelos.addItem(texto, m["ruta"])
            self._lbl_info.setText(f"{len(modelos)} modelo(s) en directorio modelos/")
        else:
            self._lbl_info.setText("Sin modelos locales en modelos/")

        self._combo_modelos.blockSignals(False)

    def _al_aplicar(self):
        """Aplica el modelo seleccionado en el combo."""
        ruta = self._combo_modelos.currentData()
        if ruta:
            self.modelo_seleccionado.emit(ruta)
            self._lbl_info.setText(f"Cargando: {self._combo_modelos.currentText()}")

    def _al_examinar(self):
        """Abre un diálogo para seleccionar un archivo .pt desde cualquier ubicación."""
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar modelo YOLO (.pt)",
            "",
            "Modelos YOLO (*.pt);;Todos los archivos (*.*)",
        )
        if ruta:
            self.modelo_seleccionado.emit(ruta)
            self._lbl_info.setText(f"Archivo: {ruta}")

    def actualizar_modelo_activo(self, nombre: str):
        """Muestra el nombre del modelo actualmente cargado."""
        self._lbl_activo.setText(f"Activo: {nombre}")
