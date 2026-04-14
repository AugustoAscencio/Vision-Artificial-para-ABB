"""
Ventana principal del sistema de vision artificial ABB.
Layout: Camara + Vista 2D cenital + datos + logs + debug.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QScrollArea,
)

from capa_interfaz.tema import Colores
from capa_interfaz.componentes.vista_camara import VistaCamara
from capa_interfaz.componentes.vista_2d import Vista2D
from capa_interfaz.componentes.panel_conexion import PanelConexion
from capa_interfaz.componentes.panel_control import PanelControl
from capa_interfaz.componentes.panel_calibracion import PanelCalibracion
from capa_interfaz.componentes.panel_deteccion import PanelDeteccion
from capa_interfaz.componentes.selector_modelo import SelectorModelo
from capa_interfaz.componentes.panel_logs import PanelLogs
from capa_interfaz.componentes.panel_debug import PanelDebug
from capa_interfaz.componentes.barra_estado import BarraEstado


class VentanaPrincipal(QMainWindow):
    """
    Dashboard con cámara real + vista 2D cenital + datos.

    +---------------+------------------+------------------+
    |  CONTROL      |  CÁMARA          |  DETECCIÓN       |
    |  ----------   |  (feed real)     |  (tabla grande)  |
    |  Conexión     |                  |  X,Y,Z,Color     |
    |  Calibración  |  VISTA 2D        |                  |
    |  Control      |  (cenital)       |  Modelo IA       |
    |  (overlays)   |  ArUco + objetos |                  |
    |               |------------------+                  |
    |               |  LOGS + DEBUG    |                  |
    +---------------+------------------+------------------+
    |               BARRA DE ESTADO                       |
    +-----------------------------------------------------+
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vision Artificial ABB — Sistema Pick & Place")
        self.setMinimumSize(1280, 720)
        self.resize(1500, 880)

        # Crear componentes
        self.vista_camara = VistaCamara()
        self.vista_2d = Vista2D()
        self.panel_conexion = PanelConexion()
        self.panel_control = PanelControl()
        self.panel_calibracion = PanelCalibracion()
        self.panel_deteccion = PanelDeteccion()
        self.selector_modelo = SelectorModelo()
        self.panel_logs = PanelLogs()
        self.panel_debug = PanelDebug()
        self.barra_estado = BarraEstado()

        self._setup_ui()

    def _setup_ui(self):
        """Construye el layout del dashboard."""
        widget_central = QWidget()
        self.setCentralWidget(widget_central)

        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(8, 8, 8, 8)
        layout_principal.setSpacing(8)

        # =============================================
        # Columna Izquierda: Controles (fija, 300px)
        # =============================================
        col_izq = QWidget()
        layout_izq = QVBoxLayout(col_izq)
        layout_izq.setContentsMargins(0, 0, 0, 0)
        layout_izq.setSpacing(0)

        scroll_izq = QScrollArea()
        scroll_izq.setWidgetResizable(True)
        scroll_izq.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_izq.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        contenido_izq = QWidget()
        layout_contenido_izq = QVBoxLayout(contenido_izq)
        layout_contenido_izq.setContentsMargins(0, 0, 4, 0)
        layout_contenido_izq.setSpacing(6)
        layout_contenido_izq.addWidget(self.panel_conexion)
        layout_contenido_izq.addWidget(self.panel_calibracion)
        layout_contenido_izq.addWidget(self.panel_control)
        layout_contenido_izq.addStretch()

        scroll_izq.setWidget(contenido_izq)
        layout_izq.addWidget(scroll_izq)
        col_izq.setFixedWidth(300)

        # =============================================
        # Columna Central: Cámara + Vista 2D + Logs
        # =============================================
        col_centro = QWidget()
        layout_centro = QVBoxLayout(col_centro)
        layout_centro.setContentsMargins(0, 0, 0, 0)
        layout_centro.setSpacing(6)

        # Splitter vertical: Cámara | Vista 2D | Logs + Debug
        splitter_centro = QSplitter(Qt.Orientation.Vertical)

        # Cámara — feed real
        self.vista_camara.setMaximumHeight(380)
        splitter_centro.addWidget(self.vista_camara)

        # Vista 2D cenital — segunda cámara virtual
        self.vista_2d.setMinimumHeight(180)
        splitter_centro.addWidget(self.vista_2d)

        # Contenedor inferior: Logs + Debug
        contenedor_inferior = QWidget()
        layout_inferior = QVBoxLayout(contenedor_inferior)
        layout_inferior.setContentsMargins(0, 0, 0, 0)
        layout_inferior.setSpacing(4)
        layout_inferior.addWidget(self.panel_logs, stretch=2)
        layout_inferior.addWidget(self.panel_debug, stretch=1)
        splitter_centro.addWidget(contenedor_inferior)

        # Proporciones: 30% cámara, 35% Vista 2D, 35% logs+debug
        splitter_centro.setStretchFactor(0, 2)
        splitter_centro.setStretchFactor(1, 3)
        splitter_centro.setStretchFactor(2, 2)

        layout_centro.addWidget(splitter_centro)

        # =============================================
        # Columna Derecha: Detecciones + Modelo (fija, 340px)
        # =============================================
        col_der = QWidget()
        layout_der = QVBoxLayout(col_der)
        layout_der.setContentsMargins(0, 0, 0, 0)
        layout_der.setSpacing(6)

        scroll_der = QScrollArea()
        scroll_der.setWidgetResizable(True)
        scroll_der.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_der.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        contenido_der = QWidget()
        layout_contenido_der = QVBoxLayout(contenido_der)
        layout_contenido_der.setContentsMargins(4, 0, 0, 0)
        layout_contenido_der.setSpacing(6)

        # Panel de detección ocupa la mayor parte
        layout_contenido_der.addWidget(self.panel_deteccion, stretch=3)
        layout_contenido_der.addWidget(self.selector_modelo, stretch=0)

        scroll_der.setWidget(contenido_der)
        layout_der.addWidget(scroll_der)
        col_der.setFixedWidth(340)

        # =============================================
        # Armar layout horizontal
        # =============================================
        splitter_h = QSplitter(Qt.Orientation.Horizontal)
        splitter_h.addWidget(col_izq)
        splitter_h.addWidget(col_centro)
        splitter_h.addWidget(col_der)
        splitter_h.setStretchFactor(0, 0)  # Izq fija
        splitter_h.setStretchFactor(1, 1)  # Centro expandible
        splitter_h.setStretchFactor(2, 0)  # Der fija

        layout_principal.addWidget(splitter_h)

        # Barra de estado
        self.setStatusBar(self.barra_estado)
