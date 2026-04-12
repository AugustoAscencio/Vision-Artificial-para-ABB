"""
Punto de entrada del sistema de visión artificial ABB.
Inicia la aplicación PyQt6 y el controlador principal.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from capa_interfaz.tema import aplicar_tema


def main():
    # Habilitar DPI alto para pantallas modernas
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Visión Artificial ABB")
    app.setOrganizationName("IndustrialVision")

    # Aplicar tema oscuro
    aplicar_tema(app)

    # Importar aquí para que el QApplication exista primero
    from aplicacion import Aplicacion

    sistema = Aplicacion()
    sistema.mostrar()

    # Shutdown limpio al cerrar la app
    app.aboutToQuit.connect(sistema.cerrar)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
