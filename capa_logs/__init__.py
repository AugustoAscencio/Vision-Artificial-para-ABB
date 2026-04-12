"""Capa de logging — registro centralizado del sistema."""

from .gestor_logs import configurar_logging, obtener_logger, ManejadorUI, obtener_manejador_ui

__all__ = ["configurar_logging", "obtener_logger", "ManejadorUI", "obtener_manejador_ui"]

