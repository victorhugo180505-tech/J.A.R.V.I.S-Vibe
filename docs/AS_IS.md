# AS-IS (arquitectura actual)

## 1) Árbol de carpetas relevante (rutas clave)

```
./
├── tools/
│   └── wake_jarvis.py
├── main.py
├── core/
│   ├── control_server.py
│   ├── state.py
│   ├── stt_azure.py
│   ├── azure_tts.py
│   ├── wake_word.py
│   └── vision_capture.py
├── ai/
│   └── openai_oauth.py
├── actions/
│   ├── dispatcher.py
│   ├── open_app.py
│   ├── open_url.py
│   └── youtube_ext.py
├── native_bridge/
│   └── http_bridge.py
└── jarvis_avatar_web/
    └── server/
        ├── avatar_ws_client.py
        ├── ws_server.py
        └── mouse_stream_auto.py
```

## 2) Flujo runtime (alto nivel)

1. `tools/wake_jarvis.py`
   - Escucha wake word (`openwakeword`) y al detectar:
     - Verifica Codex CLI (`codex.ps1`).
     - Lanza backend (`main.py`) si `/health` no responde.
     - Lanza Tauri avatar (DEV) si no está corriendo.
     - Hace `POST /mic/toggle` al backend.
2. `main.py`
   - Levanta servidores locales:
     - Avatar WS server (`jarvis_avatar_web/server/ws_server.py`).
     - HTTP bridge (`native_bridge/http_bridge.py`).
     - Mouse stream auto (`jarvis_avatar_web/server/mouse_stream_auto.py`).
   - Conecta WS client hacia el Avatar (`AvatarWSClient`).
   - Inicia `ControlServer` (HTTP de estado y toggles).
   - Inicia STT (Azure) y escucha transcripciones.
3. `core/control_server.py`
   - HTTP endpoints de salud/estado y toggles (mic, audio, vision).
4. STT/TTS
   - STT: `core/stt_azure.py` produce texto → `handle_user_text()`.
   - TTS: `core/azure_tts.py` genera `audio_b64 + visemes` → WS `type: tts`.
5. Avatar WS
   - `avatar_ws_client.py` envía mensajes (`emotion`, `say`, `tts`, `mouse`) a `ws_server.py`.

Flujo solicitado (resumen):
```
tools/wake_jarvis.py
  -> main.py
    -> control_server
      -> STT/TTS
        -> avatar WS
```

## 3) Puertos/endpoints/WS actuales + payloads (ejemplos)

### ControlServer (HTTP)
- **Base**: `http://127.0.0.1:8780`
- `GET /health`
  - Respuesta:
    ```json
    {"ok": true}
    ```
- `GET /state`
  - Respuesta:
    ```json
    {
      "audio_enabled": false,
      "mic_enabled": false,
      "vision_enabled": false,
      "wake_active": false
    }
    ```
- `POST /mic/toggle`
  - Respuesta:
    ```json
    {"mic_enabled": true}
    ```
- `POST /audio/toggle`
  - Respuesta:
    ```json
    {"audio_enabled": true}
    ```
- `POST /vision/toggle`
  - Respuesta:
    ```json
    {"vision_enabled": true}
    ```
- `GET /vision/snapshot?monitor=1`
  - Respuesta: `image/png` (bytes) o error JSON.

### Avatar WS (WebSocket)
- **WS**: `ws://127.0.0.1:8765`
- **Mensajes entrantes/salientes** (JSON string):
  - Estado inicial al conectar:
    ```json
    {"type": "state", "emotion": "neutral", "mouse": {"x": 0.0, "y": 0.0}, "updated_at": 0}
    ```
  - Set emoción:
    ```json
    {"type": "emotion", "emotion": "happy"}
    ```
  - Say (texto):
    ```json
    {"type": "say", "emotion": "neutral", "text": "Hola"}
    ```
  - Mouse (NDC -1..1):
    ```json
    {"type": "mouse", "x": 0.12, "y": -0.34}
    ```
  - TTS con visemas (desde `main.py`):
    ```json
    {
      "type": "tts",
      "emotion": "thinking",
      "audio_b64": "<base64 WAV>",
      "visemes": [{"t": 12, "id": 4}, {"t": 24, "id": 8}]
    }
    ```

### HTTP Bridge (Native Host)
- **HTTP**: `http://127.0.0.1:8766/command`
  - Payload (se reenvía por TCP al native host de Chrome):
    ```json
    {"type": "open_url", "data": {"url": "https://example.com"}}
    ```
- **TCP**: `127.0.0.1:8767`
  - Conexión entrante del native host (Chrome extension).

### Otros
- Tauri DEV se lanza desde `tools/wake_jarvis.py` (no expone puerto fijo aquí).

## 4) Módulos clave y responsabilidades

- `tools/wake_jarvis.py`
  - Wake word + orquestación: arranca backend, Tauri y mic toggle.
- `main.py`
  - Orquestador principal: IO, LLM, STT/TTS, WS avatar, ControlServer.
- `core/control_server.py`
  - HTTP de estado/toggles + snapshot de visión.
- `core/state.py`
  - Estado compartido (audio, mic, vision, wake).
- `core/stt_azure.py`
  - STT continuo Azure (mic → texto).
- `core/azure_tts.py`
  - TTS Azure (texto → WAV base64 + visemas).
- `core/wake_word.py`
  - Wake word local (openwakeword + sounddevice).
- `core/vision_capture.py`
  - Screenshot (mss) cuando `vision_enabled`.
- `ai/openai_oauth.py`
  - Llamadas LLM vía Codex CLI (modelos chat/code).
- `actions/dispatcher.py`
  - Ejecuta acciones (open_app, youtube_control; open_url aún vacío).
- `native_bridge/http_bridge.py`
  - Bridge HTTP→TCP con native host de Chrome.
- `jarvis_avatar_web/server/ws_server.py`
  - Hub WS del avatar (state, emotion, say, mouse, tts).
- `jarvis_avatar_web/server/avatar_ws_client.py`
  - Cliente WS desde backend.
- `jarvis_avatar_web/server/mouse_stream_auto.py`
  - Trackea cursor y emite `mouse` por WS.

## 5) “Puntos frágiles” (NO tocar sin validar launcher)

- **Puertos/URLs fijos**:
  - `ControlServer` en `127.0.0.1:8780` (wake_jarvis usa `/health` y `/mic/toggle`).
  - Avatar WS en `127.0.0.1:8765` (client y mouse stream dependen).
  - HTTP bridge en `127.0.0.1:8766` + TCP `8767`.
- **Wake word**:
  - `wake_jarvis.py` usa `wake_word="hey_jarvis_v0.1"` y el modelo de `openwakeword`.
- **PATH fix / imports**:
  - `wake_jarvis.py` fuerza `REPO_ROOT` en `sys.path` para imports; moverlo rompe arranque.
- **Arranque en nueva consola (Windows)**:
  - `launch_backend()` y `launch_tauri()` usan `creationflags=subprocess.CREATE_NEW_CONSOLE`.
- **Codex CLI**:
  - `CODEX_CLI_PWSH` apunta a `codex.ps1` (si se mueve, falla LLM).
- **Límites WS**:
  - `main.py` limita `audio_b64` (~0.9MB) para evitar WS 1009 (no quitar sin revisar).
- **Acciones disponibles**:
  - `dispatcher.py` solo reconoce `none`, `open_app`, `youtube_control`; el prompt permite más, pero no están implementadas.

> Nota: este documento describe el estado actual (AS-IS) sin refactors.
