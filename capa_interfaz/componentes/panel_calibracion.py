"""
Panel de calibración ArUco — controla la calibración de homografía.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton,
)

from capa_interfaz.tema import Colores


class PanelCalibracion(QGroupBox):
    """
    Panel para calibración con marcadores ArUco.

    Señales:
        solicitar_calibracion(): Calibrar usando frame actual.
        cargar_calibracion(): Cargar calibración guardada.
        guardar_calibracion(): Guardar calibración actual.
    """

    solicitar_calibracion = pyqtSignal()
    cargar_calibracion = pyqtSignal()
    guardar_calibracion = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("📐  Calibración ArUco", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── Estado de calibración ──
        self._lbl_estado = QLabel("✖  No calibrado")
        self._lbl_estado.setStyleSheet(f"""
            QLabel {{
                color: {Colores.ERROR};
                font-weight: bold;
                font-size: 13px;
                padding: 5px;
                background-color: {Colores.FONDO_TARJETA};
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self._lbl_estado)

        # ── Info marcadores ──
        self._lbl_marcadores = QLabel("Marcadores: 0 detectados")
        self._lbl_marcadores.setStyleSheet(f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px;")
        layout.addWidget(self._lbl_marcadores)

        # ── Botón calibrar ──
        self._btn_calibrar = QPushButton("🎯  Calibrar con ArUco")
        self._btn_calibrar.setProperty("clase", "verde")
        self._btn_calibrar.clicked.connect(lambda: self.solicitar_calibracion.emit())
        layout.addWidget(self._btn_calibrar)

        # ── Botones guardar/cargar ──
        layout_io = QHBoxLayout()
        self._btn_cargar = QPushButton("📂 Cargar")
        self._btn_cargar.clicked.connect(lambda: self.cargar_calibracion.emit())
        self._btn_guardar = QPushButton("💾 Guardar")
        self._btn_guardar.clicked.connect(lambda: self.guardar_calibracion.emit())
        self._btn_guardar.setEnabled(False)
        layout_io.addWidget(self._btn_cargar)
        layout_io.addWidget(self._btn_guardar)
        layout.addLayout(layout_io)

        # ── Error reproyección ──
        self._lbl_error = QLabel("")
        self._lbl_error.setStyleSheet(f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px;")
        layout.addWidget(self._lbl_error)

    def actualizar_estado(self, calibrada: bool, n_marcadores: int = 0, error_rms: float = 0.0):
        """Actualiza la visualización del estado de calibración."""
        if calibrada:
            self._lbl_estado.setText("✔  Calibrado")
            self._lbl_estado.setStyleSheet(f"""
                QLabel {{
                    color: {Colores.VERDE};
                    font-weight: bold;
                    font-size: 13px;
                    padding: 5px;
                    background-color: {Colores.FONDO_TARJETA};
                    border-radius: 6px;
                }}
            """)
            self._btn_guardar.setEnabled(True)
            self._lbl_error.setText(f"Error RMS: {error_rms:.2f} mm")
        else:
            self._lbl_estado.setText("✖  No calibrado")
            self._lbl_estado.setStyleSheet(f"""
                QLabel {{
                    color: {Colores.ERROR};
                    font-weight: bold;
                    font-size: 13px;
                    padding: 5px;
                    background-color: {Colores.FONDO_TARJETA};
                    border-radius: 6px;
                }}
            """)
            self._btn_guardar.setEnabled(False)
            self._lbl_error.setText("")

        self._lbl_marcadores.setText(f"Marcadores: {n_marcadores} detectados")

    def actualizar_conteo_marcadores(self, n: int):
        """Actualiza el conteo de marcadores en vivo."""
        self._lbl_marcadores.setText(f"Marcadores: {n} detectados")
