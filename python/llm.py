import logging
import os
import json
from datetime import datetime, timezone
from openai import OpenAI

logger = logging.getLogger(__name__)

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")


class LLMManager:
    """Manages LLM conversations via an OpenAI-compatible API."""

    def __init__(self, api_key: str, url: str, model: str, system_msg: str, max_turns: int = 8):
        self.model = model
        self.client = OpenAI(base_url=url, api_key=api_key, timeout=30.0)
        self.max_turns = max_turns
        self.context = [{"role": "system", "content": system_msg}]
        self._request_counter = 0
        os.makedirs(LOG_DIR, exist_ok=True)

    def _log_request(self, request_kwargs: dict, response_content: str | None):
        self._request_counter += 1
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{ts}_{self._request_counter:04d}.json"

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": request_kwargs.get("model"),
            "request": {
                "messages": request_kwargs.get("messages"),
            },
            "response": {
                "content": response_content,
            },
        }

        try:
            path = os.path.join(LOG_DIR, filename)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Could not write LLM log: %s", e)

    def _trim_context(self):
        user_count = sum(1 for m in self.context if m.get("role") == "user")
        if user_count <= self.max_turns:
            return

        count = 0
        cutoff = user_count - self.max_turns + 1
        for i, msg in enumerate(self.context):
            if msg.get("role") == "user":
                count += 1
                if count == cutoff:
                    self.context = [self.context[0]] + self.context[i:]
                    return

    def add_user_message(self, text: str):
        self.context.append({"role": "user", "content": text})
        self._trim_context()

    def add_assistant_message(self, text: str):
        self.context.append({"role": "assistant", "content": text})

    def generate_response(self):
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.context,
                stream=False,
                max_tokens=8192,
            )
            text = completion.choices[0].message.content or ""

            self._log_request(
                {"model": self.model, "messages": self.context},
                text,
            )

            self.context.append({"role": "assistant", "content": text})
            self._trim_context()
            return text
        except Exception as e:
            logger.error("LLM error: %s", e)
            return ""
