# ===============================
# main.py (listo para pegar) ✅
# - No borra nada: solo comenta DeepSeek y usa OpenAI OAuth (Codex CLI).
# - Detecta "code" vs "general" automáticamente.
# - Permite forzar modo con prefijos:
#   - "/code ..."  -> task_type="code"
#   - "/chat ..."  -> task_type="general"
# - Imprime el modelo REAL usado (si openai_oauth soporta return_meta=True)
# - Fallback anti-JSON roto: no crashea si el modelo contesta texto plano
# - Opción B: si el JSON viene roto, hace 1 segunda llamada para "repair" a JSON válido
# - Anti-crash WS 1009: limita el tamaño del audio_b64 antes de mandarlo por WS
# ===============================

# from ai.deepseek import ask_deepseek  # (comentado) DeepSeek ya no es el cerebro principal
from ai.openai_oauth import ask_openai_oauth

from dotenv import load_dotenv
load_dotenv(".env.local")  # carga ese archivo en os.environ
import os
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

import json
import queue
import re
import threading
import time
from core.actions_contract import action_request_from_dict
from core.memory import add_message, get_conversation
from core.policy_gate import classify_action
from core.parser import parse_response
from actions.dispatcher import cancel_pending_action, confirm_pending_action, dispatch_action

from jarvis_avatar_web.server.avatar_ws_client import AvatarWSClient
from jarvis_avatar_web.server import mouse_stream_auto
from jarvis_avatar_web.server import ws_server as avatar_ws_server
from native_bridge import http_bridge
from core.control_server import ControlServer
from core.conversation_flow import apply_speaking, apply_thinking, handle_tts_ended
from core.state import state
from core.stt_azure import AzureSpeechListener
from core.subtitles import emit_subtitle
from core.wake_bargein import detect_wake_word, trigger_wake_barge_in
from core.tts_chunker import send_tts_chunks

# ===============================
# Azure Speech (DEV LOCAL)
# ===============================

AZURE_KEY = AZURE_SPEECH_KEY
AZURE_REGION = AZURE_SPEECH_REGION
AZURE_VOICE = "es-MX-DaliaNeural"

SYSTEM_PROMPT = """
Eres JARVIS, un asistente virtual que controla una computadora con Windows.

CAPACIDADES REALES (NO INVENTAR):
- SOLO puedes ejecutar acciones usando los tipos listados abajo.
- Algunas acciones están restringidas por allowlist (apps permitidas).
- NO puedes usar teclado ni mouse, NO simules teclas, NO controles GUI.
- Si el usuario pide algo fuera de capacidades: explica la limitación y ofrece alternativas dentro de acciones.

RESPONDE SIEMPRE en JSON válido, sin texto adicional.

Formato obligatorio:
{
  "speech": "Texto breve que dirás al usuario",
  "emotion": "neutral | happy | sad | relaxed | surprised | angry | sarcastic | thinking | confident | tired | smug | annoyed | scared",
  "action": {
    "type": "none | open_app | open_url | youtube_control | play_spotify | reset_memory | delete_memory | calendar_write | github_write | screenshare_toggle | audio_share_toggle",
    "data": {}
  }
}

=== ACCIONES DISPONIBLES ===

1) open_app
data: { "app_name": "CANONICAL_NAME" }

Apps permitidas (CANONICAL_NAME):
- notepad
- spotify

Aliases (entrada del usuario -> CANONICAL_NAME):
- "bloc de notas" -> notepad
- "notas" -> notepad
- "spotify" -> spotify

Regla open_app:
- Usa SIEMPRE el CANONICAL_NAME anterior.
- Si el usuario pide una app que NO está en la lista permitida: action.type="none" y en speech di que no está permitida y sugiere preguntar "¿qué apps están permitidas?".

2) open_url
data: { "url": "https://..." }

3) youtube_control
data:
{
  "command": "open_video | play | pause | toggle | volume_up | volume_down | set_volume | seek_forward | seek_backward | next | prev",
  "query": "texto SOLO para open_video",
  "value": "número entre 0 y 1 SOLO para set_volume"
}

4) play_spotify
Usar SOLO para música (si el usuario pide música y spotify está permitido).

5) reset_memory
data: {}

6) delete_memory
Alias de reset_memory.

7) calendar_write
data: { "intent": "..." }

8) github_write
data: { "intent": "..." }

9) screenshare_toggle
data: { "intent": "..." }

10) audio_share_toggle
data: { "intent": "..." }

=== REGLAS IMPORTANTES ===
- Si el usuario menciona video/youtube/reproducción/pausa/volumen -> youtube_control
- Si el usuario dice "borra memoria" o "delete_memory" -> action.type="reset_memory" (o "delete_memory") y speech breve.
- Si el usuario pide github/calendar write -> action.type="github_write"/"calendar_write" con data mínimo {"intent":"..."}.
- Si el usuario pregunta "qué puedes hacer" o "qué apps están permitidas":
  - Responde en speech con una lista breve de acciones y apps permitidas.
  - action.type="none"
- NUNCA inventes acciones que no existan.
- No agregues campos extra.
- Sé conciso.

CONFIRMACIÓN (IMPORTANTE):
- Algunas acciones pueden requerir confirmación por seguridad.
- Si el sistema te pide confirmación (por ejemplo te llega una pregunta de confirmar), responde con "speech" pidiendo "confirmar" o "cancelar" y action.type="none".

Acciones sensibles (requieren confirmación):
- delete_memory
- reset_memory
- calendar_write
- github_write
- screenshare_toggle
- audio_share_toggle
"""

SUPPORTED_EMOTIONS = {
    "neutral", "happy", "sad", "relaxed", "angry", "surprised",
    "sarcastic", "thinking", "confident", "tired", "smug", "annoyed", "scared",
}

def normalize_emotion(e: str) -> str:
    if not isinstance(e, str):
        return "neutral"
    e = e.strip().lower()
    if e not in SUPPORTED_EMOTIONS:
        return "neutral"
    return e

def have_azure_config() -> bool:
    return bool((AZURE_KEY or "").strip()) and bool((AZURE_REGION or "").strip())

def prepare_tts_text(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    text = re.sub(r"\bjarvis\b", "Yarvis", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwow\b", "woooow", text, flags=re.IGNORECASE)
    return text

def start_local_servers():
    stop_handles = {}

    try:
        stop_handles["avatar_ws"] = avatar_ws_server.start_server_in_thread(with_console=False)
        print("✔ Avatar WS server iniciado desde main.py")
    except Exception as exc:
        print(f"⚠️ No se pudo iniciar Avatar WS server: {exc}")

    try:
        stop_handles["http_bridge"] = http_bridge.HttpBridgeServer()
        stop_handles["http_bridge"].start()
        print("✔ HTTP bridge iniciado desde main.py")
    except Exception as exc:
        stop_handles.pop("http_bridge", None)
        print(f"⚠️ No se pudo iniciar HTTP bridge: {exc}")

    try:
        stop_handles["mouse_stream"] = mouse_stream_auto.start_mouse_stream_in_thread(verbose=False)
        print("✔ Mouse listener iniciado desde main.py")
    except Exception as exc:
        print(f"⚠️ No se pudo iniciar mouse listener: {exc}")

    return stop_handles

def normalize_text(text: str) -> str:
    return (text or "").strip()

# ===============================
# Routing: code vs general
# ===============================

CODE_HINTS = [
    "error", "exception", "traceback", "stack", "stacktrace", "segfault", "core dumped",
    "compile", "compila", "compilación", "linker", "undefined reference", "ld:",
    "python", "c++", "cpp", "java", "javascript", "typescript", "node", "npm", "pip",
    "leetcode", "codeforces", "icpc", "algoritmo", "complexity", "big-o", "dp", "graph",
    "bug", "fix", "refactor", "regex", "sql", "api", "endpoint", "docker", "wsl",
    "git", "github", "pr", "pull request", "commit",
    "```", "class ", "def ", "import ", "#include", "int main", "std::", "public static",
]

def detect_task_type(user_text: str) -> str:
    t = (user_text or "").strip()
    low = t.lower()

    if low.startswith("/code "):
        return "code"
    if low == "/code":
        return "code"
    if low.startswith("/chat "):
        return "general"
    if low == "/chat":
        return "general"

    for k in CODE_HINTS:
        if k in low:
            return "code"
    return "general"

def strip_force_prefix(user_text: str) -> str:
    t = (user_text or "").strip()
    low = t.lower()
    if low.startswith("/code "):
        return t[6:].strip()
    if low.startswith("/chat "):
        return t[6:].strip()
    if low == "/code" or low == "/chat":
        return ""
    return user_text

def _safe_print(s: str) -> None:
    try:
        print(s)
    except Exception:
        try:
            print(s.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
        except Exception:
            print(repr(s))

# ===============================
# Opción B: Repair a JSON válido
# ===============================

def _wrap_as_json_fallback(text: str) -> dict:
    safe = (text or "").strip()
    if not safe:
        safe = "Lo siento, no pude interpretar la respuesta."
    return {
        "speech": safe[:800],
        "emotion": "neutral",
        "action": {"type": "none", "data": {}},
    }

def _build_json_repair_messages(system_prompt: str, user_text: str, bad_output: str, task_type: str) -> list:
    repair_system = f"""
Eres un "JSON repair bot" para JARVIS.

Devuelve SOLO JSON válido (sin texto adicional, sin markdown, sin ```).
Esquema exacto:
{{
  "speech": "string",
  "emotion": "neutral | happy | sad | relaxed | surprised | angry | sarcastic | thinking | confident | tired | smug | annoyed | scared",
  "action": {{
    "type": "none | open_app | open_url | youtube_control | play_spotify",
    "data": {{}}
  }}
}}

Reglas:
- Output: SOLO JSON.
- No inventes campos.
- Si el output original trae código o markdown, ponlo como texto dentro de "speech" (texto plano).
- Si task_type == "code", action.type debe ser "none".
"""

    payload = {
        "task_type": task_type,
        "original_system_prompt": system_prompt,
        "user_text": user_text,
        "bad_output": bad_output,
    }

    return [
        {"role": "system", "content": repair_system.strip()},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]

def parse_or_repair_json(
    raw_response: str,
    *,
    task_type: str,
    system_prompt_used: str,
    user_text: str,
    ask_fn,
    max_repairs: int = 1
) -> dict:
    # 1) intento normal
    try:
        return parse_response(raw_response)
    except Exception as e:
        first_err = e

    # 2) repair
    last_err = None
    repaired_raw = None

    for _ in range(max_repairs):
        try:
            repair_messages = _build_json_repair_messages(
                system_prompt=system_prompt_used,
                user_text=user_text,
                bad_output=raw_response,
                task_type=task_type,
            )

            # Repair SIEMPRE con "general" (más obediente al formato estricto)
            repaired_raw = ask_fn(repair_messages, task_type="general")
            return parse_response(repaired_raw)

        except Exception as e:
            last_err = e
            continue

    _safe_print(f"⚠️ JSON repair falló. first_err={first_err} last_err={last_err}")
    return _wrap_as_json_fallback(repaired_raw if repaired_raw else raw_response)

# ===============================
# MAIN HANDLER
# ===============================

def handle_user_text(user_text: str, *, emit_user_subtitle: bool = True):
    normalized_input = (user_text or "").strip().lower()
    if normalized_input in {"confirmar", "confirm"}:
        result = confirm_pending_action(send_fn=avatar.send_json, state=state)
        if result is None:
            _safe_print("ℹ️ No hay acción pendiente para confirmar.")
        elif result.ok:
            _safe_print("✔ " + str(result.output))
        else:
            _safe_print("⚠️ Acción no ejecutada: " + str(result.error))
        return
    if normalized_input in {"cancelar", "cancel"}:
        result = cancel_pending_action(send_fn=avatar.send_json, state=state)
        if result is None:
            _safe_print("ℹ️ No hay acción pendiente para cancelar.")
        else:
            _safe_print("⚠️ Acción cancelada.")
        return
    user_text = normalize_text(user_text)
    if not user_text:
        return

    task_type = detect_task_type(user_text)
    user_text = strip_force_prefix(user_text)

    if not user_text:
        _safe_print("ℹ️ Modo cambiado. Escribe tu mensaje después de /code o /chat.")
        return

    if emit_user_subtitle:
        emit_subtitle(state, avatar.send_json, "user", user_text)
    add_message("user", user_text)
    apply_thinking(state)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(get_conversation())

    try:
        try:
            raw_response, used_model = ask_openai_oauth(messages, task_type=task_type, return_meta=True)
            _safe_print(f"[LLM] task={task_type} model={used_model}")
        except TypeError:
            raw_response = ask_openai_oauth(messages, task_type=task_type)
            used_model = None
            _safe_print(f"[LLM] task={task_type} model=(unknown)  (actualiza openai_oauth.py para return_meta=True)")
    except Exception as e:
        _safe_print(f"⚠️ Error comunicándose con la IA: {e}")
        return

    data = parse_or_repair_json(
        raw_response,
        task_type=task_type,
        system_prompt_used=SYSTEM_PROMPT,
        user_text=user_text,
        ask_fn=ask_openai_oauth,
        max_repairs=1,
    )

    emo = normalize_emotion(data.get("emotion", "neutral"))
    speech = (data.get("speech", "") or "").strip()
    tts_text = prepare_tts_text(speech)

    add_message("assistant", speech)
    state.set_last_jarvis_utterance(speech)
    _safe_print(f"Jarvis [{task_type}] ({emo}): {speech}")

    # 1) mood persistente
    avatar.send_emotion(emo)

    # 2) TTS (Azure) -> WS type:"tts"
    if tts_text and have_azure_config():
        try:
            from core.azure_tts import synthesize_tts_with_visemes
            apply_speaking(state)

            # Anti-1009: limita payload grande
            MAX_AUDIO_B64 = 900_000  # ~0.9MB para evitar frames >1MB
            tts_session_id["value"] += 1
            session_token = tts_session_id["value"]
            tts_session_key = f"{int(time.time()*1000)}-{session_token}"
            tts_session_id["key"] = tts_session_key

            def synthesize_chunk(text: str):
                return synthesize_tts_with_visemes(
                    text,
                    key=AZURE_KEY,
                    region=AZURE_REGION,
                    voice=AZURE_VOICE
                )

            send_tts_chunks(
                tts_text,
                emotion=emo,
                session_id=tts_session_key,
                synthesize_fn=synthesize_chunk,
                send_fn=avatar.send_raw,
                subtitle_fn=None,
                session_getter=get_tts_session_id,
                session_token=session_token,
                max_audio_b64=MAX_AUDIO_B64,
                log_fn=_safe_print,
            )

        except Exception as e:
            _safe_print("[AZURE] FAIL -> fallback say: " + repr(e))
            avatar.send_say(speech, emo)
    else:
        if not tts_text:
            _safe_print("[TTS] speech vacío -> no mando TTS.")
        elif not have_azure_config():
            _safe_print("[TTS] falta AZURE_KEY/AZURE_REGION -> fallback say.")
        avatar.send_say(speech, emo)

    # 3) acción windows
    try:
        action_request = action_request_from_dict(data["action"])
        classification = classify_action(action_request)
        action_request.requires_confirm = bool(classification["requires_confirm"])
        action_request.risk = str(classification["risk"])
        action_request.summary = str(classification["summary"])

        result = dispatch_action(action_request, send_fn=avatar.send_json, state=state)
        if result.ok:
            _safe_print("✔ " + str(result.output))
        else:
            _safe_print("⚠️ Acción no ejecutada: " + str(result.error))
    except Exception as e:
        _safe_print("⚠️ Error ejecutando acción: " + str(e))

def stop_local_servers(stop_handles):
    bridge = stop_handles.get("http_bridge")
    if bridge:
        bridge.stop()

    stop_event = stop_handles.get("avatar_ws")
    if stop_event:
        stop_event.set()

    mouse_stop = stop_handles.get("mouse_stream")
    if mouse_stop:
        mouse_stop.set()

server_handles = start_local_servers()

avatar = AvatarWSClient("ws://127.0.0.1:8765")
avatar.start()
tts_session_id = {"value": 0, "key": None}

def get_tts_session_id() -> int:
    return tts_session_id["value"]

def cancel_tts_session() -> None:
    tts_session_id["value"] += 1

def on_state_change(payload: dict) -> None:
    avatar.send_json(payload)
    if payload.get("conversation_state") == "LISTENING":
        cancel_tts_session()

def on_avatar_message(msg: dict) -> None:
    if msg.get("type") != "tts_ended":
        return
    session_id = msg.get("tts_session_id")
    if session_id and session_id == tts_session_id.get("key"):
        handle_tts_ended(state)

state.set_state_change_handler(on_state_change)
avatar.set_on_message(on_avatar_message)
control_server = ControlServer(state)
control_server.start()
whisper_listener = AzureSpeechListener(
    state,
    key=AZURE_SPEECH_KEY,
    region=AZURE_SPEECH_REGION,
)

print("Jarvis iniciado. Escribe 'salir' para terminar.")
print("Tip: fuerza modo con '/code ...' o '/chat ...'.")

try:
    input_queue: "queue.Queue[tuple[str, bool]]" = queue.Queue()
    stop_event = threading.Event()

    def stdin_worker():
        while not stop_event.is_set():
            try:
                user_input = input("Tú: ").strip()
            except EOFError:
                break
            if user_input:
                input_queue.put((user_input, True))

    threading.Thread(target=stdin_worker, daemon=True).start()

    wake_words = ("oye jarvis", "hey jarvis")
    wake_ttl_seconds = float(os.getenv("WAKE_TTL_SECONDS", "30"))
    armed_until = {"value": 0.0}
    last_wake_ts = {"value": 0.0}

    def play_wake_beep():
        try:
            import winsound
            winsound.Beep(880, 500)
        except Exception:
            return

    def on_transcript(text: str):
        raw_text = normalize_text(text)
        if not raw_text:
            return
        emit_subtitle(state, avatar.send_json, "user", raw_text)
        now = time.time()
        matched_wake, remainder = detect_wake_word(raw_text, wake_words)
        if matched_wake:
            if now - last_wake_ts["value"] < 0.4:
                return
            last_wake_ts["value"] = now
            trigger_wake_barge_in(state, avatar.send_json, tts_session_id)
            armed_until["value"] = now + wake_ttl_seconds
            play_wake_beep()
            threading.Timer(1.2, lambda: state.set_wake_active(False)).start()
            if remainder:
                input_queue.put((remainder, False))
                state.set_wake_active(False)
            return
        if now <= armed_until["value"]:
            input_queue.put((raw_text, False))
            armed_until["value"] = 0.0
            state.set_wake_active(False)

    whisper_listener.start(on_transcript)

    while True:
        try:
            user_input, emit_user_subtitle = input_queue.get(timeout=0.1)
        except queue.Empty:
            continue
        if user_input.lower() == "salir":
            break
        handle_user_text(user_input, emit_user_subtitle=emit_user_subtitle)

finally:
    whisper_listener.stop()
    avatar.stop()
    control_server.stop()
    stop_local_servers(server_handles)
