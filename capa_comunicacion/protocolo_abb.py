"""
Protocolo de comunicación estructurado para robot ABB.
Formatea y parsea mensajes entre Python y RAPID.
"""

from capa_logs import obtener_logger
from nucleo.modelos import ComandoRobot, DeteccionObjeto

logger = obtener_logger("protocolo")


class ProtocoloABB:
    """
    Protocolo de comunicación estructurada con robot ABB vía RAPID.

    Formato de un objeto:
        "X:120.5,Y:85.3,Z:10.0,C:Rojo,T:Caja"

    Formato de múltiples objetos:
        "N:3|X:120.5,Y:85.3,Z:10.0,C:Rojo,T:Caja_pequena|X:200.0,Y:50.0,Z:30.0,C:Azul,T:Caja_mediana|..."

    Terminador: "\\n"
    """

    SEPARADOR_CAMPOS = ","
    SEPARADOR_OBJETOS = "|"
    TERMINADOR = "\n"

    @staticmethod
    def formatear_comando(comando: ComandoRobot) -> str:
        """
        Formatea un solo ComandoRobot como cadena para RAPID.

        Ejemplo: "X:120.5,Y:85.3,Z:10.0,C:Rojo,T:Caja_pequena\\n"
        """
        cadena = comando.a_cadena() + ProtocoloABB.TERMINADOR
        logger.debug(f"Comando formateado: {cadena.strip()}")
        return cadena

    @staticmethod
    def formatear_multiples(comandos: list[ComandoRobot]) -> str:
        """
        Formatea múltiples comandos en un solo mensaje.

        Ejemplo: "N:2|X:120.5,Y:85.3,Z:10.0,C:Rojo,T:Caja|X:200.0,...\\n"
        """
        if not comandos:
            return f"N:0{ProtocoloABB.TERMINADOR}"

        partes = [f"N:{len(comandos)}"]
        for cmd in comandos:
            partes.append(cmd.a_cadena())

        cadena = ProtocoloABB.SEPARADOR_OBJETOS.join(partes) + ProtocoloABB.TERMINADOR
        logger.debug(f"Multi-comando ({len(comandos)} objetos): {cadena.strip()[:80]}...")
        return cadena

    @staticmethod
    def desde_detecciones(detecciones: list[DeteccionObjeto]) -> str:
        """
        Convierte una lista de DeteccionObjeto directamente a cadena de protocolo.
        Solo incluye detecciones con coordenadas mundo válidas.
        """
        comandos = []
        for det in detecciones:
            cmd = ComandoRobot.desde_deteccion(det)
            if cmd is not None:
                comandos.append(cmd)

        if len(comandos) == 1:
            return ProtocoloABB.formatear_comando(comandos[0])
        else:
            return ProtocoloABB.formatear_multiples(comandos)

    @staticmethod
    def parsear_respuesta(datos: str) -> dict:
        """
        Parsea una respuesta del robot ABB.

        Formato esperado de respuestas:
            "ACK" — Confirmación de recepción
            "POS:X:100,Y:200,Z:300" — Posición actual del robot
            "ERR:mensaje" — Error del robot
            "READY" — Robot listo para recibir
        """
        datos = datos.strip()
        resultado = {"tipo": "desconocido", "raw": datos}

        if datos == "ACK":
            resultado["tipo"] = "confirmacion"
        elif datos == "READY":
            resultado["tipo"] = "listo"
        elif datos.startswith("POS:"):
            resultado["tipo"] = "posicion"
            try:
                partes = datos[4:].split(",")
                for parte in partes:
                    clave, valor = parte.split(":")
                    resultado[clave.strip().lower()] = float(valor)
            except Exception as e:
                logger.warning(f"Error parseando posición: {e}")
        elif datos.startswith("ERR:"):
            resultado["tipo"] = "error"
            resultado["mensaje"] = datos[4:]
        else:
            resultado["tipo"] = "texto"
            resultado["mensaje"] = datos

        return resultado
