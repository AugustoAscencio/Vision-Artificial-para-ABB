"""
Panel de depuracion expandible — muestra datos crudos del sistema en tiempo real.
Modo experto para inspeccionar coordenadas, ArUco, TCP y pipeline.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHeaderView,
)

from capa_interfaz.tema import Colores


class PanelDebug(QGroupBox):
    """
    Panel colapsable con datos del sistema en tiempo real.
    Muestra: coordenadas px/mm, ArUco IDs, calibracion, TCP, YOLO timing.
    """

    def __init__(self, parent=None):
        super().__init__("Panel Debug (Modo Experto)", parent)
        self.setCheckable(True)
        self.setChecked(False)
        self._ultimo_tcp_enviado = ""
        self._ultimo_tcp_recibido = ""
        self._setup_ui()

        # Conectar toggle
        self.toggled.connect(self._al_toggle)
        self._contenido.setVisible(False)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 20, 6, 6)

        self._contenido = QGroupBox()
        self._contenido.setStyleSheet("QGroupBox { border: none; }")
        layout_contenido = QVBoxLayout(self._contenido)
        layout_contenido.setContentsMargins(0, 0, 0, 0)
        layout_contenido.setSpacing(4)

        # ── Secciones de datos ──

        # Pipeline info
        self._lbl_pipeline = QLabel("Pipeline: --")
        self._lbl_pipeline.setStyleSheet(f"color: {Colores.CYAN}; font-size: 11px;")
        self._lbl_pipeline.setWordWrap(True)
        layout_contenido.addWidget(self._lbl_pipeline)

        # Calibracion
        self._lbl_calibracion = QLabel("Calibracion: --")
        self._lbl_calibracion.setStyleSheet(f"color: {Colores.AMARILLO}; font-size: 11px;")
        self._lbl_calibracion.setWordWrap(True)
        layout_contenido.addWidget(self._lbl_calibracion)

        # ArUco
        self._lbl_aruco = QLabel("ArUco: --")
        self._lbl_aruco.setStyleSheet(f"color: {Colores.VERDE}; font-size: 11px;")
        self._lbl_aruco.setWordWrap(True)
        layout_contenido.addWidget(self._lbl_aruco)

        # TCP
        self._lbl_tcp = QLabel("TCP: --")
        self._lbl_tcp.setStyleSheet(f"color: {Colores.NARANJA}; font-size: 11px;")
        self._lbl_tcp.setWordWrap(True)
        layout_contenido.addWidget(self._lbl_tcp)

        # Arbol de detecciones detallado
        lbl_det = QLabel("Detecciones detalladas:")
        lbl_det.setStyleSheet(f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px; font-weight: bold;")
        layout_contenido.addWidget(lbl_det)

        self._arbol_detecciones = QTreeWidget()
        self._arbol_detecciones.setHeaderLabels([
            "Objeto", "Pixeles (cx,cy)", "Mundo (X,Y) mm",
            "Z mm", "Color", "Conf", "Rango"
        ])
        self._arbol_detecciones.setMaximumHeight(180)
        self._arbol_detecciones.setAlternatingRowColors(True)
        self._arbol_detecciones.setRootIsDecorated(False)
        self._arbol_detecciones.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {Colores.FONDO_TARJETA};
                color: {Colores.TEXTO_PRIMARIO};
                font-size: 11px;
                border: 1px solid {Colores.BORDE};
                alternate-background-color: {Colores.FONDO_PANEL};
            }}
            QHeaderView::section {{
                background-color: {Colores.FONDO_PANEL};
                color: {Colores.TEXTO_SECUNDARIO};
                padding: 3px;
                border: 1px solid {Colores.BORDE};
                font-size: 10px;
            }}
        """)
        header = self._arbol_detecciones.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout_contenido.addWidget(self._arbol_detecciones)

        layout.addWidget(self._contenido)

    def _al_toggle(self, visible: bool):
        """Muestra/oculta el contenido del panel."""
        self._contenido.setVisible(visible)

    @pyqtSlot(object)
    def actualizar(self, resultado):
        """
        Actualiza todos los datos del panel con un ResultadoFrame.
        Solo se ejecuta si el panel esta visible.
        """
        if not self.isChecked():
            return

        # Pipeline
        self._lbl_pipeline.setText(
            f"Pipeline: {resultado.fps:.1f} FPS | "
            f"{len(resultado.detecciones)} objs | "
            f"Homografia: {'SI' if resultado.homografia_activa else 'NO'}"
        )

        # ArUco
        if resultado.marcadores_aruco:
            ids = [str(m.id) for m in resultado.marcadores_aruco]
            posiciones = []
            for m in resultado.marcadores_aruco:
                px_str = f"px({m.centro_px[0]},{m.centro_px[1]})"
                if m.posicion_mundo_mm:
                    px_str += f" -> ({m.posicion_mundo_mm[0]:.0f},{m.posicion_mundo_mm[1]:.0f})mm"
                posiciones.append(f"ID{m.id}: {px_str}")
            self._lbl_aruco.setText(f"ArUco: {', '.join(posiciones)}")
        else:
            self._lbl_aruco.setText("ArUco: Ninguno detectado")

        # Detecciones detalladas
        self._arbol_detecciones.clear()
        for det in resultado.detecciones:
            item = QTreeWidgetItem([
                det.etiqueta,
                f"({det.centroide_px[0]}, {det.centroide_px[1]})",
                f"({det.centroide_mm[0]:.1f}, {det.centroide_mm[1]:.1f})" if det.centroide_mm else "N/A",
                f"{det.altura_estimada_mm:.1f}" if det.altura_estimada_mm > 0 else "N/A",
                det.color_dominante,
                f"{det.confianza:.0%}",
                "FUERA" if det.fuera_de_rango else "OK",
            ])
            # Colorear fila si esta fuera de rango
            if det.fuera_de_rango:
                for col in range(7):
                    item.setForeground(col, Qt.GlobalColor.red)
            self._arbol_detecciones.addTopLevelItem(item)

        # TCP
        tcp_text = "TCP: "
        if self._ultimo_tcp_enviado:
            tcp_text += f"Env: {self._ultimo_tcp_enviado[:80]} | "
        if self._ultimo_tcp_recibido:
            tcp_text += f"Rec: {self._ultimo_tcp_recibido[:80]}"
        if not self._ultimo_tcp_enviado and not self._ultimo_tcp_recibido:
            tcp_text += "Sin actividad"
        self._lbl_tcp.setText(tcp_text)

    def actualizar_calibracion(self, calibrada: bool, error_rms: float = 0.0, n_marcadores: int = 0):
        """Actualiza info de calibracion."""
        if calibrada:
            self._lbl_calibracion.setText(
                f"Calibracion: ACTIVA | Error RMS: {error_rms:.3f} px | Marcadores: {n_marcadores}"
            )
        else:
            self._lbl_calibracion.setText(
                f"Calibracion: INACTIVA | Marcadores vistos: {n_marcadores}"
            )

    def actualizar_tcp_enviado(self, mensaje: str):
        """Actualiza el ultimo mensaje TCP enviado."""
        self._ultimo_tcp_enviado = mensaje

    def actualizar_tcp_recibido(self, mensaje: str):
        """Actualiza el ultimo mensaje TCP recibido."""
        self._ultimo_tcp_recibido = mensaje
