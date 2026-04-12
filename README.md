# 🦾 Sistema de Visión Artificial ABB — Pick & Place

Sistema completo y profesional de visión artificial para automatizar operaciones **pick and place** con robot ABB, comunicación TCP/RAPID, calibración ArUco, detección YOLO e interfaz PyQt6.

---

## 📋 Requisitos

- Python 3.10+
- Cámara USB o IP
- Robot ABB con controlador TCP (RAPID)
- (Opcional) GPU NVIDIA con CUDA para inferencia acelerada

## 🚀 Instalación

```bash
pip install -r requirements.txt
```

## ▶️ Ejecución

```bash
python main.py
```

Para generar marcadores ArUco imprimibles:
```bash
python generar_arucos.py
```

---

## 🏗️ Arquitectura

```
vision_artificial_abb/
├── main.py                          # Punto de entrada
├── aplicacion.py                    # Controlador principal (orquestador)
├── capa_configuracion/              # Ajustes YAML + validación
├── capa_logs/                       # Logging con rotación + handler UI
├── nucleo/                          # Bus de eventos, modelos de dominio
├── capa_adquisicion/                # Captura de cámara (QThread)
├── capa_procesamiento/              # Calibración intrínseca, corrección
├── capa_geometria/                  # ArUco, homografía, conversión coords
├── capa_ia/                         # YOLO, gestión modelos, color K-Means
├── capa_comunicacion/               # TCP no-bloqueante, protocolo ABB
└── capa_interfaz/                   # PyQt6 dashboard completo
```

### Pipeline de procesamiento

```
Cámara → Preprocesamiento → ArUco → YOLO → Color → Coordenadas(mm) → Protocolo → Robot ABB
   ↓                                                                                 ↑
   └───────────────── Interfaz PyQt6 (visualización + control) ─────────────────────┘
```

---

## 📐 Calibración ArUco

### Preparación
1. Ejecuta `python generar_arucos.py` → genera 4 marcadores PNG en `marcadores_aruco/`
2. Imprime los marcadores a **50mm × 50mm** (tamaño real)
3. Pega los marcadores en las 4 esquinas de la mesa de trabajo
4. Mide las posiciones (X, Y en mm) de cada marcador respecto al **origen del robot**

### Configuración
Edita `capa_configuracion/config_defecto.yaml`:
```yaml
aruco:
  puntos_mundo:
    - id: 0
      x_mm: 0.0      # Esquina inferior izquierda
      y_mm: 0.0
    - id: 1
      x_mm: 300.0     # Esquina inferior derecha
      y_mm: 0.0
    - id: 2
      x_mm: 300.0     # Esquina superior derecha
      y_mm: 200.0
    - id: 3
      x_mm: 0.0       # Esquina superior izquierda
      y_mm: 200.0
```

### Calibración en la interfaz
1. Inicia la cámara → asegúrate de que los 4 marcadores son visibles
2. Presiona **"Calibrar con ArUco"**
3. Verifica que el estado cambia a **"✔ Calibrado"**
4. Presiona **"Guardar"** para persistir la calibración

---

## 🔌 Protocolo de Comunicación ABB

### Formato de mensaje (Python → RAPID)

**Un objeto:**
```
X:120.5,Y:85.3,Z:10.0,C:Rojo,T:Caja_pequena\n
```

**Múltiples objetos:**
```
N:3|X:120.5,Y:85.3,Z:10.0,C:Rojo,T:Caja_pequena|X:200.0,Y:50.0,Z:30.0,C:Azul,T:Caja_mediana|...\n
```

### Respuestas del robot (RAPID → Python)
- `ACK` — Confirmación de recepción
- `READY` — Robot listo
- `ERR:mensaje` — Error

### Código RAPID
El archivo `rapid/modulo_vision.mod` contiene un módulo RAPID completo que:
- Escucha conexiones TCP en 172.18.9.27:8000
- Parsea el formato estructurado `X:...,Y:...,Z:...,C:...,T:...`
- Ejecuta secuencia pick and place (descomentar `EjecutarPickPlace`)
- Maneja reconexión automática ante errores de socket

---

## 🤖 Modelos YOLO

- El modelo `yolov8n.pt` se descarga automáticamente en la primera ejecución
- Para usar modelos custom, colócalos en la carpeta `modelos/`
- Cambia de modelo en caliente desde la interfaz sin reiniciar

Modelos compatibles: `yolov8n.pt`, `yolov8s.pt`, `yolov8m.pt`, `yolov8l.pt`, custom `.pt`

---

## 🧪 Modo Simulación

Para probar sin robot físico:

1. Edita `capa_configuracion/config_defecto.yaml`:
```yaml
modo_simulacion: true
robot:
  ip: "127.0.0.1"
```

2. Ejecuta `python main.py` — el simulador TCP arranca automáticamente
3. Presiona **"Conectar"** con IP `127.0.0.1` — verás las respuestas ACK

---

## 🎨 Interfaz Gráfica

Dashboard de 3 columnas con tema oscuro industrial:

| Columna | Contenido |
|---------|-----------|
| Izquierda | Conexión TCP, Calibración ArUco, Controles |
| Centro | Feed de cámara en vivo con overlays |
| Derecha | Tabla de detecciones, Selector YOLO, Logs |

- **No-bloqueante**: Cámara y procesamiento en hilos dedicados
- **Reactiva**: Actualización inmediata de todos los paneles
- **Logs en tiempo real**: Con colores por nivel y filtros

---

## ⚙️ Configuración

Toda la configuración se gestiona desde `capa_configuracion/config_defecto.yaml`.
Los cambios de IP/puerto se guardan automáticamente al cerrar la aplicación.

---

## 📁 Archivos Generados

| Archivo | Propósito |
|---------|-----------|
| `config_usuario.yaml` | Config personalizada (se crea al guardar) |
| `calibracion/homografia.npz` | Matriz de homografía guardada |
| `calibracion/calibracion_camara.npz` | Calibración intrínseca |
| `logs/vision_abb.log` | Archivo de log rotativo |
| `marcadores_aruco/*.png` | Marcadores para impresión |
