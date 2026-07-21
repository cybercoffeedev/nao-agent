"""LLM conversation manager using OpenAI-compatible API."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).parent.parent / "logs"


class LLMManager:
    """Manages LLM conversations via an OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        url: str,
        model: str,
        system_msg: str,
        max_turns: int = 8,
    ) -> None:
        """Initialize LLM manager.

        Args:
            api_key: API key for authentication.
            url: Base URL for the OpenAI-compatible API.
            model: Model name to use for completions.
            system_msg: System prompt/instruction for the LLM.
            max_turns: Maximum number of conversation turns to keep in context.
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if not url:
            raise ValueError("url cannot be empty")
        if not model:
            raise ValueError("model cannot be empty")

        self.model = model
        self.client = OpenAI(base_url=url, api_key=api_key, timeout=30.0)
        self.max_turns = max_turns
        self.context: list[dict[str, str]] = [{"role": "system", "content": system_msg}]
        self._request_counter: int = 0
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    def _log_request(self, request_kwargs: dict, response_content: str | None) -> None:
        """Log LLM request/response to a JSON file."""
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
            path = LOG_DIR / filename
            path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Could not write LLM log: %s", e)

    def _trim_context(self) -> None:
        """Trim context to keep only the most recent turns."""
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

    def add_user_message(self, text: str) -> None:
        """Add a user message to the context."""
        self.context.append({"role": "user", "content": text})
        self._trim_context()

    def add_assistant_message(self, text: str) -> None:
        """Add an assistant message to the context."""
        self.context.append({"role": "assistant", "content": text})

    def generate_response(self) -> str:
        """Generate a response from the LLM.

        Returns:
            The generated response text, or empty string on error.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.context,
                stream=False,
                max_tokens=8192,
            )
            text: str = completion.choices[0].message.content or ""

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
