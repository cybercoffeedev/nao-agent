"""LLM conversation manager using OpenAI-compatible API."""

import logging
import time

from openai import OpenAI

logger = logging.getLogger(__name__)

MAX_RETRIES: int = 3
BASE_DELAY: float = 1.0

CORE_SYSTEM_PROMPT = """\
You are a voice assistant for a NAO robot. Always respond in the same language as the user.

Always respond as a JSON array of steps. Format:
[{"speak": "text"}, {"action": "name", "args": {"param": "value"}}]

Rules:
- Never use Markdown
- Always return a JSON array
- Actions without arguments do not require the "args" field
- Use "speak" to say something to the user
- Combine "action" and "speak" in the same step when the robot should do something and say something
"""


def build_system_prompt(actions: dict[str, str], user_prompt: str = "") -> str:
    """Build full system prompt from core instructions, actions and user customization.

    Args:
        actions: Mapping of action name to description.
        user_prompt: Optional user-defined prompt appended at the end.
    """
    sections = [CORE_SYSTEM_PROMPT]

    if actions:
        lines = ["Available actions:"]
        for name, desc in actions.items():
            lines.append(f"- {name} - {desc}")
        sections.append("\n".join(lines) + "\n")

    if user_prompt.strip():
        sections.append(user_prompt.strip())

    return "\n".join(sections)


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
            system_msg: Full system prompt for the LLM.
            max_turns: Maximum number of conversation turns to keep in context.
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if not url:
            raise ValueError("url cannot be empty")
        if not model:
            raise ValueError("model cannot be empty")

        self.model = model
        self.client = OpenAI(base_url=url, api_key=api_key, timeout=30.0, max_retries=0)
        self.max_turns = max_turns
        self.context: list[dict[str, str]] = [{"role": "system", "content": system_msg}]

    def _trim_context(self) -> None:
        """Trim context to keep the most recent assistant turns."""
        assistant_count = sum(1 for m in self.context if m.get("role") == "assistant")
        if assistant_count <= self.max_turns:
            return

        target = assistant_count - self.max_turns
        count = 0
        for i, msg in enumerate(self.context):
            if msg.get("role") == "assistant":
                count += 1
                if count == target:
                    self.context = [self.context[0]] + self.context[i:]
                    return

    def add_user_message(self, text: str) -> None:
        """Add a user message to the context."""
        self.context.append({"role": "user", "content": text})
        self._trim_context()

    def generate_response(self) -> str:
        """Generate a response from the LLM with retry.

        Returns:
            The generated response text, or empty string on error.
        """
        for attempt in range(MAX_RETRIES):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.context,
                    max_tokens=256,
                    stream=False,
                )
                if not completion.choices:
                    logger.error("LLM returned no choices")
                    return ""
                text: str = completion.choices[0].message.content or ""

                if text:
                    self.context.append({"role": "assistant", "content": text})
                    self._trim_context()
                return text
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    delay = BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "LLM error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, MAX_RETRIES, delay, e,
                    )
                    time.sleep(delay)
                else:
                    logger.error("LLM error after %d attempts: %s", MAX_RETRIES, e)
                    return ""
