"""
Panel de logs en tiempo real — muestra registros con colores por nivel.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QComboBox, QLabel,
)
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor

from capa_interfaz.tema import Colores


# Colores por nivel de log
_COLORES_NIVEL = {
    "DEBUG":    "#6e7681",
    "INFO":     "#e6edf3",
    "WARNING":  "#d29922",
    "ERROR":    "#f85149",
    "CRITICAL": "#ff1744",
}

_MAX_LINEAS = 1000


class PanelLogs(QGroupBox):
    """Panel de visualización de logs en tiempo real con filtros y colores."""

    def __init__(self, parent=None):
        super().__init__("📝  Registro", parent)
        self._auto_scroll = True
        self._filtro_nivel = "DEBUG"
        self._conteo_lineas = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # ── Controles ──
        layout_controles = QHBoxLayout()

        self._combo_filtro = QComboBox()
        self._combo_filtro.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self._combo_filtro.setCurrentText("DEBUG")
        self._combo_filtro.setFixedWidth(100)
        self._combo_filtro.currentTextChanged.connect(self._al_cambiar_filtro)

        self._btn_limpiar = QPushButton("🗑")
        self._btn_limpiar.setFixedWidth(36)
        self._btn_limpiar.setToolTip("Limpiar logs")
        self._btn_limpiar.clicked.connect(self.limpiar)

        self._btn_scroll = QPushButton("⬇")
        self._btn_scroll.setFixedWidth(36)
        self._btn_scroll.setToolTip("Auto-scroll")
        self._btn_scroll.setCheckable(True)
        self._btn_scroll.setChecked(True)
        self._btn_scroll.clicked.connect(
            lambda checked: setattr(self, '_auto_scroll', checked)
        )

        layout_controles.addWidget(QLabel("Filtro:"))
        layout_controles.addWidget(self._combo_filtro)
        layout_controles.addStretch()
        layout_controles.addWidget(self._btn_scroll)
        layout_controles.addWidget(self._btn_limpiar)
        layout.addLayout(layout_controles)

        # ── Área de texto ──
        self._texto = QTextEdit()
        self._texto.setReadOnly(True)
        self._texto.setMinimumHeight(100)
        layout.addWidget(self._texto)

    @pyqtSlot(str, str)
    def agregar_log(self, nivel: str, mensaje: str):
        """
        Agrega una línea de log con color según el nivel.

        Args:
            nivel: DEBUG, INFO, WARNING, ERROR, CRITICAL
            mensaje: Texto formateado del log.
        """
        # Filtrar por nivel
        niveles_orden = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        idx_filtro = niveles_orden.index(self._filtro_nivel) if self._filtro_nivel in niveles_orden else 0
        idx_nivel = niveles_orden.index(nivel) if nivel in niveles_orden else 0
        if idx_nivel < idx_filtro:
            return

        # Limitar líneas
        self._conteo_lineas += 1
        if self._conteo_lineas > _MAX_LINEAS:
            cursor = self._texto.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, 100)
            cursor.removeSelectedText()
            self._conteo_lineas -= 100

        # Insertar con color
        color = _COLORES_NIVEL.get(nivel, Colores.TEXTO_PRIMARIO)
        formato = QTextCharFormat()
        formato.setForeground(QColor(color))

        cursor = self._texto.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(mensaje + "\n", formato)

        # Auto-scroll
        if self._auto_scroll:
            scrollbar = self._texto.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _al_cambiar_filtro(self, nivel: str):
        self._filtro_nivel = nivel

    def limpiar(self):
        """Limpia todos los logs."""
        self._texto.clear()
        self._conteo_lineas = 0
