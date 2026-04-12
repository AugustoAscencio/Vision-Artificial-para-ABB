"""
Barra de estado inferior — muestra estados del sistema de un vistazo.
"""

from PyQt6.QtWidgets import QStatusBar, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt

from capa_interfaz.tema import Colores
from nucleo.modelos import EstadoConexion


class BarraEstado(QStatusBar):
    """Barra de estado inferior con indicadores del sistema."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QStatusBar {{
                background-color: {Colores.FONDO_PANEL};
                border-top: 1px solid {Colores.BORDE};
                padding: 2px 8px;
            }}
        """)

        # Contenedor con indicadores
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(20)

        # Indicadores
        self._lbl_camara = self._crear_indicador("📷 Apagada", Colores.TEXTO_SECUNDARIO)
        self._lbl_tcp = self._crear_indicador("🔌 Desconectado", Colores.TEXTO_SECUNDARIO)
        self._lbl_fps = self._crear_indicador("FPS: —", Colores.TEXTO_SECUNDARIO)
        self._lbl_calibracion = self._crear_indicador("📐 No calibrado", Colores.TEXTO_SECUNDARIO)
        self._lbl_objetos = self._crear_indicador("📦 0 objetos", Colores.TEXTO_SECUNDARIO)
        self._lbl_modelo = self._crear_indicador("🤖 —", Colores.TEXTO_SECUNDARIO)

        layout.addWidget(self._lbl_camara)
        layout.addWidget(self._lbl_tcp)
        layout.addWidget(self._lbl_fps)
        layout.addWidget(self._lbl_calibracion)
        layout.addWidget(self._lbl_objetos)
        layout.addWidget(self._lbl_modelo)
        layout.addStretch()

        self.addPermanentWidget(contenedor)

    def _crear_indicador(self, texto: str, color: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet(f"color: {color}; font-size: 12px; background: transparent; border: none;")
        return lbl

    def actualizar_camara(self, activa: bool):
        if activa:
            self._lbl_camara.setText("📷 Activa")
            self._lbl_camara.setStyleSheet(f"color: {Colores.VERDE}; font-size: 12px; background: transparent; border: none;")
        else:
            self._lbl_camara.setText("📷 Apagada")
            self._lbl_camara.setStyleSheet(f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 12px; background: transparent; border: none;")

    def actualizar_tcp(self, estado: EstadoConexion):
        textos = {
            EstadoConexion.DESCONECTADO: ("🔌 Desconectado", Colores.TEXTO_SECUNDARIO),
            EstadoConexion.CONECTANDO: ("🔌 Conectando...", Colores.AMARILLO),
            EstadoConexion.CONECTADO: ("🔌 Conectado", Colores.VERDE),
            EstadoConexion.ERROR: ("🔌 Error", Colores.ERROR),
            EstadoConexion.RECONECTANDO: ("🔌 Reconectando...", Colores.NARANJA),
        }
        texto, color = textos.get(estado, ("🔌 ?", Colores.TEXTO_SECUNDARIO))
        self._lbl_tcp.setText(texto)
        self._lbl_tcp.setStyleSheet(f"color: {color}; font-size: 12px; background: transparent; border: none;")

    def actualizar_fps(self, fps: float):
        color = Colores.VERDE if fps >= 15 else Colores.AMARILLO if fps >= 5 else Colores.ERROR
        self._lbl_fps.setText(f"FPS: {fps:.1f}")
        self._lbl_fps.setStyleSheet(f"color: {color}; font-size: 12px; background: transparent; border: none;")

    def actualizar_calibracion(self, calibrada: bool):
        if calibrada:
            self._lbl_calibracion.setText("📐 Calibrado")
            self._lbl_calibracion.setStyleSheet(f"color: {Colores.VERDE}; font-size: 12px; background: transparent; border: none;")
        else:
            self._lbl_calibracion.setText("📐 No calibrado")
            self._lbl_calibracion.setStyleSheet(f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 12px; background: transparent; border: none;")

    def actualizar_objetos(self, n: int):
        color = Colores.CYAN if n > 0 else Colores.TEXTO_SECUNDARIO
        self._lbl_objetos.setText(f"📦 {n} objetos")
        self._lbl_objetos.setStyleSheet(f"color: {color}; font-size: 12px; background: transparent; border: none;")

    def actualizar_modelo(self, nombre: str):
        self._lbl_modelo.setText(f"🤖 {nombre}")
        self._lbl_modelo.setStyleSheet(f"color: {Colores.MORADO}; font-size: 12px; background: transparent; border: none;")
