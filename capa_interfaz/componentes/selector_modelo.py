"""
Selector de modelo YOLO — permite elegir modelos .pt con visualización
del modelo activo, origen del archivo y feedback de carga.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QFileDialog,
)

from capa_interfaz.tema import Colores


class SelectorModelo(QGroupBox):
    """
    Selector de modelo YOLO con lista de todos los modelos .pt
    encontrados en modelos/, raíz del proyecto y rutas externas.

    Señales:
        modelo_seleccionado(str): Ruta del modelo seleccionado.
        recargar_modelos(): Solicita recargar lista de modelos.
    """

    modelo_seleccionado = pyqtSignal(str)
    recargar_modelos = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("🤖  Modelo de Detección (IA)", parent)
        self._nombre_activo = ""
        self._cargando = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── Modelo activo (prominente) ──
        self._lbl_activo = QLabel("● Activo: --")
        self._lbl_activo.setStyleSheet(f"""
            QLabel {{
                color: {Colores.VERDE};
                font-size: 13px;
                font-weight: bold;
                padding: 4px 8px;
                background-color: {Colores.FONDO_TARJETA};
                border-radius: 6px;
                border: 1px solid {Colores.VERDE};
            }}
        """)
        self._lbl_activo.setWordWrap(True)
        layout.addWidget(self._lbl_activo)

        # ── ComboBox de modelos ──
        lbl_combo = QLabel("Seleccionar modelo:")
        lbl_combo.setStyleSheet(f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px;")
        layout.addWidget(lbl_combo)

        self._combo_modelos = QComboBox()
        self._combo_modelos.setToolTip("Modelos .pt encontrados en modelos/ y raíz del proyecto")
        layout.addWidget(self._combo_modelos)

        # ── Botones ──
        layout_btns = QHBoxLayout()

        self._btn_aplicar = QPushButton("▶ Aplicar")
        self._btn_aplicar.setProperty("clase", "verde")
        self._btn_aplicar.setToolTip("Cargar el modelo seleccionado")
        self._btn_aplicar.clicked.connect(self._al_aplicar)

        self._btn_recargar = QPushButton("↻ Recargar")
        self._btn_recargar.setToolTip("Reescanear directorios buscando modelos .pt")
        self._btn_recargar.clicked.connect(lambda: self.recargar_modelos.emit())

        layout_btns.addWidget(self._btn_aplicar)
        layout_btns.addWidget(self._btn_recargar)
        layout.addLayout(layout_btns)

        # ── Botón examinar ──
        self._btn_examinar = QPushButton("📂 Examinar archivo .pt ...")
        self._btn_examinar.setToolTip("Cargar un modelo .pt desde cualquier ubicación")
        self._btn_examinar.clicked.connect(self._al_examinar)
        layout.addWidget(self._btn_examinar)

        # ── Info estado ──
        self._lbl_info = QLabel("")
        self._lbl_info.setStyleSheet(f"color: {Colores.TEXTO_SECUNDARIO}; font-size: 11px;")
        self._lbl_info.setWordWrap(True)
        layout.addWidget(self._lbl_info)

    def establecer_modelos(self, modelos: list[dict]):
        """
        Puebla el combo con modelos disponibles de todas las fuentes.
        Cada modelo: {"nombre": "...", "ruta": "...", "tamano_mb": ..., "origen": "..."}
        """
        self._combo_modelos.blockSignals(True)
        self._combo_modelos.clear()

        indice_activo = -1

        if modelos:
            for i, m in enumerate(modelos):
                origen = m.get("origen", "")
                texto = f"{m['nombre']} ({m['tamano_mb']:.1f} MB) [{origen}]"
                self._combo_modelos.addItem(texto, m["ruta"])
                # Si este modelo es el activo, recordar su índice
                if m["nombre"] == self._nombre_activo:
                    indice_activo = i

            self._lbl_info.setText(f"{len(modelos)} modelo(s) encontrados")
        else:
            self._lbl_info.setText("Sin modelos .pt encontrados")

        # Siempre agregar opción de descarga automática al final
        self._combo_modelos.addItem("─── Descargar yolov8n.pt (auto) ───", "yolov8n.pt")

        # Pre-seleccionar el modelo activo
        if indice_activo >= 0:
            self._combo_modelos.setCurrentIndex(indice_activo)

        self._combo_modelos.blockSignals(False)

    def _al_aplicar(self):
        """Aplica el modelo seleccionado en el combo."""
        ruta = self._combo_modelos.currentData()
        if ruta:
            self._establecer_cargando(True)
            self.modelo_seleccionado.emit(ruta)

    def _al_examinar(self):
        """Abre un diálogo para seleccionar un archivo .pt desde cualquier ubicación."""
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar modelo YOLO (.pt)",
            "",
            "Modelos YOLO (*.pt);;Todos los archivos (*.*)",
        )
        if ruta:
            self._establecer_cargando(True)
            self.modelo_seleccionado.emit(ruta)

    def _establecer_cargando(self, cargando: bool):
        """Feedback visual durante la carga de un modelo."""
        self._cargando = cargando
        self._btn_aplicar.setEnabled(not cargando)
        self._btn_examinar.setEnabled(not cargando)
        self._combo_modelos.setEnabled(not cargando)
        if cargando:
            self._lbl_activo.setText("◌ Cargando modelo...")
            self._lbl_activo.setStyleSheet(f"""
                QLabel {{
                    color: {Colores.AMARILLO};
                    font-size: 13px;
                    font-weight: bold;
                    padding: 4px 8px;
                    background-color: {Colores.FONDO_TARJETA};
                    border-radius: 6px;
                    border: 1px solid {Colores.AMARILLO};
                }}
            """)

    def actualizar_modelo_activo(self, nombre: str):
        """Muestra el nombre del modelo actualmente cargado y restaura controles."""
        self._nombre_activo = nombre
        self._lbl_activo.setText(f"● Activo: {nombre}")
        self._lbl_activo.setStyleSheet(f"""
            QLabel {{
                color: {Colores.VERDE};
                font-size: 13px;
                font-weight: bold;
                padding: 4px 8px;
                background-color: {Colores.FONDO_TARJETA};
                border-radius: 6px;
                border: 1px solid {Colores.VERDE};
            }}
        """)
        self._lbl_info.setText(f"Modelo '{nombre}' cargado correctamente")

        # Restaurar controles si estaban deshabilitados
        if self._cargando:
            self._establecer_cargando(False)

        # Sincronizar combo con el modelo activo
        for i in range(self._combo_modelos.count()):
            datos = self._combo_modelos.itemData(i)
            if datos and nombre in str(datos):
                self._combo_modelos.blockSignals(True)
                self._combo_modelos.setCurrentIndex(i)
                self._combo_modelos.blockSignals(False)
                break
