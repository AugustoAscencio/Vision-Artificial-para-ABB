MODULE ModuloVision
    !═══════════════════════════════════════════════════════════
    ! Módulo RAPID para comunicación con sistema de visión Python
    ! Robot ABB — Pick & Place con Visión Artificial
    !═══════════════════════════════════════════════════════════
    
    ! ── Sockets ──
    VAR socketdev servidor;
    VAR socketdev cliente;
    
    ! ── Datos recibidos ──
    VAR string datos_recibidos;
    VAR bool datos_validos;
    
    ! ── Coordenadas parseadas ──
    VAR num coord_x;
    VAR num coord_y;
    VAR num coord_z;
    VAR string color_obj;
    VAR string tipo_obj;
    
    ! ── Posiciones del robot ──
    CONST robtarget pos_reposo := [[400,0,300],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget pos_dejar := [[400,200,100],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    VAR robtarget pos_objeto;
    
    ! ── Herramienta ──
    PERS tooldata herramienta := [TRUE,[[0,0,100],[1,0,0,0]],[1,[0,0,50],[1,0,0,0],0,0,0]];
    
    ! ── Variables de control ──
    VAR num pos_separador;
    VAR string campo;
    VAR string clave;
    VAR string valor;
    VAR num longitud;
    
    !═══════════════════════════════════════════════════════════
    ! PROCEDIMIENTO PRINCIPAL
    !═══════════════════════════════════════════════════════════
    PROC main()
        ! Iniciar servidor de sockets
        IniciarServidor;
        
        ! Bucle principal
        WHILE TRUE DO
            ! Recibir datos del sistema de visión
            RecibirDatos;
            
            IF datos_validos THEN
                ! Parsear el mensaje
                ParsearMensaje datos_recibidos;
                
                ! Enviar confirmación
                SocketSend cliente \Str:="ACK\0A";
                
                ! Ejecutar pick and place
                ! EjecutarPickPlace;
                
                ! Log
                TPWrite "Objeto: X=" + NumToStr(coord_x,1) + " Y=" + NumToStr(coord_y,1) + " Z=" + NumToStr(coord_z,1) + " C=" + color_obj;
            ENDIF
        ENDWHILE
        
    ERROR
        IF ERRNO = ERR_SOCK_TIMEOUT THEN
            TPWrite "Timeout de socket — esperando reconexión...";
            CerrarSockets;
            IniciarServidor;
            RETRY;
        ELSEIF ERRNO = ERR_SOCK_CLOSED THEN
            TPWrite "Socket cerrado — reconectando...";
            CerrarSockets;
            IniciarServidor;
            RETRY;
        ENDIF
    ENDPROC
    
    !═══════════════════════════════════════════════════════════
    ! INICIAR SERVIDOR TCP
    !═══════════════════════════════════════════════════════════
    PROC IniciarServidor()
        SocketCreate servidor;
        SocketBind servidor, "172.18.9.27", 8000;
        SocketListen servidor;
        TPWrite "Esperando conexión del sistema de visión...";
        SocketAccept servidor, cliente, \Time:=WAIT_MAX;
        TPWrite "Sistema de visión conectado.";
        
        ! Enviar saludo (el script Python lo espera)
        SocketSend cliente \Str:=" ";
    ENDPROC
    
    !═══════════════════════════════════════════════════════════
    ! RECIBIR DATOS
    !═══════════════════════════════════════════════════════════
    PROC RecibirDatos()
        datos_validos := FALSE;
        SocketReceive cliente \Str:=datos_recibidos \Time:=WAIT_MAX;
        
        IF StrLen(datos_recibidos) > 2 THEN
            datos_validos := TRUE;
        ENDIF
    ENDPROC
    
    !═══════════════════════════════════════════════════════════
    ! PARSEAR MENSAJE ESTRUCTURADO
    ! Formato: "X:120.5,Y:85.3,Z:10.0,C:Rojo,T:Caja_pequena"
    !═══════════════════════════════════════════════════════════
    PROC ParsearMensaje(string mensaje)
        VAR num inicio;
        VAR num fin;
        VAR string segmento;
        VAR num pos_dos_puntos;
        VAR string clave_local;
        VAR string valor_local;
        VAR num valor_numerico;
        VAR bool ok_conversion;
        
        ! Inicializar valores por defecto
        coord_x := 0;
        coord_y := 0;
        coord_z := 0;
        color_obj := "?";
        tipo_obj := "?";
        
        inicio := 1;
        longitud := StrLen(mensaje);
        
        WHILE inicio <= longitud DO
            ! Buscar siguiente coma o fin de cadena
            fin := inicio;
            WHILE fin <= longitud AND StrPart(mensaje, fin, 1) <> "," DO
                fin := fin + 1;
            ENDWHILE
            
            ! Extraer segmento (ej: "X:120.5")
            segmento := StrPart(mensaje, inicio, fin - inicio);
            
            ! Buscar los dos puntos
            pos_dos_puntos := 1;
            WHILE pos_dos_puntos <= StrLen(segmento) AND StrPart(segmento, pos_dos_puntos, 1) <> ":" DO
                pos_dos_puntos := pos_dos_puntos + 1;
            ENDWHILE
            
            IF pos_dos_puntos < StrLen(segmento) THEN
                clave_local := StrPart(segmento, 1, pos_dos_puntos - 1);
                valor_local := StrPart(segmento, pos_dos_puntos + 1, StrLen(segmento) - pos_dos_puntos);
                
                ! Asignar según la clave
                IF clave_local = "X" THEN
                    ok_conversion := StrToVal(valor_local, valor_numerico);
                    IF ok_conversion THEN coord_x := valor_numerico; ENDIF
                    
                ELSEIF clave_local = "Y" THEN
                    ok_conversion := StrToVal(valor_local, valor_numerico);
                    IF ok_conversion THEN coord_y := valor_numerico; ENDIF
                    
                ELSEIF clave_local = "Z" THEN
                    ok_conversion := StrToVal(valor_local, valor_numerico);
                    IF ok_conversion THEN coord_z := valor_numerico; ENDIF
                    
                ELSEIF clave_local = "C" THEN
                    color_obj := valor_local;
                    
                ELSEIF clave_local = "T" THEN
                    tipo_obj := valor_local;
                ENDIF
            ENDIF
            
            inicio := fin + 1;
        ENDWHILE
    ENDPROC
    
    !═══════════════════════════════════════════════════════════
    ! EJECUTAR PICK AND PLACE
    !═══════════════════════════════════════════════════════════
    PROC EjecutarPickPlace()
        ! Construir posición destino
        pos_objeto := pos_reposo;
        pos_objeto.trans.x := coord_x;
        pos_objeto.trans.y := coord_y;
        pos_objeto.trans.z := coord_z + 50;  ! Aproximación por encima
        
        ! 1. Ir a posición de reposo
        MoveJ pos_reposo, v500, z50, herramienta;
        
        ! 2. Aproximación al objeto (por encima)
        MoveL pos_objeto, v200, z10, herramienta;
        
        ! 3. Bajar al objeto
        pos_objeto.trans.z := coord_z;
        MoveL pos_objeto, v100, fine, herramienta;
        
        ! 4. Activar gripper (ajustar según tu herramienta)
        ! SetDO DO_Gripper, 1;
        WaitTime 0.5;
        
        ! 5. Subir con el objeto
        pos_objeto.trans.z := coord_z + 100;
        MoveL pos_objeto, v200, z10, herramienta;
        
        ! 6. Ir a posición de dejar
        MoveJ pos_dejar, v500, z50, herramienta;
        
        ! 7. Bajar y soltar
        pos_objeto := pos_dejar;
        pos_objeto.trans.z := 50;
        MoveL pos_objeto, v100, fine, herramienta;
        
        ! SetDO DO_Gripper, 0;
        WaitTime 0.5;
        
        ! 8. Subir y volver a reposo
        MoveL pos_dejar, v200, z10, herramienta;
        MoveJ pos_reposo, v500, z50, herramienta;
        
        TPWrite "Pick & Place completado.";
    ENDPROC
    
    !═══════════════════════════════════════════════════════════
    ! CERRAR SOCKETS (para reconexión limpia)
    !═══════════════════════════════════════════════════════════
    PROC CerrarSockets()
        SocketClose cliente;
        SocketClose servidor;
    ENDPROC
    
ENDMODULE
