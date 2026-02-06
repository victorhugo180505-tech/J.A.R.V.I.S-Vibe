from typing import List, Dict, Optional
from ai.codex_app_server_client import CodexAppServer

class OpenAIChatViaCodexAppServerProvider:
    def __init__(self, app: CodexAppServer, model_general="gpt-5.2", model_code="gpt-5.2-codex"):
        self.app = app
        self.model_general = model_general
        self.model_code = model_code
        self._thread_general: Optional[str] = None
        self._thread_code: Optional[str] = None

    def _ensure_threads(self):
        if not self._thread_general:
            self._thread_general = self.app.start_thread(self.model_general)
        if not self._thread_code:
            self._thread_code = self.app.start_thread(self.model_code)

    def generate(self, messages: List[Dict], task_type: str = "general") -> str:
        """
        messages: estilo OpenAI [{role, content}]
        task_type: 'general' o 'code'
        """
        self._ensure_threads()

        # MVP: usamos el último mensaje del usuario; luego hacemos formateo mejor
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = m.get("content", "")
                break

        if task_type == "code":
            return self.app.run_turn_text(self._thread_code, user_text, model=self.model_code)
        else:
            return self.app.run_turn_text(self._thread_general, user_text, model=self.model_general)
