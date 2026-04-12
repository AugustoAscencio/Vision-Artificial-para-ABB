"""
Panel de detección — tabla de objetos detectados con coordenadas, color y estado.
"""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)
from PyQt6.QtGui import QColor

from capa_interfaz.tema import Colores
from nucleo.modelos import DeteccionObjeto


class PanelDeteccion(QGroupBox):
    """
    Tabla de objetos detectados con datos completos.

    Señales:
        enviar_seleccionado(int): Enviar objeto del índice seleccionado.
        enviar_todos(): Enviar todos los objetos.
    """

    enviar_seleccionado = pyqtSignal(int)
    enviar_todos = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("📦  Detecciones", parent)
        self._detecciones: list[DeteccionObjeto] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── Conteo ──
        self._lbl_conteo = QLabel("Objetos: 0")
        self._lbl_conteo.setStyleSheet(f"""
            color: {Colores.CYAN};
            font-weight: bold;
            font-size: 14px;
        """)
        layout.addWidget(self._lbl_conteo)

        # ── Tabla ──
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(6)
        self._tabla.setHorizontalHeaderLabels([
            "Tipo", "Conf", "X(mm)", "Y(mm)", "Z(mm)", "Color"
        ])
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tabla.setMinimumHeight(120)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setAlternatingRowColors(True)
        layout.addWidget(self._tabla)

        # ── Botones de envío ──
        layout_btns = QHBoxLayout()
        self._btn_enviar_sel = QPushButton("📤 Enviar seleccionado")
        self._btn_enviar_sel.clicked.connect(self._al_enviar_seleccionado)
        self._btn_enviar_sel.setEnabled(False)

        self._btn_enviar_todos = QPushButton("📤 Enviar todos")
        self._btn_enviar_todos.setProperty("clase", "verde")
        self._btn_enviar_todos.clicked.connect(lambda: self.enviar_todos.emit())
        self._btn_enviar_todos.setEnabled(False)

        layout_btns.addWidget(self._btn_enviar_sel)
        layout_btns.addWidget(self._btn_enviar_todos)
        layout.addLayout(layout_btns)

    def actualizar_detecciones(self, detecciones: list[DeteccionObjeto]):
        """Actualiza la tabla con las detecciones actuales."""
        self._detecciones = detecciones
        self._lbl_conteo.setText(f"Objetos: {len(detecciones)}")

        self._tabla.setRowCount(len(detecciones))

        for fila, det in enumerate(detecciones):
            # Tipo
            item_tipo = QTableWidgetItem(det.etiqueta)
            self._tabla.setItem(fila, 0, item_tipo)

            # Confianza
            item_conf = QTableWidgetItem(f"{det.confianza:.0%}")
            item_conf.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tabla.setItem(fila, 1, item_conf)

            # Coordenadas mundo
            if det.centroide_mm is not None:
                x_txt = f"{det.centroide_mm[0]:.1f}"
                y_txt = f"{det.centroide_mm[1]:.1f}"
            else:
                x_txt = "—"
                y_txt = "—"

            item_x = QTableWidgetItem(x_txt)
            item_x.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tabla.setItem(fila, 2, item_x)

            item_y = QTableWidgetItem(y_txt)
            item_y.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tabla.setItem(fila, 3, item_y)

            item_z = QTableWidgetItem(f"{det.altura_estimada_mm:.1f}")
            item_z.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tabla.setItem(fila, 4, item_z)

            # Color con fondo visual
            item_color = QTableWidgetItem(det.color_dominante)
            item_color.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            r, g, b = det.color_rgb
            item_color.setBackground(QColor(r, g, b, 80))
            self._tabla.setItem(fila, 5, item_color)

            # Marcar fuera de rango
            if det.fuera_de_rango:
                for col in range(6):
                    item = self._tabla.item(fila, col)
                    if item:
                        item.setForeground(QColor(Colores.ERROR))

        hay_datos = len(detecciones) > 0
        self._btn_enviar_todos.setEnabled(hay_datos)
        self._btn_enviar_sel.setEnabled(hay_datos)

    def _al_enviar_seleccionado(self):
        fila = self._tabla.currentRow()
        if fila >= 0:
            self.enviar_seleccionado.emit(fila)

    def obtener_deteccion(self, indice: int) -> DeteccionObjeto | None:
        """Retorna la detección en el índice dado."""
        if 0 <= indice < len(self._detecciones):
            return self._detecciones[indice]
        return None
