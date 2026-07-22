"""LLM conversation manager using OpenAI-compatible API."""

import logging

from openai import OpenAI

from .llm_logger import LLMLogger

logger = logging.getLogger(__name__)


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
        self._logger = LLMLogger()

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
            if not completion.choices:
                logger.error("LLM returned no choices")
                return ""
            text: str = completion.choices[0].message.content or ""

            self._logger.log(
                {"model": self.model, "messages": self.context},
                text,
            )

            if text:
                self.context.append({"role": "assistant", "content": text})
            return text
        except Exception as e:
            logger.error("LLM error: %s", e)
            return ""
