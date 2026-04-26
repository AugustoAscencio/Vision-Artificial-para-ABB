"""
Panel de puntos mundo ArUco — tabla editable para configurar las
posiciones reales (mm) de los 4 marcadores sin tocar código.

Los cambios se aplican al instante al hacer clic en "Aplicar".
"""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)

from capa_interfaz.tema import Colores
from capa_configuracion.ajustes import PuntoMundoAruco


class PanelPuntosMundo(QGroupBox):
    """
    Tabla editable con los 4 puntos mundo ArUco (ID, X_mm, Y_mm).

    Señales:
        puntos_cambiados(list): Lista de PuntoMundoAruco actualizada.
    """

    puntos_cambiados = pyqtSignal(object)  # list[PuntoMundoAruco]

    def __init__(self, parent=None):
        super().__init__("🌍  Puntos Mundo ArUco", parent)
        self._puntos_originales: list[PuntoMundoAruco] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── Instrucción ──
        lbl_info = QLabel("Coordenadas reales (mm) de cada marcador:")
        lbl_info.setStyleSheet(
            f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px;"
        )
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # ── Tabla ──
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(3)
        self._tabla.setHorizontalHeaderLabels(["ID", "X (mm)", "Y (mm)"])
        self._tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._tabla.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tabla.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._tabla.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setMinimumHeight(130)
        self._tabla.setMaximumHeight(170)
        layout.addWidget(self._tabla)

        # ── Botones ──
        layout_btns = QHBoxLayout()

        self._btn_aplicar = QPushButton("✔ Aplicar")
        self._btn_aplicar.setProperty("clase", "verde")
        self._btn_aplicar.setToolTip(
            "Aplicar los valores editados inmediatamente "
            "(recalcula homografía y rejilla)"
        )
        self._btn_aplicar.clicked.connect(self._al_aplicar)

        self._btn_restaurar = QPushButton("↩ Restaurar")
        self._btn_restaurar.setToolTip(
            "Restaurar los valores originales del archivo YAML"
        )
        self._btn_restaurar.clicked.connect(self._al_restaurar)

        layout_btns.addWidget(self._btn_aplicar)
        layout_btns.addWidget(self._btn_restaurar)
        layout.addLayout(layout_btns)

    # ═══════════════════════════════════════════════════════
    # API pública
    # ═══════════════════════════════════════════════════════

    def establecer_puntos(self, puntos: list[PuntoMundoAruco]):
        """Carga los puntos mundo iniciales (desde config YAML)."""
        self._puntos_originales = [
            PuntoMundoAruco(id=p.id, x_mm=p.x_mm, y_mm=p.y_mm)
            for p in puntos
        ]
        self._llenar_tabla(puntos)

    # ═══════════════════════════════════════════════════════
    # Internos
    # ═══════════════════════════════════════════════════════

    def _llenar_tabla(self, puntos: list[PuntoMundoAruco]):
        """Rellena la tabla con los valores dados."""
        self._tabla.setRowCount(len(puntos))
        for fila, p in enumerate(puntos):
            # ID — solo lectura
            item_id = QTableWidgetItem(str(p.id))
            item_id.setFlags(item_id.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_id.setForeground(
                __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(
                    Colores.CYAN
                )
            )
            self._tabla.setItem(fila, 0, item_id)

            # X
            item_x = QTableWidgetItem(f"{p.x_mm:.2f}")
            item_x.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tabla.setItem(fila, 1, item_x)

            # Y
            item_y = QTableWidgetItem(f"{p.y_mm:.2f}")
            item_y.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tabla.setItem(fila, 2, item_y)

    def _leer_puntos_de_tabla(self) -> list[PuntoMundoAruco]:
        """Lee los valores actuales de la tabla y retorna la lista."""
        puntos = []
        for fila in range(self._tabla.rowCount()):
            item_id = self._tabla.item(fila, 0)
            item_x = self._tabla.item(fila, 1)
            item_y = self._tabla.item(fila, 2)
            if item_id and item_x and item_y:
                try:
                    puntos.append(PuntoMundoAruco(
                        id=int(item_id.text()),
                        x_mm=float(item_x.text()),
                        y_mm=float(item_y.text()),
                    ))
                except ValueError:
                    pass  # Ignorar valores no numéricos
        return puntos

    def _al_aplicar(self):
        """Lee los valores de la tabla y emite la señal."""
        puntos = self._leer_puntos_de_tabla()
        if puntos:
            self.puntos_cambiados.emit(puntos)

    def _al_restaurar(self):
        """Restaura los valores originales del YAML."""
        self._llenar_tabla(self._puntos_originales)
        self.puntos_cambiados.emit(list(self._puntos_originales))
