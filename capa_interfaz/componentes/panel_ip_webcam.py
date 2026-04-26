"""
Panel IP Webcam — permite usar el celular como cámara vía HTTP/MJPEG.
Compatible con la app "IP Webcam" de Android.
"""

import urllib.request
import urllib.error

from PyQt6.QtCore import pyqtSignal, Qt, QThread
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox,
)

from capa_interfaz.tema import Colores


class HiloProbarConexion(QThread):
    """Prueba la conexión IP Webcam en un hilo separado."""
    resultado = pyqtSignal(bool, str)  # (exito, mensaje)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        try:
            req = urllib.request.Request(self._url, method="GET")
            resp = urllib.request.urlopen(req, timeout=3)
            if resp.status == 200:
                self.resultado.emit(True, "Conexión exitosa")
            else:
                self.resultado.emit(False, f"HTTP {resp.status}")
        except urllib.error.URLError as e:
            self.resultado.emit(False, f"No se pudo conectar: {e.reason}")
        except Exception as e:
            self.resultado.emit(False, f"Error: {e}")


class PanelIPWebcam(QGroupBox):
    """
    Panel para conectar a IP Webcam (celular Android como cámara).

    Señales:
        iniciar_ip_webcam(str): URL del stream MJPEG para iniciar captura.
    """

    iniciar_ip_webcam = pyqtSignal(str)  # URL completa del video stream

    def __init__(self, parent=None):
        super().__init__("📱  IP Webcam (Celular)", parent)
        self._hilo_prueba: HiloProbarConexion | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── Instrucción ──
        lbl_info = QLabel(
            "Usa tu celular como cámara.\n"
            "Abre IP Webcam en el celular y usa la URL del servidor."
        )
        lbl_info.setStyleSheet(
            f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px;"
        )
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # ── IP ──
        layout_ip = QHBoxLayout()
        lbl_ip = QLabel("IP:")
        lbl_ip.setFixedWidth(30)
        self._txt_ip = QLineEdit("192.168.1.11")
        self._txt_ip.setPlaceholderText("Ej: 192.168.1.11")
        layout_ip.addWidget(lbl_ip)
        layout_ip.addWidget(self._txt_ip)
        layout.addLayout(layout_ip)

        # ── Puerto ──
        layout_puerto = QHBoxLayout()
        lbl_puerto = QLabel("Puerto:")
        lbl_puerto.setFixedWidth(50)
        self._spn_puerto = QSpinBox()
        self._spn_puerto.setRange(1, 65535)
        self._spn_puerto.setValue(8080)
        layout_puerto.addWidget(lbl_puerto)
        layout_puerto.addWidget(self._spn_puerto)
        layout.addLayout(layout_puerto)

        # ── URL preview ──
        self._lbl_url = QLabel("")
        self._lbl_url.setStyleSheet(
            f"color: {Colores.MORADO}; font-size: 10px; font-family: monospace;"
        )
        self._lbl_url.setWordWrap(True)
        layout.addWidget(self._lbl_url)

        # Actualizar URL en vivo
        self._txt_ip.textChanged.connect(self._actualizar_url_preview)
        self._spn_puerto.valueChanged.connect(self._actualizar_url_preview)
        self._actualizar_url_preview()

        # ── Botones ──
        layout_btns = QHBoxLayout()

        self._btn_probar = QPushButton("🔍 Probar Conexión")
        self._btn_probar.setToolTip(
            "Verifica que el celular está accesible en la red"
        )
        self._btn_probar.clicked.connect(self._al_probar_conexion)

        self._btn_usar = QPushButton("📷 Usar como Cámara")
        self._btn_usar.setProperty("clase", "verde")
        self._btn_usar.setToolTip(
            "Inicia la captura usando el stream del celular"
        )
        self._btn_usar.clicked.connect(self._al_usar_camara)

        layout_btns.addWidget(self._btn_probar)
        layout_btns.addWidget(self._btn_usar)
        layout.addLayout(layout_btns)

        # ── Estado ──
        self._lbl_estado = QLabel("")
        self._lbl_estado.setStyleSheet(
            f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px;"
        )
        self._lbl_estado.setWordWrap(True)
        layout.addWidget(self._lbl_estado)

    @property
    def url_video(self) -> str:
        """URL completa del stream MJPEG."""
        ip = self._txt_ip.text().strip()
        puerto = self._spn_puerto.value()
        return f"http://{ip}:{puerto}/video"

    def _actualizar_url_preview(self):
        self._lbl_url.setText(f"URL: {self.url_video}")

    def _al_probar_conexion(self):
        """Prueba la conexión en un hilo para no bloquear la UI."""
        self._btn_probar.setEnabled(False)
        self._lbl_estado.setText("⏳ Probando conexión...")
        self._lbl_estado.setStyleSheet(
            f"color: {Colores.AMARILLO}; font-size: 11px;"
        )

        # Probar la URL base (no el stream de video para ir más rápido)
        ip = self._txt_ip.text().strip()
        puerto = self._spn_puerto.value()
        url_test = f"http://{ip}:{puerto}/"

        self._hilo_prueba = HiloProbarConexion(url_test)
        self._hilo_prueba.resultado.connect(self._al_resultado_prueba)
        self._hilo_prueba.start()

    def _al_resultado_prueba(self, exito: bool, mensaje: str):
        """Callback cuando la prueba de conexión termina."""
        self._btn_probar.setEnabled(True)
        if exito:
            self._lbl_estado.setText(f"✔ {mensaje}")
            self._lbl_estado.setStyleSheet(
                f"color: {Colores.VERDE}; font-size: 11px;"
            )
        else:
            self._lbl_estado.setText(f"✖ {mensaje}")
            self._lbl_estado.setStyleSheet(
                f"color: {Colores.ERROR}; font-size: 11px;"
            )

    def _al_usar_camara(self):
        """Emite la señal para iniciar la cámara con la URL del celular."""
        url = self.url_video
        self._lbl_estado.setText(f"📡 Conectando a {url}...")
        self._lbl_estado.setStyleSheet(
            f"color: {Colores.CYAN}; font-size: 11px;"
        )
        self.iniciar_ip_webcam.emit(url)
