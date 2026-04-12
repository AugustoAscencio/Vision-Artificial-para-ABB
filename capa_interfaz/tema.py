"""
Tema visual del sistema — paleta industrial oscura inspirada en ABB.
"""


# ═══════════════════════════════════════════════════════════════
# Paleta de colores
# ═══════════════════════════════════════════════════════════════

class Colores:
    # Fondos
    FONDO_PRINCIPAL = "#0d1117"
    FONDO_PANEL = "#161b22"
    FONDO_TARJETA = "#1c2333"
    FONDO_INPUT = "#0d1117"
    FONDO_HOVER = "#21262d"

    # Bordes
    BORDE = "#30363d"
    BORDE_ACTIVO = "#58a6ff"

    # Texto
    TEXTO_PRIMARIO = "#e6edf3"
    TEXTO_SECUNDARIO = "#8b949e"
    TEXTO_DESHABILITADO = "#484f58"

    # Acentos
    ROJO_ABB = "#ff4444"
    AZUL_ACENTO = "#58a6ff"
    CYAN = "#00d4ff"
    VERDE = "#3fb950"
    AMARILLO = "#d29922"
    NARANJA = "#f0883e"
    MORADO = "#bc8cff"

    # Estados
    EXITO = "#3fb950"
    ERROR = "#f85149"
    ADVERTENCIA = "#d29922"
    INFO = "#58a6ff"


# ═══════════════════════════════════════════════════════════════
# Stylesheet global
# ═══════════════════════════════════════════════════════════════

STYLESHEET_GLOBAL = f"""
    /* ── Base ────────────────────────────────────── */
    QMainWindow {{
        background-color: {Colores.FONDO_PRINCIPAL};
    }}
    QWidget {{
        color: {Colores.TEXTO_PRIMARIO};
        font-family: 'Segoe UI', 'Inter', sans-serif;
        font-size: 13px;
    }}

    /* ── Paneles / GroupBox ───────────────────────── */
    QGroupBox {{
        background-color: {Colores.FONDO_PANEL};
        border: 1px solid {Colores.BORDE};
        border-radius: 8px;
        margin-top: 14px;
        padding: 14px 10px 10px 10px;
        font-weight: bold;
        font-size: 13px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 12px;
        color: {Colores.AZUL_ACENTO};
    }}

    /* ── Labels ──────────────────────────────────── */
    QLabel {{
        background: transparent;
        border: none;
    }}

    /* ── Inputs ──────────────────────────────────── */
    QLineEdit, QSpinBox {{
        background-color: {Colores.FONDO_INPUT};
        border: 1px solid {Colores.BORDE};
        border-radius: 6px;
        padding: 6px 10px;
        color: {Colores.TEXTO_PRIMARIO};
        selection-background-color: {Colores.AZUL_ACENTO};
    }}
    QLineEdit:focus, QSpinBox:focus {{
        border-color: {Colores.AZUL_ACENTO};
    }}

    /* ── Botones ─────────────────────────────────── */
    QPushButton {{
        background-color: {Colores.FONDO_TARJETA};
        border: 1px solid {Colores.BORDE};
        border-radius: 6px;
        padding: 8px 16px;
        color: {Colores.TEXTO_PRIMARIO};
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {Colores.FONDO_HOVER};
        border-color: {Colores.AZUL_ACENTO};
    }}
    QPushButton:pressed {{
        background-color: {Colores.AZUL_ACENTO};
        color: white;
    }}
    QPushButton:disabled {{
        color: {Colores.TEXTO_DESHABILITADO};
        border-color: {Colores.BORDE};
    }}

    /* ── Botón acento verde ──────────────────────── */
    QPushButton[clase="verde"] {{
        background-color: #1a3a2a;
        border-color: {Colores.VERDE};
        color: {Colores.VERDE};
    }}
    QPushButton[clase="verde"]:hover {{
        background-color: #224a34;
    }}

    /* ── Botón acento rojo ───────────────────────── */
    QPushButton[clase="rojo"] {{
        background-color: #3a1a1a;
        border-color: {Colores.ERROR};
        color: {Colores.ERROR};
    }}
    QPushButton[clase="rojo"]:hover {{
        background-color: #4a2424;
    }}

    /* ── ComboBox ─────────────────────────────────── */
    QComboBox {{
        background-color: {Colores.FONDO_INPUT};
        border: 1px solid {Colores.BORDE};
        border-radius: 6px;
        padding: 6px 10px;
        color: {Colores.TEXTO_PRIMARIO};
    }}
    QComboBox:hover {{
        border-color: {Colores.AZUL_ACENTO};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {Colores.FONDO_PANEL};
        border: 1px solid {Colores.BORDE};
        selection-background-color: {Colores.AZUL_ACENTO};
        color: {Colores.TEXTO_PRIMARIO};
    }}

    /* ── Slider ──────────────────────────────────── */
    QSlider::groove:horizontal {{
        height: 6px;
        background: {Colores.BORDE};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {Colores.AZUL_ACENTO};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    QSlider::sub-page:horizontal {{
        background: {Colores.AZUL_ACENTO};
        border-radius: 3px;
    }}

    /* ── TextEdit (Logs) ─────────────────────────── */
    QTextEdit {{
        background-color: {Colores.FONDO_INPUT};
        border: 1px solid {Colores.BORDE};
        border-radius: 6px;
        padding: 6px;
        font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 11px;
        color: {Colores.TEXTO_PRIMARIO};
    }}

    /* ── Tabla ────────────────────────────────────── */
    QTableWidget {{
        background-color: {Colores.FONDO_INPUT};
        border: 1px solid {Colores.BORDE};
        border-radius: 6px;
        gridline-color: {Colores.BORDE};
        font-size: 12px;
    }}
    QTableWidget::item {{
        padding: 4px;
    }}
    QTableWidget::item:selected {{
        background-color: {Colores.AZUL_ACENTO};
    }}
    QHeaderView::section {{
        background-color: {Colores.FONDO_PANEL};
        border: 1px solid {Colores.BORDE};
        padding: 4px 8px;
        font-weight: bold;
        font-size: 11px;
        color: {Colores.AZUL_ACENTO};
    }}

    /* ── ScrollBar ────────────────────────────────── */
    QScrollBar:vertical {{
        background: {Colores.FONDO_PRINCIPAL};
        width: 10px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {Colores.BORDE};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {Colores.TEXTO_SECUNDARIO};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ── StatusBar ────────────────────────────────── */
    QStatusBar {{
        background-color: {Colores.FONDO_PANEL};
        border-top: 1px solid {Colores.BORDE};
        color: {Colores.TEXTO_SECUNDARIO};
        font-size: 12px;
    }}

    /* ── CheckBox ─────────────────────────────────── */
    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {Colores.BORDE};
        border-radius: 4px;
        background: {Colores.FONDO_INPUT};
    }}
    QCheckBox::indicator:checked {{
        background: {Colores.AZUL_ACENTO};
        border-color: {Colores.AZUL_ACENTO};
    }}
"""


def aplicar_tema(app):
    """Aplica el tema global a la aplicación Qt."""
    app.setStyleSheet(STYLESHEET_GLOBAL)
