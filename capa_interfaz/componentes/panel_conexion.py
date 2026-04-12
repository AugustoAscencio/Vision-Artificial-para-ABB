"""
Panel de conexión TCP — controla la conexión con el robot ABB.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton,
)

from capa_interfaz.tema import Colores
from nucleo.modelos import EstadoConexion


class PanelConexion(QGroupBox):
    """
    Panel para configurar y controlar la conexión TCP con ABB.

    Señales:
        solicitar_conexion(str, int): IP y puerto para conectar.
        solicitar_desconexion(): Desconectar.
    """

    solicitar_conexion = pyqtSignal(str, int)
    solicitar_desconexion = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("🔌  Conexión Robot", parent)
        self._estado_actual = EstadoConexion.DESCONECTADO
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── IP ──
        layout_ip = QHBoxLayout()
        lbl_ip = QLabel("IP:")
        lbl_ip.setFixedWidth(45)
        self._input_ip = QLineEdit("172.18.9.27")
        self._input_ip.setPlaceholderText("Ej: 172.18.9.27")
        layout_ip.addWidget(lbl_ip)
        layout_ip.addWidget(self._input_ip)
        layout.addLayout(layout_ip)

        # ── Puerto ──
        layout_puerto = QHBoxLayout()
        lbl_puerto = QLabel("Puerto:")
        lbl_puerto.setFixedWidth(45)
        self._input_puerto = QSpinBox()
        self._input_puerto.setRange(1, 65535)
        self._input_puerto.setValue(8000)
        layout_puerto.addWidget(lbl_puerto)
        layout_puerto.addWidget(self._input_puerto)
        layout.addLayout(layout_puerto)

        # ── Botones ──
        layout_botones = QHBoxLayout()
        self._btn_conectar = QPushButton("⚡ Conectar")
        self._btn_conectar.setProperty("clase", "verde")
        self._btn_conectar.clicked.connect(self._al_conectar)

        self._btn_desconectar = QPushButton("⛔ Desconectar")
        self._btn_desconectar.setProperty("clase", "rojo")
        self._btn_desconectar.setEnabled(False)
        self._btn_desconectar.clicked.connect(self._al_desconectar)

        layout_botones.addWidget(self._btn_conectar)
        layout_botones.addWidget(self._btn_desconectar)
        layout.addLayout(layout_botones)

        # ── Estado ──
        self._lbl_estado = QLabel("● DESCONECTADO")
        self._lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

        # ── Último mensaje ──
        self._lbl_ultimo_msg = QLabel("Último: —")
        self._lbl_ultimo_msg.setStyleSheet(f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px;")
        self._lbl_ultimo_msg.setWordWrap(True)
        layout.addWidget(self._lbl_ultimo_msg)

    def _al_conectar(self):
        ip = self._input_ip.text().strip()
        puerto = self._input_puerto.value()
        if ip:
            self.solicitar_conexion.emit(ip, puerto)

    def _al_desconectar(self):
        self.solicitar_desconexion.emit()

    def actualizar_estado(self, estado: EstadoConexion):
        """Actualiza la visualización del estado de conexión."""
        self._estado_actual = estado

        estilos = {
            EstadoConexion.DESCONECTADO: (f"● DESCONECTADO", Colores.ERROR),
            EstadoConexion.CONECTANDO:    (f"◌ CONECTANDO...", Colores.AMARILLO),
            EstadoConexion.CONECTADO:     (f"● CONECTADO", Colores.VERDE),
            EstadoConexion.ERROR:         (f"✖ ERROR", Colores.ERROR),
            EstadoConexion.RECONECTANDO:  (f"↻ RECONECTANDO...", Colores.NARANJA),
        }

        texto, color = estilos.get(estado, ("?", Colores.TEXTO_SECUNDARIO))
        self._lbl_estado.setText(texto)
        self._lbl_estado.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-weight: bold;
                font-size: 13px;
                padding: 5px;
                background-color: {Colores.FONDO_TARJETA};
                border-radius: 6px;
            }}
        """)

        conectado = estado == EstadoConexion.CONECTADO
        self._btn_conectar.setEnabled(not conectado)
        self._btn_desconectar.setEnabled(conectado)
        self._input_ip.setEnabled(not conectado)
        self._input_puerto.setEnabled(not conectado)

    def actualizar_ultimo_mensaje(self, mensaje: str):
        """Muestra el último mensaje enviado/recibido."""
        texto = mensaje[:60] + "..." if len(mensaje) > 60 else mensaje
        self._lbl_ultimo_msg.setText(f"Último: {texto}")

    @property
    def ip(self) -> str:
        return self._input_ip.text().strip()

    @property
    def puerto(self) -> int:
        return self._input_puerto.value()

    def establecer_ip_puerto(self, ip: str, puerto: int):
        """Establece IP y puerto desde la configuración."""
        self._input_ip.setText(ip)
        self._input_puerto.setValue(puerto)
