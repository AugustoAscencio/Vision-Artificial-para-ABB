MODULE Module1

    ! ══════════════════════════════════════════════════════════
    ! Sistema de Visión Artificial — Módulo ABB
    ! Recibe coordenadas (mm) desde Python via TCP/IP
    !
    ! Formato: "X:583.4,Y:-218.7,Z:80.0,C:Blanco,T:Caja\n"
    !
    ! ⚠ IMPORTANTE: StrFind en RAPID busca CARACTERES del set,
    !   NO subcadenas. Por eso parseamos por COMAS (char único).
    ! ══════════════════════════════════════════════════════════

    VAR socketdev serverSocket;
    VAR socketdev clientSocket;

    VAR string data := "";

    ! Coordenadas parseadas
    VAR num coord_x := 0;
    VAR num coord_y := 0;
    VAR num coord_z := 0;

    ! ── Posiciones de referencia ──
    CONST robtarget ID0 := [[419.654, 250, 144.000029246],
                            [0, 0, 1, 0],
                            [0, 0, 0, 0],
                            [9E9, 9E9, 9E9, 9E9, 9E9, 9E9]];

    CONST robtarget HOME := [[506.291650772, 0, 679.49999918],
                             [0.499999994, 0, 0.866025407, 0],
                             [0, 0, 0, 0],
                             [9E9, 9E9, 9E9, 9E9, 9E9, 9E9]];

    CONST num ALTURA_APROX := 100;

    ! ══════════════════════════════════════════════════════════
    ! MAIN
    ! ══════════════════════════════════════════════════════════
    PROC main()

        TPWrite "=== Sistema Vision ABB Iniciado ===";

        SocketCreate serverSocket;
        SocketBind serverSocket, "192.168.1.13", 8000;
        SocketListen serverSocket;

        TPWrite "Escuchando en 192.168.1.13:8000";

        WHILE TRUE DO

            TPWrite "Esperando conexion...";
            SocketAccept serverSocket, clientSocket \Time:=WAIT_MAX;
            TPWrite "Cliente conectado!";

            WHILE TRUE DO

                SocketReceive clientSocket \Str:=data;

                IF ParsearPorComas(data) THEN
                    TPWrite "→ X=" \Num:=coord_x;
                    TPWrite "  Y=" \Num:=coord_y;
                    TPWrite "  Z=" \Num:=coord_z;

                    SocketSend clientSocket \Str:="ACK\0A";
                    EjecutarPick;
                ELSE
                    TPWrite "ERROR: Parseo fallido";
                    TPWrite "Dato: " + data;
                    SocketSend clientSocket \Str:="ERR:PARSE\0A";
                ENDIF

            ENDWHILE

        ENDWHILE

    ERROR
        IF ERRNO = ERR_SOCK_TIMEOUT THEN
            TPWrite "Timeout socket";
            RETRY;
        ELSEIF ERRNO = ERR_SOCK_CLOSED THEN
            TPWrite "Cliente desconectado";
            SocketClose clientSocket;
            RETRY;
        ELSE
            TPWrite "Error: " \Num:=ERRNO;
            SocketClose clientSocket;
            RETRY;
        ENDIF

    ENDPROC

    ! ══════════════════════════════════════════════════════════
    ! PARSER POR COMAS
    !
    ! Formato fijo: "X:{val},Y:{val},Z:{val},C:{val},T:{val}"
    !
    ! Estrategia segura: buscar comas (carácter único, StrFind
    ! funciona correcto) y extraer campos por posición.
    !
    ! Campo 1 (X): desde pos 1 hasta coma1
    ! Campo 2 (Y): desde coma1+1 hasta coma2
    ! Campo 3 (Z): desde coma2+1 hasta coma3
    ! ══════════════════════════════════════════════════════════
    FUNC bool ParsearPorComas(string msg)

        VAR num coma1;
        VAR num coma2;
        VAR num coma3;
        VAR num largo;
        VAR string str_val;
        VAR bool ok;

        largo := StrLen(msg);

        ! ── Buscar las 3 primeras comas ──
        ! StrFind con "," busca el CARACTER coma → correcto
        coma1 := StrFind(msg, 1, ",");
        IF coma1 > largo THEN
            TPWrite "Error: no hay coma 1";
            RETURN FALSE;
        ENDIF

        coma2 := StrFind(msg, coma1 + 1, ",");
        IF coma2 > largo THEN
            TPWrite "Error: no hay coma 2";
            RETURN FALSE;
        ENDIF

        coma3 := StrFind(msg, coma2 + 1, ",");
        IF coma3 > largo THEN
            TPWrite "Error: no hay coma 3";
            RETURN FALSE;
        ENDIF

        ! ── Extraer X ──
        ! Campo 1: "X:583.4" → desde pos 3 hasta coma1-1
        ! (saltamos "X:" que son 2 caracteres)
        IF coma1 > 3 THEN
            str_val := StrPart(msg, 3, coma1 - 3);
            ok := StrToVal(str_val, coord_x);
            IF NOT ok THEN
                TPWrite "Error X: '" + str_val + "'";
                RETURN FALSE;
            ENDIF
        ELSE
            TPWrite "Error: campo X muy corto";
            RETURN FALSE;
        ENDIF

        ! ── Extraer Y ──
        ! Campo 2: "Y:-218.7" → desde coma1+3 hasta coma2-1
        ! (coma1+1 = inicio campo Y, +2 para saltar "Y:")
        IF coma2 - coma1 > 3 THEN
            str_val := StrPart(msg, coma1 + 3, coma2 - coma1 - 3);
            ok := StrToVal(str_val, coord_y);
            IF NOT ok THEN
                TPWrite "Error Y: '" + str_val + "'";
                RETURN FALSE;
            ENDIF
        ELSE
            TPWrite "Error: campo Y muy corto";
            RETURN FALSE;
        ENDIF

        ! ── Extraer Z ──
        ! Campo 3: "Z:80.0" → desde coma2+3 hasta coma3-1
        IF coma3 - coma2 > 3 THEN
            str_val := StrPart(msg, coma2 + 3, coma3 - coma2 - 3);
            IF str_val = "NULL" THEN
                coord_z := 0;
            ELSE
                ok := StrToVal(str_val, coord_z);
                IF NOT ok THEN
                    coord_z := 0;
                ENDIF
            ENDIF
        ELSE
            coord_z := 0;
        ENDIF

        RETURN TRUE;

    ENDFUNC

    ! ══════════════════════════════════════════════════════════
    ! MOVIMIENTO PICK
    ! ══════════════════════════════════════════════════════════
    PROC EjecutarPick()

        VAR robtarget pos_obj;
        VAR robtarget pos_arriba;

        pos_obj := ID0;
        pos_obj.trans.x := coord_x;
        pos_obj.trans.y := coord_y;

        IF coord_z > 0 THEN
            pos_obj.trans.z := coord_z;
        ENDIF

        pos_arriba := pos_obj;
        pos_arriba.trans.z := pos_obj.trans.z + ALTURA_APROX;

        ! 1. HOME
        MoveJ HOME, v800, z100, tool0\WObj:=wobj0;

        ! 2. Aproximación
        MoveJ pos_arriba, v800, z50, tool0\WObj:=wobj0;

        ! 3. Descenso al objeto
        MoveL pos_obj, v100, fine, tool0\WObj:=wobj0;

        ! 4. Gripper (agregar Set/Reset DO aquí)
        WaitTime 0.5;

        ! 5. Subir
        MoveL pos_arriba, v400, z50, tool0\WObj:=wobj0;

        ! 6. HOME
        MoveJ HOME, v800, z100, tool0\WObj:=wobj0;

        TPWrite "Pick OK → (" \Num:=coord_x;
        TPWrite ", " \Num:=coord_y;
        TPWrite ")";

    ENDPROC

ENDMODULE
