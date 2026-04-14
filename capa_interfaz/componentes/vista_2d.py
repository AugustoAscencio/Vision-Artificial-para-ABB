"""
Vista 2D cenital del espacio de trabajo — representación top-down precisa.

Dibuja con QPainter un plano 2D basado en los 4 marcadores ArUco,
mostrando el área de trabajo calibrada, objetos detectados, grid
en milímetros, y opcionalmente una imagen de fondo escalada.

Funciona como una "cámara virtual superior" del sistema.
"""

import math
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QImage,
    QPixmap, QPainterPath, QPolygonF, QLinearGradient,
)
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy

from capa_interfaz.tema import Colores
from nucleo.modelos import DeteccionObjeto, MarcadorAruco
from capa_logs import obtener_logger

logger = obtener_logger("vista_2d")


# ═══════════════════════════════════════════════════════════════
# Validador geométrico de ArUco
# ═══════════════════════════════════════════════════════════════

class ValidadorAruco:
    """
    Valida coherencia geométrica de los 4 marcadores ArUco.

    Verifica:
    - Que haya exactamente 4 puntos con IDs únicos
    - Orden correcto (sentido horario o antihorario)
    - Distancias coherentes (no colapsan, no son infinitas)
    - Forma cuadrilátera convexa (no auto-intersecta)
    - Proporciones razonables (no un cuadrilátero degenerado)
    """

    @staticmethod
    def validar(puntos_mundo: list[dict]) -> dict:
        """
        Valida los puntos mundo del config ArUco.

        Args:
            puntos_mundo: Lista de {"id": int, "x_mm": float, "y_mm": float}
                         o PuntoMundoAruco con atributos .id, .x_mm, .y_mm

        Returns:
            {"valido": bool, "errores": [...], "advertencias": [...],
             "info": {"area_mm2": ..., "perimetro_mm": ..., "orden": "..."}}
        """
        resultado = {
            "valido": True,
            "errores": [],
            "advertencias": [],
            "info": {},
        }

        # Extraer datos (soportar dict y dataclass)
        puntos = []
        for p in puntos_mundo:
            if hasattr(p, "id"):
                puntos.append({"id": p.id, "x_mm": p.x_mm, "y_mm": p.y_mm})
            else:
                puntos.append(p)

        # === Verificar cantidad ===
        if len(puntos) != 4:
            resultado["valido"] = False
            resultado["errores"].append(
                f"Se requieren exactamente 4 marcadores, hay {len(puntos)}"
            )
            return resultado

        # === Verificar IDs únicos ===
        ids = [p["id"] for p in puntos]
        if len(set(ids)) != 4:
            resultado["valido"] = False
            resultado["errores"].append(
                f"IDs duplicados: {ids}"
            )
            return resultado

        # Ordenar por ID para consistencia
        puntos_ord = sorted(puntos, key=lambda p: p["id"])
        coords = [(p["x_mm"], p["y_mm"]) for p in puntos_ord]

        # === Verificar valores finitos ===
        for i, (x, y) in enumerate(coords):
            if not (math.isfinite(x) and math.isfinite(y)):
                resultado["valido"] = False
                resultado["errores"].append(
                    f"Coordenada no finita en ID {puntos_ord[i]['id']}: ({x}, {y})"
                )
                return resultado

        # === Verificar distancias entre puntos ===
        distancias = []
        for i in range(4):
            j = (i + 1) % 4
            dx = coords[j][0] - coords[i][0]
            dy = coords[j][1] - coords[i][1]
            dist = math.sqrt(dx * dx + dy * dy)
            distancias.append(dist)

            if dist < 10.0:  # menos de 10mm
                resultado["valido"] = False
                resultado["errores"].append(
                    f"Marcadores ID {puntos_ord[i]['id']} e ID {puntos_ord[j]['id']} "
                    f"demasiado cercanos: {dist:.1f} mm"
                )

            if dist > 5000.0:  # más de 5 metros
                resultado["advertencias"].append(
                    f"Distancia muy grande entre ID {puntos_ord[i]['id']} e "
                    f"ID {puntos_ord[j]['id']}: {dist:.1f} mm"
                )

        # === Verificar convexidad (sentido del polígono) ===
        cruz_z = []
        for i in range(4):
            o = coords[i]
            a = coords[(i + 1) % 4]
            b = coords[(i + 2) % 4]
            # Producto cruzado del vector OA x AB
            cross = (a[0] - o[0]) * (b[1] - a[1]) - (a[1] - o[1]) * (b[0] - a[0])
            cruz_z.append(cross)

        # Todos deben tener el mismo signo para ser convexo
        positivos = sum(1 for c in cruz_z if c > 0)
        negativos = sum(1 for c in cruz_z if c < 0)

        if positivos > 0 and negativos > 0:
            resultado["advertencias"].append(
                "Los marcadores no forman un cuadrilátero convexo — "
                "revisar posiciones o IDs"
            )

        orden = "horario" if positivos >= negativos else "antihorario"
        resultado["info"]["orden"] = orden

        # === Calcular área (shoelace) ===
        area = 0.0
        for i in range(4):
            j = (i + 1) % 4
            area += coords[i][0] * coords[j][1]
            area -= coords[j][0] * coords[i][1]
        area = abs(area) / 2.0
        resultado["info"]["area_mm2"] = round(area, 1)
        resultado["info"]["area_cm2"] = round(area / 100.0, 1)

        if area < 100.0:  # menos de 1 cm²
            resultado["valido"] = False
            resultado["errores"].append(
                f"Área del espacio de trabajo demasiado pequeña: {area:.1f} mm²"
            )

        # === Perímetro ===
        perimetro = sum(distancias)
        resultado["info"]["perimetro_mm"] = round(perimetro, 1)
        resultado["info"]["distancias_mm"] = [round(d, 1) for d in distancias]

        # === Proporciones (ratio largo/ancho) ===
        if len(distancias) >= 4:
            lado_max = max(distancias)
            lado_min = min(distancias)
            if lado_min > 0:
                ratio = lado_max / lado_min
                resultado["info"]["ratio_lados"] = round(ratio, 2)
                if ratio > 10.0:
                    resultado["advertencias"].append(
                        f"Proporción de lados extrema: {ratio:.1f}:1"
                    )

        return resultado


# ═══════════════════════════════════════════════════════════════
# Widget Vista 2D
# ═══════════════════════════════════════════════════════════════

class Vista2D(QWidget):
    """
    Vista cenital 2D del espacio de trabajo.

    Renderiza con QPainter:
    - Plano base con los 4 marcadores ArUco
    - Zona calibrada (polígono verde translúcido)
    - Grid en milímetros con etiquetas
    - Objetos detectados como rectángulos con centroide
    - Imagen de fondo opcional escalada al plano

    Señales:
        objeto_seleccionado(int): Índice del objeto clickeado.
    """

    objeto_seleccionado = pyqtSignal(int)
    frame_virtual_generado = pyqtSignal(object)  # Emite np.ndarray (frame virtual)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Datos del plano
        self._puntos_mundo: list[dict] = []  # [{"id": 0, "x_mm": ..., "y_mm": ...}, ...]
        self._marcadores_detectados: list[MarcadorAruco] = []
        self._detecciones: list[DeteccionObjeto] = []

        # Imagen de fondo y simulación
        self._imagen_fondo: Optional[QImage] = None
        self._imagen_fondo_cv: Optional[np.ndarray] = None
        self._escala_imagen = 1.0
        self._offset_imagen = QPointF(0.0, 0.0)
        self._arrastrando_imagen = False
        self._ultimo_pos_raton = QPointF()

        # Configuración visual
        self._mostrar_grid = True
        self._espaciado_grid_mm = 50.0
        self._margen_px = 40

        # Estado de validación
        self._validacion: Optional[dict] = None
        self._validador = ValidadorAruco()

        # Límites calculados (mm)
        self._x_min = 0.0
        self._x_max = 300.0
        self._y_min = 0.0
        self._y_max = 200.0
        self._px_por_mm = 1.0

        # Tooltip/hover
        self.setMouseTracking(True)
        self._objeto_hover = -1

        logger.info("Vista 2D inicializada")

    # ═══════════════════════════════════════════════════════
    # API pública
    # ═══════════════════════════════════════════════════════

    def actualizar_puntos_mundo(self, puntos_mundo: list):
        """
        Establece las posiciones de los 4 ArUco desde el config.
        Acepta PuntoMundoAruco o dicts con {id, x_mm, y_mm}.
        """
        self._puntos_mundo = []
        for p in puntos_mundo:
            if hasattr(p, "id"):
                self._puntos_mundo.append({
                    "id": p.id, "x_mm": p.x_mm, "y_mm": p.y_mm
                })
            else:
                self._puntos_mundo.append(p)

        # Validar coherencia geométrica
        self._validacion = self._validador.validar(self._puntos_mundo)

        if self._validacion["errores"]:
            for err in self._validacion["errores"]:
                logger.error(f"Validación ArUco: {err}")
        for adv in self._validacion.get("advertencias", []):
            logger.warning(f"Validación ArUco: {adv}")

        if self._validacion["valido"]:
            info = self._validacion["info"]
            logger.info(
                f"ArUco validado — Orden: {info['orden']}, "
                f"Área: {info['area_cm2']} cm², "
                f"Perímetro: {info['perimetro_mm']} mm"
            )

        # Recalcular límites
        self._recalcular_limites()
        self.update()

    def actualizar_marcadores(self, marcadores: list[MarcadorAruco]):
        """Actualiza los marcadores ArUco detectados en tiempo real."""
        self._marcadores_detectados = marcadores
        self.update()

    def actualizar_detecciones(self, detecciones: list[DeteccionObjeto]):
        """Actualiza los objetos detectados por YOLO."""
        self._detecciones = detecciones
        self.update()

    def activar_grid(self, activo: bool):
        """Activa/desactiva la grilla de referencia."""
        self._mostrar_grid = activo
        self.update()

    def establecer_imagen_fondo(self, imagen_cv: np.ndarray):
        """
        Establece una imagen de fondo para el plano 2D.
        La imagen se escala para ajustarse al área del espacio de trabajo.
        """
        self._imagen_fondo_cv = imagen_cv.copy()
        # Resetear estado de simulación
        self._escala_imagen = 1.0
        self._offset_imagen = QPointF(0.0, 0.0)
        
        # Convertir BGR → RGB para Qt
        rgb = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_por_linea = ch * w
        self._imagen_fondo = QImage(
            rgb.data, w, h, bytes_por_linea, QImage.Format.Format_RGB888
        ).copy()
        logger.info(f"Imagen base establecida para simulación: {w}x{h}")
        self.update()
        self._emitir_frame_virtual()

    def obtener_imagen_fondo_cv(self) -> Optional[np.ndarray]:
        """Retorna la imagen de fondo en formato OpenCV (BGR)."""
        return self._imagen_fondo_cv

    def limpiar(self):
        """Limpia todos los datos de la vista."""
        self._detecciones = []
        self._marcadores_detectados = []
        self._imagen_fondo = None
        self._imagen_fondo_cv = None
        self.update()

    # ═══════════════════════════════════════════════════════
    # Transformaciones de coordenadas
    # ═══════════════════════════════════════════════════════

    def _recalcular_limites(self):
        """Recalcula los límites del espacio y la escala píxeles/mm."""
        if not self._puntos_mundo:
            return

        xs = [p["x_mm"] for p in self._puntos_mundo]
        ys = [p["y_mm"] for p in self._puntos_mundo]

        # Ampliar un 10% por cada lado como margen visual
        rango_x = max(xs) - min(xs)
        rango_y = max(ys) - min(ys)
        margen_x = max(rango_x * 0.1, 20.0)
        margen_y = max(rango_y * 0.1, 20.0)

        self._x_min = min(xs) - margen_x
        self._x_max = max(xs) + margen_x
        self._y_min = min(ys) - margen_y
        self._y_max = max(ys) + margen_y

    def _mm_a_widget(self, x_mm: float, y_mm: float) -> QPointF:
        """Convierte coordenadas mundo (mm) a coordenadas del widget (px)."""
        w = self.width() - 2 * self._margen_px
        h = self.height() - 2 * self._margen_px

        rango_x = self._x_max - self._x_min
        rango_y = self._y_max - self._y_min

        if rango_x <= 0 or rango_y <= 0:
            return QPointF(self._margen_px, self._margen_px)

        # Escala uniforme (mantener proporciones)
        escala_x = w / rango_x
        escala_y = h / rango_y
        self._px_por_mm = min(escala_x, escala_y)

        # Centrar en el widget
        ancho_real = rango_x * self._px_por_mm
        alto_real = rango_y * self._px_por_mm
        offset_x = self._margen_px + (w - ancho_real) / 2.0
        offset_y = self._margen_px + (h - alto_real) / 2.0

        px = offset_x + (x_mm - self._x_min) * self._px_por_mm
        # Y invertido (en pantalla Y crece hacia abajo, en mundo hacia arriba)
        py = offset_y + (self._y_max - y_mm) * self._px_por_mm

        return QPointF(px, py)

    def _widget_a_mm(self, px: float, py: float) -> tuple[float, float]:
        """Convierte coordenadas del widget a coordenadas mundo (mm)."""
        w = self.width() - 2 * self._margen_px
        h = self.height() - 2 * self._margen_px

        rango_x = self._x_max - self._x_min
        rango_y = self._y_max - self._y_min

        ancho_real = rango_x * self._px_por_mm
        alto_real = rango_y * self._px_por_mm
        offset_x = self._margen_px + (w - ancho_real) / 2.0
        offset_y = self._margen_px + (h - alto_real) / 2.0

        x_mm = self._x_min + (px - offset_x) / self._px_por_mm
        y_mm = self._y_max - (py - offset_y) / self._px_por_mm

        return (x_mm, y_mm)

    # ═══════════════════════════════════════════════════════
    # Renderizado (QPainter)
    # ═══════════════════════════════════════════════════════

    def paintEvent(self, event):
        """Renderiza toda la vista 2D."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Fondo oscuro
            painter.fillRect(self.rect(), QColor(Colores.FONDO_TARJETA))

            if not self._puntos_mundo:
                self._dibujar_placeholder(painter)
                painter.end()
                return

            # 1. Imagen de fondo (si existe)
            if self._imagen_fondo is not None:
                self._dibujar_imagen_fondo(painter)

            # 2. Grid
            if self._mostrar_grid:
                self._dibujar_grid(painter)

            # 3. Zona calibrada (polígono ArUco)
            self._dibujar_zona_aruco(painter)

            # 4. Marcadores ArUco
            self._dibujar_marcadores(painter)

            # 5. Objetos detectados
            self._dibujar_detecciones(painter)

            # 6. Info de validación
            self._dibujar_info_validacion(painter)

            # 7. Ejes de referencia
            self._dibujar_ejes(painter)

            painter.end()

        except Exception as e:
            logger.error(f"Error en paintEvent Vista2D: {e}")

    def _dibujar_placeholder(self, painter: QPainter):
        """Dibuja mensaje cuando no hay datos."""
        painter.setPen(QPen(QColor(Colores.TEXTO_SECUNDARIO)))
        fuente = QFont("Segoe UI", 12)
        painter.setFont(fuente)
        painter.drawText(
            self.rect(), Qt.AlignmentFlag.AlignCenter,
            "Vista 2D — Sin datos ArUco\n\n"
            "Configura los 4 marcadores\nen config_usuario.yaml"
        )

    def _dibujar_imagen_fondo(self, painter: QPainter):
        """Dibuja la imagen de fondo centrada en el espacio de trabajo ArUco."""
        if self._imagen_fondo is None or not self._puntos_mundo:
            return

        # Calcular el rectángulo del espacio de trabajo en coordenadas del widget
        xs = [p["x_mm"] for p in self._puntos_mundo]
        ys = [p["y_mm"] for p in self._puntos_mundo]

        p_tl = self._mm_a_widget(min(xs), max(ys))  # top-left
        p_br = self._mm_a_widget(max(xs), min(ys))  # bottom-right
        rect_workspace = QRectF(p_tl, p_br)

        # La imagen se ajusta para LLENAR el espacio de trabajo completo
        # Luego se aplica escala del usuario y offset del paneo
        centro = rect_workspace.center()
        ancho_dibujo = rect_workspace.width() * self._escala_imagen
        alto_dibujo = rect_workspace.height() * self._escala_imagen

        rect_dibujo = QRectF(
            centro.x() - ancho_dibujo / 2.0 + self._offset_imagen.x(),
            centro.y() - alto_dibujo / 2.0 + self._offset_imagen.y(),
            ancho_dibujo,
            alto_dibujo,
        )

        painter.save()
        painter.setOpacity(0.7)
        pixmap = QPixmap.fromImage(self._imagen_fondo)
        painter.drawPixmap(rect_dibujo.toRect(), pixmap)
        painter.restore()

    def _dibujar_grid(self, painter: QPainter):
        """Dibuja una grilla de referencia con etiquetas en mm."""
        pen_grid = QPen(QColor(60, 60, 60, 80), 1, Qt.PenStyle.DotLine)
        pen_eje = QPen(QColor(100, 200, 255, 120), 1, Qt.PenStyle.SolidLine)
        fuente = QFont("Consolas", 8)
        painter.setFont(fuente)

        paso = self._espaciado_grid_mm

        # Líneas verticales (X constante)
        x = math.ceil(self._x_min / paso) * paso
        while x <= self._x_max:
            p_arriba = self._mm_a_widget(x, self._y_max)
            p_abajo = self._mm_a_widget(x, self._y_min)

            es_eje = abs(x) < 0.01
            painter.setPen(pen_eje if es_eje else pen_grid)
            painter.drawLine(p_arriba, p_abajo)

            # Etiqueta
            painter.setPen(QPen(QColor(120, 120, 120)))
            painter.drawText(
                QPointF(p_abajo.x() + 2, p_abajo.y() + 12),
                f"{x:.0f}"
            )
            x += paso

        # Líneas horizontales (Y constante)
        y = math.ceil(self._y_min / paso) * paso
        while y <= self._y_max:
            p_izq = self._mm_a_widget(self._x_min, y)
            p_der = self._mm_a_widget(self._x_max, y)

            es_eje = abs(y) < 0.01
            painter.setPen(pen_eje if es_eje else pen_grid)
            painter.drawLine(p_izq, p_der)

            # Etiqueta
            painter.setPen(QPen(QColor(120, 120, 120)))
            painter.drawText(
                QPointF(p_izq.x() - 35, p_izq.y() + 4),
                f"{y:.0f}"
            )
            y += paso

    def _dibujar_zona_aruco(self, painter: QPainter):
        """Dibuja el polígono definido por los 4 ArUco con relleno translúcido."""
        if len(self._puntos_mundo) < 3:
            return

        # Ordenar por ID
        puntos_ord = sorted(self._puntos_mundo, key=lambda p: p["id"])

        # Construir polígono Qt en orden de IDs
        poligono = QPolygonF()
        for p in puntos_ord:
            poligono.append(self._mm_a_widget(p["x_mm"], p["y_mm"]))

        # Relleno verde translúcido
        color_relleno = QColor(0, 220, 80, 30)
        painter.setBrush(QBrush(color_relleno))

        # Borde verde
        pen_zona = QPen(QColor(0, 220, 80, 180), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen_zona)
        painter.drawPolygon(poligono)

        # Líneas de conexión entre ArUcos (lados del polígono con distancias)
        painter.setPen(QPen(QColor(0, 220, 80, 100), 1, Qt.PenStyle.DashLine))
        fuente_dist = QFont("Consolas", 8)
        painter.setFont(fuente_dist)

        for i in range(len(puntos_ord)):
            j = (i + 1) % len(puntos_ord)
            p1 = puntos_ord[i]
            p2 = puntos_ord[j]

            pt1 = self._mm_a_widget(p1["x_mm"], p1["y_mm"])
            pt2 = self._mm_a_widget(p2["x_mm"], p2["y_mm"])

            # Calcular distancia real
            dx = p2["x_mm"] - p1["x_mm"]
            dy = p2["y_mm"] - p1["y_mm"]
            dist = math.sqrt(dx * dx + dy * dy)

            # Punto medio para la etiqueta de distancia
            medio = QPointF((pt1.x() + pt2.x()) / 2, (pt1.y() + pt2.y()) / 2)
            painter.setPen(QPen(QColor(200, 255, 200, 200)))
            painter.drawText(
                QPointF(medio.x() - 15, medio.y() - 5),
                f"{dist:.0f}mm"
            )

    def _dibujar_marcadores(self, painter: QPainter):
        """Dibuja los 4 marcadores ArUco como cuadrados con ID y coordenadas."""
        tamano_marcador = max(12.0, 50.0 * self._px_por_mm)  # tamaño visual mínimo
        tamano_marcador = min(tamano_marcador, 30.0)  # máximo

        fuente_id = QFont("Segoe UI", 10, QFont.Weight.Bold)
        fuente_coord = QFont("Consolas", 7)

        for p in self._puntos_mundo:
            centro = self._mm_a_widget(p["x_mm"], p["y_mm"])
            mitad = tamano_marcador / 2

            # Verificar si este marcador fue detectado en cámara real
            detectado = any(
                m.id == p["id"] for m in self._marcadores_detectados
            )

            # Cuadrado del marcador
            rect = QRectF(
                centro.x() - mitad, centro.y() - mitad,
                tamano_marcador, tamano_marcador
            )

            if detectado:
                # Detectado: fondo azul, borde brillante
                painter.setBrush(QBrush(QColor(0, 120, 255, 100)))
                painter.setPen(QPen(QColor(0, 180, 255), 2))
            else:
                # No detectado: fondo gris, borde tenue
                painter.setBrush(QBrush(QColor(80, 80, 80, 80)))
                painter.setPen(QPen(QColor(150, 150, 150), 1))

            painter.drawRect(rect)

            # Centro del marcador (punto rojo)
            painter.setBrush(QBrush(QColor(255, 50, 50)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(centro, 4, 4)

            # ID del marcador
            painter.setPen(QPen(QColor(255, 255, 100)))
            painter.setFont(fuente_id)
            painter.drawText(
                QPointF(centro.x() + mitad + 4, centro.y() - 2),
                f"ID:{p['id']}"
            )

            # Coordenadas en mm
            painter.setPen(QPen(QColor(180, 180, 180)))
            painter.setFont(fuente_coord)
            painter.drawText(
                QPointF(centro.x() + mitad + 4, centro.y() + 12),
                f"({p['x_mm']:.0f}, {p['y_mm']:.0f}) mm"
            )

    def _dibujar_detecciones(self, painter: QPainter):
        """Dibuja objetos detectados como rectángulos con centroides."""
        fuente_obj = QFont("Segoe UI", 8)
        fuente_coord = QFont("Consolas", 7)

        for i, det in enumerate(self._detecciones):
            if det.centroide_mm is None:
                continue

            x_mm, y_mm = det.centroide_mm
            centro = self._mm_a_widget(x_mm, y_mm)

            # Tamaño del rectángulo proporcional al bbox
            ancho_mm = det.ancho_px * (1.0 / max(self._px_por_mm, 0.1))
            alto_mm = det.alto_px * (1.0 / max(self._px_por_mm, 0.1))

            # Mínimo visual
            ancho_vis = max(ancho_mm * self._px_por_mm, 20.0)
            alto_vis = max(alto_mm * self._px_por_mm, 15.0)

            # Rectángulo del objeto
            rect = QRectF(
                centro.x() - ancho_vis / 2, centro.y() - alto_vis / 2,
                ancho_vis, alto_vis
            )

            # Color del objeto
            r, g, b = det.color_rgb
            color_obj = QColor(r, g, b, 60)
            color_borde = QColor(r, g, b, 200)

            if det.fuera_de_rango:
                color_borde = QColor(255, 0, 0, 200)

            # Relleno translúcido
            painter.setBrush(QBrush(color_obj))
            painter.setPen(QPen(color_borde, 2))
            painter.drawRect(rect)

            # Centroide (cruz)
            tamano_cruz = 6
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            painter.drawLine(
                QPointF(centro.x() - tamano_cruz, centro.y()),
                QPointF(centro.x() + tamano_cruz, centro.y()),
            )
            painter.drawLine(
                QPointF(centro.x(), centro.y() - tamano_cruz),
                QPointF(centro.x(), centro.y() + tamano_cruz),
            )

            # Etiqueta del objeto
            painter.setFont(fuente_obj)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(
                QPointF(rect.right() + 4, rect.top() + 12),
                f"{det.etiqueta} ({det.confianza:.0%})"
            )

            # Coordenadas
            painter.setFont(fuente_coord)
            painter.setPen(QPen(QColor(200, 255, 200)))
            z_str = f"{det.altura_estimada_mm:.0f}" if det.altura_estimada_mm > 0 else "N/A"
            painter.drawText(
                QPointF(rect.right() + 4, rect.top() + 24),
                f"X:{x_mm:.1f} Y:{y_mm:.1f} Z:{z_str}"
            )

            # Color dominante
            if det.color_dominante != "desconocido":
                painter.setPen(QPen(QColor(r, g, b)))
                painter.drawText(
                    QPointF(rect.right() + 4, rect.top() + 36),
                    f"● {det.color_dominante}"
                )

            # Marcar fuera de rango
            if det.fuera_de_rango:
                painter.setPen(QPen(QColor(255, 0, 0), 2))
                painter.drawLine(rect.topLeft(), rect.bottomRight())
                painter.drawLine(rect.topRight(), rect.bottomLeft())

    def _dibujar_ejes(self, painter: QPainter):
        """Dibuja etiquetas de ejes X e Y."""
        fuente = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(fuente)

        # Etiqueta eje X
        painter.setPen(QPen(QColor(255, 100, 100)))
        painter.drawText(
            QPointF(self.width() - 55, self.height() - 8),
            "X (mm) →"
        )

        # Etiqueta eje Y
        painter.setPen(QPen(QColor(100, 255, 100)))
        painter.save()
        painter.translate(12, 70)
        painter.rotate(-90)
        painter.drawText(QPointF(0, 0), "Y (mm) →")
        painter.restore()

    def _dibujar_info_validacion(self, painter: QPainter):
        """Dibuja información de validación en la esquina superior."""
        if self._validacion is None:
            return

        fuente = QFont("Consolas", 8)
        painter.setFont(fuente)
        y_texto = 14

        if self._validacion["valido"]:
            info = self._validacion["info"]
            painter.setPen(QPen(QColor(Colores.VERDE)))
            painter.drawText(QPointF(8, y_texto), f"✔ ArUco válido — {info['orden']}")
            y_texto += 13
            painter.setPen(QPen(QColor(Colores.TEXTO_SECUNDARIO)))
            painter.drawText(
                QPointF(8, y_texto),
                f"Área: {info['area_cm2']} cm² | Per: {info['perimetro_mm']} mm"
            )
        else:
            painter.setPen(QPen(QColor(Colores.ERROR)))
            for err in self._validacion["errores"]:
                painter.drawText(QPointF(8, y_texto), f"✖ {err}")
                y_texto += 13

        # Advertencias
        for adv in self._validacion.get("advertencias", []):
            y_texto += 13
            painter.setPen(QPen(QColor(Colores.AMARILLO)))
            painter.drawText(QPointF(8, y_texto), f"⚠ {adv}")

    # ═══════════════════════════════════════════════════════
    # Interacción
    # ═══════════════════════════════════════════════════════

    def wheelEvent(self, event):
        """Hace zoom a la imagen de fondo."""
        if self._imagen_fondo is None:
            return

        delta = event.angleDelta().y()
        # Zoom de 10%
        factor = 1.1 if delta > 0 else 0.9
        
        nueva_escala = self._escala_imagen * factor
        # Limitar escala entre 0.1 y 10.0
        if 0.1 <= nueva_escala <= 10.0:
            self._escala_imagen = nueva_escala
            self.update()
            self._emitir_frame_virtual()

    def mousePressEvent(self, event):
        """Inicia arrastre si es clic derecho, o selección si es izquierdo."""
        if event.button() == Qt.MouseButton.RightButton and self._imagen_fondo is not None:
            self._arrastrando_imagen = True
            self._ultimo_pos_raton = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for i, det in enumerate(self._detecciones):
                if det.centroide_mm is None:
                    continue
                centro = self._mm_a_widget(det.centroide_mm[0], det.centroide_mm[1])
                dist = math.sqrt(
                    (pos.x() - centro.x()) ** 2 + (pos.y() - centro.y()) ** 2
                )
                if dist < 25:  # Radio de 25px para click
                    self.objeto_seleccionado.emit(i)
                    logger.debug(f"Vista2D: objeto {i} ({det.etiqueta}) seleccionado")
                    return

    def mouseMoveEvent(self, event):
        """Arrastra imagen simulada o muestra tooltips."""
        pos = event.position()
        
        # Arrastre de imagen simulada
        if self._arrastrando_imagen:
            dx = pos.x() - self._ultimo_pos_raton.x()
            dy = pos.y() - self._ultimo_pos_raton.y()
            self._offset_imagen.setX(self._offset_imagen.x() + dx)
            self._offset_imagen.setY(self._offset_imagen.y() + dy)
            self._ultimo_pos_raton = pos
            self.update()
            self._emitir_frame_virtual()
            return

        # Comportamiento normal de tooltip
        x_mm, y_mm = self._widget_a_mm(pos.x(), pos.y())
        for i, det in enumerate(self._detecciones):
            if det.centroide_mm is None:
                continue
            centro = self._mm_a_widget(det.centroide_mm[0], det.centroide_mm[1])
            dist = math.sqrt(
                (pos.x() - centro.x()) ** 2 + (pos.y() - centro.y()) ** 2
            )
            if dist < 25:
                z_txt = f"{det.altura_estimada_mm:.0f}" if det.altura_estimada_mm > 0 else "N/A"
                self.setToolTip(
                    f"{det.etiqueta} ({det.confianza:.0%})\n"
                    f"X: {det.centroide_mm[0]:.1f} mm\n"
                    f"Y: {det.centroide_mm[1]:.1f} mm\n"
                    f"Z: {z_txt} mm\n"
                    f"Color: {det.color_dominante}"
                )
                return

        self.setToolTip(f"({x_mm:.0f}, {y_mm:.0f}) mm")

    def mouseReleaseEvent(self, event):
        """Termina el arrastre."""
        if event.button() == Qt.MouseButton.RightButton and self._arrastrando_imagen:
            self._arrastrando_imagen = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _emitir_frame_virtual(self):
        """
        Genera un frame 1280x720 que simula lo que vería una cámara cenital.

        Lógica:
        - Con escala=1.0 y offset=(0,0), la imagen COMPLETA se ajusta a 1280x720
          (como si la cámara viera toda la escena).
        - Zoom in (escala > 1): se recorta una porción más pequeña del centro
          y se amplía → YOLO ve los objetos más grandes.
        - Pan (offset): desplaza el centro del recorte.
        """
        if self._imagen_fondo_cv is None:
            return

        w_out, h_out = 1280, 720
        h_orig, w_orig = self._imagen_fondo_cv.shape[:2]

        # ── Paso 1: Escala base para que la imagen COMPLETA quepa en w_out×h_out ──
        escala_base_x = w_out / w_orig
        escala_base_y = h_out / h_orig
        escala_base = min(escala_base_x, escala_base_y)

        # ── Paso 2: Aplicar zoom del usuario ──
        escala_final = escala_base * self._escala_imagen

        # ── Paso 3: Centrar la imagen en el frame de salida ──
        offset_centrado_x = (w_out - w_orig * escala_final) / 2.0
        offset_centrado_y = (h_out - h_orig * escala_final) / 2.0

        # ── Paso 4: Traducir paneo del widget a paneo del frame de salida ──
        ratio_x = w_out / max(self.width(), 1)
        ratio_y = h_out / max(self.height(), 1)
        pan_x = self._offset_imagen.x() * ratio_x
        pan_y = self._offset_imagen.y() * ratio_y

        # ── Paso 5: Construir la matriz afín ──
        M = np.float32([
            [escala_final, 0, offset_centrado_x + pan_x],
            [0, escala_final, offset_centrado_y + pan_y]
        ])

        frame_virtual = cv2.warpAffine(
            self._imagen_fondo_cv, M, (w_out, h_out),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )

        self.frame_virtual_generado.emit(frame_virtual)
