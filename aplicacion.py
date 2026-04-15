"""
Controlador principal de la aplicación.
Instancia todas las capas, conecta señales y gestiona el pipeline.
"""

import sys
import time
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt6.QtWidgets import QApplication

from capa_logs import configurar_logging, obtener_logger, obtener_manejador_ui
from capa_configuracion import Ajustes, cargar_ajustes, guardar_ajustes
from capa_adquisicion import ServicioCamara, enumerar_camaras
from capa_procesamiento import CalibradorCamara, Preprocesador
from capa_procesamiento.overlays import MotorOverlays
from capa_geometria import DetectorAruco, CalculadorHomografia, TransformadorCoordenadas
from capa_ia import DetectorYOLO, GestorModelos, AnalizadorColor
from capa_comunicacion import ClienteTCP, ProtocoloABB, SimuladorRobot
from capa_interfaz.tema import aplicar_tema
from capa_interfaz.ventana_principal import VentanaPrincipal
from nucleo.modelos import (
    DeteccionObjeto, ResultadoFrame, MarcadorAruco,
    ComandoRobot, EstadoConexion,
)


logger = obtener_logger("aplicacion")


# ═══════════════════════════════════════════════════════════════
# Hilo de procesamiento (pipeline completo)
# ═══════════════════════════════════════════════════════════════

class HiloProcesamiento(QThread):
    """
    Hilo dedicado al pipeline de procesamiento de visión.
    Recibe frames, ejecuta detección, transforma coordenadas y emite resultados.
    """

    resultado_listo = pyqtSignal(object)   # ResultadoFrame
    detecciones_listas = pyqtSignal(object) # list[DeteccionObjeto]

    def __init__(
        self,
        preprocesador: Preprocesador,
        detector_aruco: DetectorAruco,
        calculador_homografia: CalculadorHomografia,
        transformador: TransformadorCoordenadas,
        detector_yolo: DetectorYOLO,
        analizador_color: AnalizadorColor,
        motor_overlays: MotorOverlays,
        parent=None,
    ):
        super().__init__(parent)
        self._preprocesador = preprocesador
        self._detector_aruco = detector_aruco
        self._homografia = calculador_homografia
        self._transformador = transformador
        self._detector_yolo = detector_yolo
        self._analizador_color = analizador_color
        self._motor_overlays = motor_overlays
        self._frame_pendiente: Optional[np.ndarray] = None
        self._procesando = False
        self._ejecutando = False

    @property
    def esta_ocupado(self) -> bool:
        return self._procesando

    def recibir_frame(self, frame: np.ndarray):
        """Recibe un frame para procesar. Si hay uno pendiente, lo sobreescribe."""
        if not self._procesando:
            self._frame_pendiente = frame

    def iniciar(self):
        self._ejecutando = True
        self.start()

    def detener(self):
        self._ejecutando = False

    def run(self):
        """Bucle de procesamiento continuo."""
        while self._ejecutando:
            if self._frame_pendiente is not None:
                frame = self._frame_pendiente
                self._frame_pendiente = None
                self._procesando = True
                try:
                    resultado = self._procesar_frame(frame)
                    self.resultado_listo.emit(resultado)
                    self.detecciones_listas.emit(resultado.detecciones)
                except Exception as e:
                    logger.error(f"Error en pipeline: {e}", exc_info=True)
                finally:
                    self._procesando = False
            else:
                time.sleep(0.005)  # 5ms idle

    def _procesar_frame(self, frame: np.ndarray) -> ResultadoFrame:
        """Pipeline completo de un frame."""
        inicio = time.perf_counter()

        # 1. Preprocesamiento
        frame_proc = self._preprocesador.procesar(frame)

        # 2. Detección ArUco (siempre se ejecuta para visualización)
        marcadores = self._detector_aruco.detectar(frame_proc)

        # 3. Detección YOLO
        detecciones = self._detector_yolo.detectar(frame_proc)

        # 4. Análisis de color para cada detección
        for det in detecciones:
            nombre_color, rgb = self._analizador_color.color_dominante(frame_proc, det.bbox)
            det.color_dominante = nombre_color
            det.color_rgb = rgb

        # 5. Transformación de coordenadas (si hay homografía)
        if self._homografia.esta_calibrada:
            detecciones = self._transformador.transformar_lote(detecciones)

        # 6. Dibujar overlays
        frame_vis = frame_proc.copy()

        # Dibujar ArUco
        if marcadores:
            frame_vis = self._detector_aruco.dibujar_marcadores(frame_vis, marcadores)

        # Dibujar detecciones YOLO
        if detecciones:
            frame_vis = self._detector_yolo.dibujar_detecciones(frame_vis, detecciones)

        # Overlays AR (crosshair, zona calibrada, rejilla)
        if self._motor_overlays.mostrar_rejilla and self._homografia.esta_calibrada:
            frame_vis = self._motor_overlays.dibujar_zona_calibrada(frame_vis, marcadores)
            frame_vis = self._motor_overlays.dibujar_rejilla(frame_vis, self._homografia)

        if self._motor_overlays.mostrar_crosshair:
            frame_vis = self._motor_overlays.dibujar_crosshair(frame_vis)

        fps = 1.0 / max(time.perf_counter() - inicio, 0.001)

        return ResultadoFrame(
            frame_original=frame,
            frame_procesado=frame_vis,
            detecciones=detecciones,
            marcadores_aruco=marcadores,
            homografia_activa=self._homografia.esta_calibrada,
            fps=fps,
        )


# ═══════════════════════════════════════════════════════════════
# Controlador principal
# ═══════════════════════════════════════════════════════════════

class Aplicacion(QObject):
    """
    Controlador principal que orquesta todas las capas del sistema.
    Hereda de QObject para compatibilidad con señales/slots Qt.
    """

    def __init__(self):
        super().__init__()
        # ── Configuración ──
        self._ajustes = cargar_ajustes()
        errores = self._ajustes.validar()
        if errores:
            print(f"⚠ Errores de configuración: {errores}")

        # ── Logging ──
        self._manejador_ui = configurar_logging(
            nivel=self._ajustes.log_nivel,
            archivo=self._ajustes.log_archivo,
            max_bytes=self._ajustes.log_max_bytes,
            backups=self._ajustes.log_backups,
        )

        logger.info("Inicializando sistema de visión artificial ABB...")

        # ── Capa de procesamiento ──
        self._calibrador_camara = CalibradorCamara()
        self._calibrador_camara.cargar_calibracion()

        self._preprocesador = Preprocesador(
            calibrador=self._calibrador_camara,
            corregir_distorsion=self._ajustes.corregir_distorsion,
            mejorar_contraste=self._ajustes.mejorar_contraste,
            reducir_ruido=self._ajustes.reducir_ruido,
        )

        # ── Capa de geometría ──
        self._detector_aruco = DetectorAruco(self._ajustes.aruco_diccionario)
        self._calculador_homografia = CalculadorHomografia()
        self._calculador_homografia.cargar()

        # Calcular límites dinámicos desde los puntos ArUco (+100mm de margen)
        xs = [p.x_mm for p in self._ajustes.aruco_puntos_mundo]
        ys = [p.y_mm for p in self._ajustes.aruco_puntos_mundo]
        limites = {
            "x_min": min(xs) - 100.0 if xs else -50.0,
            "x_max": max(xs) + 100.0 if xs else 400.0,
            "y_min": min(ys) - 100.0 if ys else -50.0,
            "y_max": max(ys) + 100.0 if ys else 300.0,
        }

        self._transformador = TransformadorCoordenadas(
            calculador_homografia=self._calculador_homografia,
            alturas_por_tipo=self._ajustes.alturas_objetos,
            limites_espacio_mm=limites,
        )

        # ── Capa IA ──
        self._gestor_modelos = GestorModelos()
        self._detector_yolo = DetectorYOLO(
            ruta_modelo=self._gestor_modelos.ruta_modelo(self._ajustes.yolo_modelo),
            confianza=self._ajustes.yolo_confianza,
            iou=self._ajustes.yolo_iou,
            dispositivo=self._ajustes.yolo_dispositivo,
        )
        self._analizador_color = AnalizadorColor()

        # ── Capa adquisición ──
        self._servicio_camara = ServicioCamara()
        self._servicio_camara.configurar(
            self._ajustes.camara_indice,
            self._ajustes.camara_resolucion,
        )

        # ── Capa comunicación ──
        self._cliente_tcp = ClienteTCP()
        self._cliente_tcp.configurar(
            ip=self._ajustes.robot_ip,
            puerto=self._ajustes.robot_puerto,
            reconexion=self._ajustes.reconexion_automatica,
            timeout=self._ajustes.timeout_conexion_s,
        )
        self._protocolo = ProtocoloABB()
        self._simulador: Optional[SimuladorRobot] = None

        # ── Modo simulación ──
        if self._ajustes.modo_simulacion:
            self._simulador = SimuladorRobot("127.0.0.1", self._ajustes.robot_puerto)
            self._simulador.iniciar()
            logger.info("Modo simulacion activado -- simulador ABB corriendo")

        # ── Motor de overlays AR ──
        self._motor_overlays = MotorOverlays()

        # ── Pipeline de procesamiento ──
        self._hilo_procesamiento = HiloProcesamiento(
            preprocesador=self._preprocesador,
            detector_aruco=self._detector_aruco,
            calculador_homografia=self._calculador_homografia,
            transformador=self._transformador,
            detector_yolo=self._detector_yolo,
            analizador_color=self._analizador_color,
            motor_overlays=self._motor_overlays,
        )

        # ── Interfaz gráfica ──
        self._ventana = VentanaPrincipal()
        self._envio_automatico = self._ajustes.envio_automatico
        self._modo_simulador_ui = False
        self._ultimo_resultado: Optional[ResultadoFrame] = None

        # ── Conectar señales ──
        self._conectar_seniales()

        # ── Inicializar UI ──
        self._inicializar_ui()

        logger.info("Sistema inicializado correctamente")

    # ═══════════════════════════════════════════════════════
    # Conexión de señales
    # ═══════════════════════════════════════════════════════

    def _conectar_seniales(self):
        """Conecta todas las señales entre capas."""

        # ── Cámara → Pipeline ──
        self._servicio_camara.frame_listo.connect(self._al_recibir_frame)
        self._servicio_camara.fps_actualizado.connect(self._al_fps_camara)
        self._servicio_camara.error_camara.connect(self._al_error_camara)
        self._servicio_camara.camara_detenida.connect(self._al_camara_detenida)

        # ── Pipeline → UI ──
        self._hilo_procesamiento.resultado_listo.connect(self._al_resultado_procesamiento)
        self._hilo_procesamiento.detecciones_listas.connect(self._al_detecciones_listas)

        # ── TCP → UI ──
        self._cliente_tcp.conexion_cambiada.connect(self._al_conexion_cambiada)
        self._cliente_tcp.mensaje_enviado.connect(self._al_mensaje_enviado)
        self._cliente_tcp.mensaje_recibido.connect(self._al_mensaje_recibido)
        self._cliente_tcp.error_conexion.connect(self._al_error_tcp)

        # ── UI → Acciones ──
        v = self._ventana

        # Control de camara
        v.panel_control.iniciar_camara.connect(self._al_iniciar_camara)
        v.panel_control.detener_camara.connect(self._al_detener_camara)
        v.panel_control.confianza_cambiada.connect(self._al_cambiar_confianza)
        v.panel_control.preprocesamiento_cambiado.connect(self._al_cambiar_preprocesamiento)
        v.panel_control.envio_automatico_cambiado.connect(self._al_cambiar_envio_automatico)
        v.panel_control.imagen_cargada.connect(self._al_cargar_imagen)
        v.panel_control.simulador_cambiado.connect(self._al_cambiar_modo_simulador)

        # Simulación virtual
        v.vista_2d.frame_virtual_generado.connect(self._al_recibir_frame_virtual)

        # Overlays AR
        v.panel_control.crosshair_cambiado.connect(self._al_cambiar_crosshair)
        v.panel_control.rejilla_cambiada.connect(self._al_cambiar_rejilla)

        # Conexion TCP
        v.panel_conexion.solicitar_conexion.connect(self._al_conectar_tcp)
        v.panel_conexion.solicitar_desconexion.connect(self._al_desconectar_tcp)

        # Calibracion
        v.panel_calibracion.solicitar_calibracion.connect(self._al_calibrar_aruco)
        v.panel_calibracion.cargar_calibracion.connect(self._al_cargar_calibracion)
        v.panel_calibracion.guardar_calibracion.connect(self._al_guardar_calibracion)

        # Modelo YOLO
        v.selector_modelo.modelo_seleccionado.connect(self._al_cambiar_modelo)
        v.selector_modelo.recargar_modelos.connect(self._al_recargar_modelos)

        # Deteccion -> Envio
        v.panel_deteccion.enviar_seleccionado.connect(self._al_enviar_seleccionado)
        v.panel_deteccion.enviar_todos.connect(self._al_enviar_todos)

        # ── Logs -> UI ──
        self._manejador_ui.log_emitido.connect(v.panel_logs.agregar_log)

    # ═══════════════════════════════════════════════════════
    # Inicialización UI
    # ═══════════════════════════════════════════════════════

    def _inicializar_ui(self):
        """Establece valores iniciales en la UI."""
        v = self._ventana

        # Conexión
        v.panel_conexion.establecer_ip_puerto(
            self._ajustes.robot_ip,
            self._ajustes.robot_puerto,
        )

        # Cámaras disponibles
        camaras = enumerar_camaras()
        v.panel_control.establecer_camaras(camaras)
        v.panel_control.establecer_confianza(self._ajustes.yolo_confianza)

        # Modelos
        modelos = self._gestor_modelos.listar_modelos()
        v.selector_modelo.establecer_modelos(modelos)
        v.selector_modelo.actualizar_modelo_activo(self._detector_yolo.nombre_modelo)

        # Calibración
        v.panel_calibracion.actualizar_estado(
            self._calculador_homografia.esta_calibrada,
            error_rms=self._calculador_homografia.error_reproyeccion,
        )
        v.barra_estado.actualizar_calibracion(self._calculador_homografia.esta_calibrada)
        v.barra_estado.actualizar_modelo(self._detector_yolo.nombre_modelo)
        
        # Iniciar Vista 2D con los puntos configurados
        v.vista_2d.actualizar_puntos_mundo(self._ajustes.aruco_puntos_mundo)

    # ═══════════════════════════════════════════════════════
    # Handlers — Cámara
    # ═══════════════════════════════════════════════════════

    @pyqtSlot(int)
    def _al_iniciar_camara(self, indice: int):
        logger.info(f"Iniciando cámara {indice}...")
        self._servicio_camara.configurar(indice, self._ajustes.camara_resolucion)
        self._servicio_camara.iniciar_captura()
        self._hilo_procesamiento.iniciar()
        self._ventana.panel_control.actualizar_estado_camara(True)
        self._ventana.barra_estado.actualizar_camara(True)

    @pyqtSlot()
    def _al_detener_camara(self):
        logger.info("Deteniendo cámara...")
        self._servicio_camara.detener_captura()
        self._hilo_procesamiento.detener()
        self._ventana.vista_camara.limpiar()
        self._ventana.panel_control.actualizar_estado_camara(False)
        self._ventana.barra_estado.actualizar_camara(False)

    @pyqtSlot(object)
    def _al_recibir_frame(self, frame: np.ndarray):
        """Frame nuevo de la cámara → enviarlo al pipeline de procesamiento."""
        if not self._modo_simulador_ui:
            self._hilo_procesamiento.recibir_frame(frame)

    @pyqtSlot(float)
    def _al_fps_camara(self, fps: float):
        self._ventana.barra_estado.actualizar_fps(fps)

    @pyqtSlot(str)
    def _al_error_camara(self, error: str):
        logger.error(f"Error de cámara: {error}")

    @pyqtSlot()
    def _al_camara_detenida(self):
        self._ventana.panel_control.actualizar_estado_camara(False)
        self._ventana.barra_estado.actualizar_camara(False)

    # ═══════════════════════════════════════════════════════
    # Handlers — Pipeline
    # ═══════════════════════════════════════════════════════

    @pyqtSlot(object)
    def _al_resultado_procesamiento(self, resultado: ResultadoFrame):
        """Resultado completo del pipeline -> actualizar UI."""
        self._ultimo_resultado = resultado

        # Actualizar estado HUD antes de enviar el frame
        self._ventana.vista_camara.actualizar_estado(
            n_objetos=len(resultado.detecciones),
            calibrada=self._calculador_homografia.esta_calibrada
        )

        # Actualizar vista de camara con frame procesado
        self._ventana.vista_camara.actualizar_frame(resultado.frame_procesado)

        # Actualizar Vista 2D
        self._ventana.vista_2d.actualizar_marcadores(resultado.marcadores_aruco)
        self._ventana.vista_2d.actualizar_detecciones(resultado.detecciones)

        # Actualizar conteo de marcadores ArUco
        self._ventana.panel_calibracion.actualizar_conteo_marcadores(
            len(resultado.marcadores_aruco)
        )

        # Actualizar barra de estado
        self._ventana.barra_estado.actualizar_objetos(len(resultado.detecciones))

        # Actualizar panel debug
        self._ventana.panel_debug.actualizar(resultado)

    @pyqtSlot(str)
    def _al_cargar_imagen(self, ruta: str):
        """Carga una imagen manual, activa el simulador y la procesa."""
        logger.info(f"Cargando imagen para simulador: {ruta}")
        try:
            img_bgr = cv2.imread(ruta)
            if img_bgr is None:
                logger.error("No se pudo leer la imagen")
                return

            # 1. Activar modo simulador PRIMERO (sincrónico en mismo hilo)
            self._modo_simulador_ui = True
            self._ventana.panel_control._chk_simulador.setChecked(True)

            # 2. Asegurar que el hilo de procesamiento esté corriendo
            if not self._hilo_procesamiento._ejecutando:
                self._hilo_procesamiento.iniciar()

            # 3. Establecer imagen (esto emite frame_virtual_generado)
            self._ventana.vista_2d.establecer_imagen_fondo(img_bgr)

            # 4. Respaldo: procesar directamente si la señal no llegó a tiempo
            #    Construir frame virtual = imagen completa escalada a 1280x720
            h, w = img_bgr.shape[:2]
            escala = min(1280 / w, 720 / h)
            nuevo_w = int(w * escala)
            nuevo_h = int(h * escala)
            frame_redim = cv2.resize(img_bgr, (nuevo_w, nuevo_h), interpolation=cv2.INTER_LINEAR)
            frame_virtual = np.zeros((720, 1280, 3), dtype=np.uint8)
            y_off = (720 - nuevo_h) // 2
            x_off = (1280 - nuevo_w) // 2
            frame_virtual[y_off:y_off + nuevo_h, x_off:x_off + nuevo_w] = frame_redim
            self._hilo_procesamiento.recibir_frame(frame_virtual)

            logger.info(f"Imagen simulada cargada: {w}x{h} → frame virtual 1280x720")

        except Exception as e:
            logger.error(f"Error procesando imagen: {e}", exc_info=True)

    @pyqtSlot(object)
    def _al_recibir_frame_virtual(self, frame_virtual: np.ndarray):
        """Cámara simulada desde la Vista 2D -> Alimenta el hilo procesador."""
        if self._modo_simulador_ui:
            self._hilo_procesamiento.recibir_frame(frame_virtual)

    @pyqtSlot(bool)
    def _al_cambiar_modo_simulador(self, activo: bool):
        self._modo_simulador_ui = activo
        logger.info(f"Modo Simulador {'ACTIVADO' if activo else 'DESACTIVADO'}")
        
        # Si se desactiva y el hilo está corriendo sin cámara, tal vez queramos reiniciar stats
        if activo:
            # Forzar pipeline asíncrono si no está on
            if not self._hilo_procesamiento._ejecutando:
                self._hilo_procesamiento.iniciar()
        else:
            if not self._servicio_camara.esta_activa:
                self._hilo_procesamiento.detener()

    @pyqtSlot(object)
    def _al_detecciones_listas(self, detecciones: list):
        """Detecciones listas -> actualizar tabla y envio automatico."""
        self._ventana.panel_deteccion.actualizar_detecciones(detecciones)

        # Envio automatico al robot
        if self._envio_automatico and self._cliente_tcp.esta_conectado:
            # Solo usar px como fallback si NO hay homografía calibrada
            usar_px = self._modo_simulador_ui and not self._calculador_homografia.esta_calibrada
            comandos = []
            for d in detecciones:
                cmd = ComandoRobot.desde_deteccion(d, usar_pixeles=usar_px)
                if cmd:
                    comandos.append(cmd)
            if comandos:
                for cmd in comandos:
                    mensaje = ProtocoloABB.formatear_comando(cmd)
                    self._cliente_tcp.enviar(mensaje)
                    logger.info(f"Auto-enviado: {mensaje.strip()}")

    # ═══════════════════════════════════════════════════════
    # Handlers — TCP
    # ═══════════════════════════════════════════════════════

    @pyqtSlot(str, int)
    def _al_conectar_tcp(self, ip: str, puerto: int):
        logger.info(f"Conectando a {ip}:{puerto}...")
        self._cliente_tcp.configurar(ip, puerto, self._ajustes.reconexion_automatica)
        self._cliente_tcp.conectar(ip, puerto)

    @pyqtSlot()
    def _al_desconectar_tcp(self):
        logger.info("Desconectando TCP...")
        self._cliente_tcp.desconectar()

    @pyqtSlot(object)
    def _al_conexion_cambiada(self, estado: EstadoConexion):
        self._ventana.panel_conexion.actualizar_estado(estado)
        self._ventana.barra_estado.actualizar_tcp(estado)

    @pyqtSlot(str)
    def _al_mensaje_enviado(self, mensaje: str):
        self._ventana.panel_conexion.actualizar_ultimo_mensaje(f"-> {mensaje}")
        self._ventana.panel_debug.actualizar_tcp_enviado(mensaje)

    @pyqtSlot(str)
    def _al_mensaje_recibido(self, mensaje: str):
        self._ventana.panel_conexion.actualizar_ultimo_mensaje(f"<- {mensaje}")
        self._ventana.panel_debug.actualizar_tcp_recibido(mensaje)
        respuesta = self._protocolo.parsear_respuesta(mensaje)
        logger.info(f"Respuesta robot: {respuesta}")

    @pyqtSlot(str)
    def _al_error_tcp(self, error: str):
        logger.warning(f"TCP: {error}")

    # ═══════════════════════════════════════════════════════
    # Handlers — Calibración
    # ═══════════════════════════════════════════════════════

    @pyqtSlot()
    def _al_calibrar_aruco(self):
        """Calibra la homografía usando el frame actual y los marcadores ArUco."""
        if self._ultimo_resultado is None:
            logger.warning("No hay frame disponible — inicia la cámara primero")
            return

        marcadores = self._ultimo_resultado.marcadores_aruco
        if len(marcadores) < 4:
            logger.warning(
                f"Solo {len(marcadores)} marcadores detectados — se necesitan 4 mínimo"
            )
            self._ventana.panel_calibracion.actualizar_estado(False, len(marcadores))
            return

        exito = self._calculador_homografia.recalcular(
            marcadores,
            self._ajustes.aruco_puntos_mundo,
        )

        self._ventana.panel_calibracion.actualizar_estado(
            exito,
            len(marcadores),
            self._calculador_homografia.error_reproyeccion,
        )
        self._ventana.barra_estado.actualizar_calibracion(exito)

        if exito:
            logger.info("Calibración ArUco exitosa")
        else:
            logger.error("Calibración ArUco fallida")

    @pyqtSlot()
    def _al_cargar_calibracion(self):
        exito = self._calculador_homografia.cargar()
        self._ventana.panel_calibracion.actualizar_estado(exito)
        self._ventana.barra_estado.actualizar_calibracion(exito)

    @pyqtSlot()
    def _al_guardar_calibracion(self):
        self._calculador_homografia.guardar()

    # ═══════════════════════════════════════════════════════
    # Handlers — Modelo YOLO
    # ═══════════════════════════════════════════════════════

    @pyqtSlot(str)
    def _al_cambiar_modelo(self, ruta: str):
        logger.info(f"Cambiando modelo a: {ruta}")
        exito = self._detector_yolo.cambiar_modelo(ruta)
        if exito:
            nombre = self._detector_yolo.nombre_modelo
            self._ventana.selector_modelo.actualizar_modelo_activo(nombre)
            self._ventana.barra_estado.actualizar_modelo(nombre)
            # Persistir seleccion en ajustes
            self._ajustes.yolo_modelo = ruta
            logger.info(f"Modelo activo: {nombre}")

    @pyqtSlot()
    def _al_recargar_modelos(self):
        modelos = self._gestor_modelos.listar_modelos()
        self._ventana.selector_modelo.establecer_modelos(modelos)

    @pyqtSlot(float)
    def _al_cambiar_confianza(self, valor: float):
        self._detector_yolo.confianza = valor
        logger.debug(f"Confianza YOLO: {valor:.0%}")

    @pyqtSlot(bool, bool, bool)
    def _al_cambiar_preprocesamiento(self, contraste: bool, ruido: bool, distorsion: bool):
        self._preprocesador.mejorar_contraste = contraste
        self._preprocesador.reducir_ruido = ruido
        self._preprocesador.corregir_distorsion = distorsion

    @pyqtSlot(bool)
    def _al_cambiar_envio_automatico(self, activo: bool):
        self._envio_automatico = activo
        logger.info(f"Envio automatico: {'ACTIVADO' if activo else 'DESACTIVADO'}")

    @pyqtSlot(bool)
    def _al_cambiar_crosshair(self, activo: bool):
        self._motor_overlays.mostrar_crosshair = activo
        logger.debug(f"Crosshair: {'ACTIVADO' if activo else 'DESACTIVADO'}")

    @pyqtSlot(bool)
    def _al_cambiar_rejilla(self, activo: bool):
        self._motor_overlays.mostrar_rejilla = activo
        logger.debug(f"Rejilla AR: {'ACTIVADO' if activo else 'DESACTIVADO'}")

    # ═══════════════════════════════════════════════════════
    # Handlers — Envío manual
    # ═══════════════════════════════════════════════════════

    @pyqtSlot(int)
    def _al_enviar_seleccionado(self, indice: int):
        det = self._ventana.panel_deteccion.obtener_deteccion(indice)
        if det is None:
            return
        # Solo usar px como fallback si NO hay homografía
        usar_px = self._modo_simulador_ui and not self._calculador_homografia.esta_calibrada
        if det:
            cmd = ComandoRobot.desde_deteccion(det, usar_pixeles=usar_px)
            if not cmd:
                logger.warning(
                    f"No se puede enviar '{det.etiqueta}' — "
                    f"centroide_mm={det.centroide_mm}, fuera_de_rango={det.fuera_de_rango}"
                )
                return

            mensaje = ProtocoloABB.formatear_comando(cmd)
            self._cliente_tcp.enviar(mensaje)
            logger.info(f"Enviado: {mensaje.strip()}")
        else:
            logger.warning("No se puede enviar — sin coordenadas disponibles")

    @pyqtSlot()
    def _al_enviar_todos(self):
        if self._ultimo_resultado is None:
            return
        # Solo usar px como fallback si NO hay homografía
        usar_px = self._modo_simulador_ui and not self._calculador_homografia.esta_calibrada
        detecciones = self._ultimo_resultado.detecciones
        comandos = []
        for d in detecciones:
            cmd = ComandoRobot.desde_deteccion(d, usar_pixeles=usar_px)
            if cmd:
                comandos.append(cmd)
        if comandos:
            for cmd in comandos:
                mensaje = ProtocoloABB.formatear_comando(cmd)
                self._cliente_tcp.enviar(mensaje)
                logger.info(f"Enviado: {mensaje.strip()}")
            logger.info(f"Total enviados: {len(comandos)} objetos")
        else:
            logger.warning("No hay objetos válidos para enviar")

    # ═══════════════════════════════════════════════════════
    # Lifecycle
    # ═══════════════════════════════════════════════════════

    def mostrar(self):
        """Muestra la ventana principal."""
        self._ventana.show()

    def cerrar(self):
        """Cierre limpio de todos los recursos."""
        logger.info("Cerrando sistema...")

        # Detener camara
        self._servicio_camara.detener_captura()
        self._servicio_camara.wait(3000)

        # Detener pipeline
        self._hilo_procesamiento.detener()
        self._hilo_procesamiento.wait(3000)

        # Desconectar TCP
        self._cliente_tcp.desconectar()
        self._cliente_tcp.wait(3000)

        # Detener simulador
        if self._simulador:
            self._simulador.detener()

        # Guardar configuracion
        self._ajustes.robot_ip = self._ventana.panel_conexion.ip
        self._ajustes.robot_puerto = self._ventana.panel_conexion.puerto
        guardar_ajustes(self._ajustes)

        # Remover ManejadorUI del logger para evitar error atexit
        import logging
        logger_raiz = logging.getLogger("vision_abb")
        if self._manejador_ui in logger_raiz.handlers:
            logger_raiz.removeHandler(self._manejador_ui)
            self._manejador_ui._cerrado = True

        logger.info("Sistema cerrado correctamente")
