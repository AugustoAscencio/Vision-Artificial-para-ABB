"""
Panel de Snapshot (Captura de Datos) — permite congelar el resultado del 
pipeline para inspeccionar y exportar datos sin que se actualicen en vivo.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog
)

from capa_interfaz.tema import Colores


class PanelSnapshot(QGroupBox):
    """
    Panel para controlar el modo Snapshot y exportación.

    Señales:
        tomar_snapshot(): Solicitud para congelar el frame actual.
        liberar_snapshot(): Solicitud para volver al modo en vivo.
        exportar_csv(str): Exportar snapshot a CSV.
        exportar_json(str): Exportar snapshot a JSON.
    """

    tomar_snapshot = pyqtSignal()
    liberar_snapshot = pyqtSignal()
    exportar_csv = pyqtSignal(str)
    exportar_json = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("📸  Captura de Datos (Snapshot)", parent)
        self._modo_snapshot = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── Instrucción ──
        lbl_info = QLabel(
            "Congela el frame actual para capturar sus datos,\n"
            "enviarlos uno a uno o exportarlos."
        )
        lbl_info.setStyleSheet(
            f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px;"
        )
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # ── Estado ──
        self._lbl_estado = QLabel("🟢 EN VIVO")
        self._lbl_estado.setStyleSheet(f"""
            QLabel {{
                color: {Colores.VERDE};
                font-weight: bold;
                font-size: 13px;
                padding: 4px;
                background-color: {Colores.FONDO_TARJETA};
                border-radius: 4px;
                text-align: center;
            }}
        """)
        layout.addWidget(self._lbl_estado)

        # ── Botones Control ──
        layout_control = QHBoxLayout()
        
        self._btn_capturar = QPushButton("📸 Capturar")
        self._btn_capturar.setProperty("clase", "verde")
        self._btn_capturar.clicked.connect(self._al_capturar)
        
        self._btn_liberar = QPushButton("▶ Reanudar")
        self._btn_liberar.setEnabled(False)
        self._btn_liberar.clicked.connect(self._al_liberar)
        
        layout_control.addWidget(self._btn_capturar)
        layout_control.addWidget(self._btn_liberar)
        layout.addLayout(layout_control)

        # ── Botones Exportar ──
        layout_export = QHBoxLayout()
        
        self._btn_csv = QPushButton("💾 CSV")
        self._btn_csv.setEnabled(False)
        self._btn_csv.clicked.connect(self._al_exportar_csv)
        
        self._btn_json = QPushButton("💾 JSON")
        self._btn_json.setEnabled(False)
        self._btn_json.clicked.connect(self._al_exportar_json)
        
        layout_export.addWidget(self._btn_csv)
        layout_export.addWidget(self._btn_json)
        layout.addLayout(layout_export)

    def _al_capturar(self):
        self._modo_snapshot = True
        self._btn_capturar.setEnabled(False)
        self._btn_liberar.setEnabled(True)
        self._btn_csv.setEnabled(True)
        self._btn_json.setEnabled(True)
        
        self._lbl_estado.setText("🔴 DATOS CAPTURADOS")
        self._lbl_estado.setStyleSheet(f"""
            QLabel {{
                color: {Colores.ERROR};
                font-weight: bold;
                font-size: 13px;
                padding: 4px;
                background-color: {Colores.FONDO_TARJETA};
                border-radius: 4px;
                text-align: center;
            }}
        """)
        self.tomar_snapshot.emit()

    def _al_liberar(self):
        self._modo_snapshot = False
        self._btn_capturar.setEnabled(True)
        self._btn_liberar.setEnabled(False)
        self._btn_csv.setEnabled(False)
        self._btn_json.setEnabled(False)
        
        self._lbl_estado.setText("🟢 EN VIVO")
        self._lbl_estado.setStyleSheet(f"""
            QLabel {{
                color: {Colores.VERDE};
                font-weight: bold;
                font-size: 13px;
                padding: 4px;
                background-color: {Colores.FONDO_TARJETA};
                border-radius: 4px;
                text-align: center;
            }}
        """)
        self.liberar_snapshot.emit()

    def _al_exportar_csv(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar a CSV", "captura_datos.csv", "Archivos CSV (*.csv)"
        )
        if ruta:
            self.exportar_csv.emit(ruta)

    def _al_exportar_json(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar a JSON", "captura_datos.json", "Archivos JSON (*.json)"
        )
        if ruta:
            self.exportar_json.emit(ruta)
