MODULE Module1

    VAR socketdev serverSockert;
    VAR socketdev clientSockert;

    VAR string data := "";
    
    ! ── Variables para almacenar X y Y recibidos ──
    VAR num coord_x;
    VAR num coord_y;
    
    ! ── Tu posición maestra (Z constante = 144...) ──
    CONST robtarget ID0:=[[419.654,250,144.000029246],[0,0,1,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];

    ! Posición inicial (ajusta a la que prefieras)
    CONST robtarget pos_inicial := [[400,0,300],[0,0,1,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];


    PROC main()
        SocketCreate serverSockert;
        SocketBind serverSockert,"192.168.1.13",8000;
        SocketListen serverSockert;
        
        WHILE TRUE DO
            TPWrite "Esperando conexion de Python...";
            SocketAccept serverSockert, clientSockert \Time:=WAIT_MAX;
            
            ! Bucle de recepción continua
            WHILE TRUE DO
                SocketReceive clientSockert \Str:=data;
                
                ! Extraer X y Y del texto recibido
                ParsearXY data;
                
                ! Responder a Python para confirmar la recepción
                SocketSend clientSockert \Str:="ACK\0A";
                
                ! Ir a realizar el movimiento
                Path_10;
            ENDWHILE
        ENDWHILE
    
    ERROR
        ! Si hay desconexión, cerrar socket y esperar al siguiente intento
        SocketClose clientSockert;
        RETRY;
    ENDPROC

    ! ── Subrutina para extraer X y Y de la cadena "X:12.3,Y:45.6,Z:..." ──
    PROC ParsearXY(string mensaje)
        VAR num pos_X;
        VAR num pos_Y;
        VAR num pos_Z;
        VAR string str_X;
        VAR string str_Y;
        VAR bool ok;
        
        coord_x := 0;
        coord_y := 0;
        
        ! Buscar posiciones de las letras en el texto
        pos_X := StrFind(mensaje, 1, "X:");
        pos_Y := StrFind(mensaje, 1, "Y:");
        pos_Z := StrFind(mensaje, 1, "Z:");
        
        IF pos_X > 0 AND pos_Y > 0 AND pos_Z > 0 THEN
            str_X := StrPart(mensaje, pos_X + 2, pos_Y - (pos_X + 3));
            str_Y := StrPart(mensaje, pos_Y + 2, pos_Z - (pos_Y + 3));
            
            ok := StrToVal(str_X, coord_x);
            ok := StrToVal(str_Y, coord_y);
        ENDIF
    ENDPROC

    ! ── Subrutina de Movimiento ──
    PROC Path_10()
        VAR robtarget pos_obj;
        VAR robtarget pos_arriba;
        
        ! 1. Mapear X y Y a ID0, manteniendo Z=144.000... intacto
        pos_obj := ID0;
        pos_obj.trans.x := coord_x;
        pos_obj.trans.y := coord_y;
        
        ! 2. Crear posición con Z un poco mas grande (+100 de espacio)
        pos_arriba := pos_obj;
        pos_arriba.trans.z := pos_obj.trans.z + 100;
        
        ! - Primero a posicion inicial (opcional de seguridad)
        MoveJ pos_inicial, v1000, z100, MyTool\WObj:=wobj0;
        
        ! - Ir a X Y con un Z un poco mas grande
        MoveJ pos_arriba, v1000, z50, MyTool\WObj:=wobj0;
        
        ! - Ir directo mediante Linea hacia abajo
        MoveL pos_obj, v100, fine, MyTool\WObj:=wobj0;
        
        WaitTime 0.5; ! Agregar agarre aqui
        
        ! - Luego arriba con Z otra vez
        MoveL pos_arriba, v500, z50, MyTool\WObj:=wobj0;
        
        ! - Luego a su posicion inicial
        MoveJ pos_inicial, v1000, z100, MyTool\WObj:=wobj0;
        
        TPWrite "Ciclo Pick Place finalizado";
    ENDPROC

ENDMODULE
