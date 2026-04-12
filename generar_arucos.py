"""
Generador de marcadores ArUco para impresión.
Crea archivos PNG de marcadores individuales y una página con los 4 marcadores.
"""

import cv2
import numpy as np
from pathlib import Path


def generar_marcadores(
    diccionario_nombre: str = "DICT_4X4_50",
    ids: list[int] = None,
    tamano_px: int = 400,
    directorio_salida: str = "marcadores_aruco",
):
    """
    Genera imágenes PNG de marcadores ArUco.

    Args:
        diccionario_nombre: Nombre del diccionario ArUco.
        ids: Lista de IDs a generar. Por defecto [0, 1, 2, 3].
        tamano_px: Tamaño del marcador en píxeles.
        directorio_salida: Carpeta donde se guardan los PNG.
    """
    if ids is None:
        ids = [0, 1, 2, 3]

    # Obtener diccionario
    diccionarios = {
        "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
        "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
        "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
        "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
        "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
    }

    clave = diccionarios.get(diccionario_nombre, cv2.aruco.DICT_4X4_50)
    diccionario = cv2.aruco.getPredefinedDictionary(clave)

    salida = Path(directorio_salida)
    salida.mkdir(parents=True, exist_ok=True)

    marcadores_generados = []

    for id_marcador in ids:
        # Generar marcador
        imagen = cv2.aruco.generateImageMarker(diccionario, id_marcador, tamano_px)

        # Añadir borde blanco
        borde = 40
        con_borde = np.ones(
            (tamano_px + 2 * borde, tamano_px + 2 * borde),
            dtype=np.uint8
        ) * 255
        con_borde[borde:borde + tamano_px, borde:borde + tamano_px] = imagen

        # Añadir texto con ID
        cv2.putText(
            con_borde,
            f"ID: {id_marcador}",
            (borde, tamano_px + borde + 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0,),
            2,
        )

        # Guardar
        ruta = salida / f"aruco_id{id_marcador}.png"
        cv2.imwrite(str(ruta), con_borde)
        marcadores_generados.append(con_borde)
        print(f"[OK] Marcador ID {id_marcador} guardado en: {ruta}")

    # ── Generar página combinada A4 ──
    if len(marcadores_generados) >= 4:
        # Crear grid 2x2
        fila1 = np.hstack([marcadores_generados[0], marcadores_generados[1]])
        fila2 = np.hstack([marcadores_generados[2], marcadores_generados[3]])
        pagina = np.vstack([fila1, fila2])

        # Redimensionar para A4 (aprox 2480x3508 a 300dpi)
        ruta_pagina = salida / "pagina_4_marcadores.png"
        cv2.imwrite(str(ruta_pagina), pagina)
        print(f"[OK] Pagina con 4 marcadores guardada en: {ruta_pagina}")

    print(f"\n===========================================")
    print(f"Marcadores generados en: {salida.resolve()}")
    print(f"Diccionario: {diccionario_nombre}")
    print(f"IDs: {ids}")
    print(f"Tamaño: {tamano_px}x{tamano_px} px")
    print(f"===========================================")
    print(f"\nInstrucciones:")
    print(f"1. Imprime los marcadores a tamaño real (ej: 50mm x 50mm)")
    print(f"2. Pegalos en las 4 esquinas de la superficie de trabajo")
    print(f"3. Mide las posiciones (mm) de cada uno respecto al origen del robot")
    print(f"4. Actualiza config_defecto.yaml -> aruco.puntos_mundo")
    print(f"5. En la interfaz, presiona 'Calibrar con ArUco'")


if __name__ == "__main__":
    generar_marcadores()
