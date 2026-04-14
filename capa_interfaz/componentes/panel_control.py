"""
Panel de control — botones para cámara, preprocesamiento y envío automático.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QSlider, QCheckBox,
)
from PyQt6.QtCore import Qt

from capa_interfaz.tema import Colores


class PanelControl(QGroupBox):
    """
    Panel de control general del sistema.

    Señales:
        iniciar_camara(int): Índice de cámara a iniciar.
        detener_camara(): Detener cámara.
        confianza_cambiada(float): Nueva confianza YOLO.
        preprocesamiento_cambiado(bool, bool, bool): contraste, ruido, distorsión.
        envio_automatico_cambiado(bool): Toggle envío automático.
    """

    iniciar_camara = pyqtSignal(int)
    detener_camara = pyqtSignal()
    confianza_cambiada = pyqtSignal(float)
    preprocesamiento_cambiado = pyqtSignal(bool, bool, bool)
    envio_automatico_cambiado = pyqtSignal(bool)
    crosshair_cambiado = pyqtSignal(bool)
    rejilla_cambiada = pyqtSignal(bool)
    imagen_cargada = pyqtSignal(str)   # Ruta de imagen → YOLO → Vista 2D
    simulador_cambiado = pyqtSignal(bool) # Modo simulador on/off

    def __init__(self, parent=None):
        super().__init__("🎮  Control", parent)
        self._camara_activa = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Selector de cámara ──
        layout_cam = QHBoxLayout()
        lbl_cam = QLabel("Cámara:")
        self._combo_camara = QComboBox()
        self._combo_camara.addItem("Cámara 0", 0)
        layout_cam.addWidget(lbl_cam)
        layout_cam.addWidget(self._combo_camara)
        layout.addLayout(layout_cam)

        # ── Botones cámara ──
        layout_btns = QHBoxLayout()
        self._btn_iniciar = QPushButton("▶  Iniciar")
        self._btn_iniciar.setProperty("clase", "verde")
        self._btn_iniciar.clicked.connect(self._al_iniciar_camara)

        self._btn_detener = QPushButton("⏹  Detener")
        self._btn_detener.setProperty("clase", "rojo")
        self._btn_detener.setEnabled(False)
        self._btn_detener.clicked.connect(self._al_detener_camara)

        layout_btns.addWidget(self._btn_iniciar)
        layout_btns.addWidget(self._btn_detener)
        layout.addLayout(layout_btns)

        # ── Confianza YOLO ──
        layout_conf = QVBoxLayout()
        layout_conf_header = QHBoxLayout()
        lbl_conf = QLabel("Confianza YOLO:")
        self._lbl_conf_valor = QLabel("50%")
        self._lbl_conf_valor.setStyleSheet(f"color: {Colores.CYAN}; font-weight: bold;")
        layout_conf_header.addWidget(lbl_conf)
        layout_conf_header.addStretch()
        layout_conf_header.addWidget(self._lbl_conf_valor)
        layout_conf.addLayout(layout_conf_header)

        self._slider_confianza = QSlider(Qt.Orientation.Horizontal)
        self._slider_confianza.setRange(5, 95)
        self._slider_confianza.setValue(50)
        self._slider_confianza.setTickInterval(5)
        self._slider_confianza.valueChanged.connect(self._al_cambiar_confianza)
        layout_conf.addWidget(self._slider_confianza)
        layout.addLayout(layout_conf)

        # ── Preprocesamiento ──
        lbl_pre = QLabel("Preprocesamiento:")
        lbl_pre.setStyleSheet(f"color: {Colores.AZUL_ACENTO}; font-weight: bold; margin-top: 6px;")
        layout.addWidget(lbl_pre)

        self._chk_contraste = QCheckBox("Mejorar contraste (CLAHE)")
        self._chk_contraste.stateChanged.connect(self._al_cambiar_preprocesamiento)
        layout.addWidget(self._chk_contraste)

        self._chk_ruido = QCheckBox("Reducir ruido")
        self._chk_ruido.stateChanged.connect(self._al_cambiar_preprocesamiento)
        layout.addWidget(self._chk_ruido)

        # ── Envío automático ──
        self._chk_envio_auto = QCheckBox("Envio automatico al robot")
        self._chk_envio_auto.setStyleSheet(f"color: {Colores.NARANJA}; font-weight: bold; margin-top: 6px;")
        self._chk_envio_auto.stateChanged.connect(
            lambda state: self.envio_automatico_cambiado.emit(state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self._chk_envio_auto)

        # ── Visualización AR ──
        lbl_vis = QLabel("Visualizacion:")
        lbl_vis.setStyleSheet(f"color: {Colores.AZUL_ACENTO}; font-weight: bold; margin-top: 6px;")
        layout.addWidget(lbl_vis)

        self._chk_crosshair = QCheckBox("Mostrar crosshair (referencia)")
        self._chk_crosshair.stateChanged.connect(
            lambda state: self.crosshair_cambiado.emit(state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self._chk_crosshair)

        self._chk_rejilla = QCheckBox("Mostrar rejilla AR (zona calibrada)")
        self._chk_rejilla.stateChanged.connect(
            lambda state: self.rejilla_cambiada.emit(state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self._chk_rejilla)

        # ── Vista 2D ──
        lbl_2d = QLabel("Vista 2D cenital:")
        lbl_2d.setStyleSheet(f"color: {Colores.MORADO}; font-weight: bold; margin-top: 6px;")
        layout.addWidget(lbl_2d)

        self._btn_cargar_imagen = QPushButton("📂 Cargar imagen → YOLO")
        self._btn_cargar_imagen.setToolTip(
            "Cargar una imagen para procesarla con YOLO\n"
            "y mostrar las detecciones en la Vista 2D"
        )
        self._btn_cargar_imagen.clicked.connect(self._al_cargar_imagen)
        layout.addWidget(self._btn_cargar_imagen)

        self._chk_simulador = QCheckBox("Activar MODO SIMULADOR")
        self._chk_simulador.setStyleSheet(f"color: {Colores.NARANJA}; font-weight: bold;")
        self._chk_simulador.setToolTip("Ignora la webcam y usa la imagen de la Vista 2D como cámara.")
        self._chk_simulador.stateChanged.connect(
            lambda state: self.simulador_cambiado.emit(state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self._chk_simulador)

    def _al_cargar_imagen(self):
        from PyQt6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar imagen para procesar",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp);;Todos los archivos (*.*)"
        )
        if ruta:
            self.imagen_cargada.emit(ruta)

    def _al_iniciar_camara(self):
        indice = self._combo_camara.currentData()
        self.iniciar_camara.emit(indice if indice is not None else 0)

    def _al_detener_camara(self):
        self.detener_camara.emit()

    def _al_cambiar_confianza(self, valor):
        porcentaje = valor / 100.0
        self._lbl_conf_valor.setText(f"{valor}%")
        self.confianza_cambiada.emit(porcentaje)

    def _al_cambiar_preprocesamiento(self):
        self.preprocesamiento_cambiado.emit(
            self._chk_contraste.isChecked(),
            self._chk_ruido.isChecked(),
            True,  # distorsión siempre activa si hay calibración
        )

    def actualizar_estado_camara(self, activa: bool):
        """Actualiza los botones según el estado de la cámara."""
        self._camara_activa = activa
        self._btn_iniciar.setEnabled(not activa)
        self._btn_detener.setEnabled(activa)
        self._combo_camara.setEnabled(not activa)

    def establecer_camaras(self, camaras: list[dict]):
        """Puebla el combo con las cámaras disponibles."""
        self._combo_camara.clear()
        if not camaras:
            self._combo_camara.addItem("Sin cámaras", -1)
            return
        for cam in camaras:
            nombre = f"{cam['nombre']} ({cam['resolucion'][0]}x{cam['resolucion'][1]})"
            self._combo_camara.addItem(nombre, cam["indice"])

    def establecer_confianza(self, valor: float):
        """Establece la confianza inicial desde config."""
        self._slider_confianza.setValue(int(valor * 100))
