import json
import logging
import os
from datetime import datetime, timezone
from openai import OpenAI

logger = logging.getLogger(__name__)

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")


class LLMManager:
    """Manages LLM conversations via an OpenAI-compatible API."""
    def __init__(self, api_key: str, url: str, model: str, system_msg: str, max_turns: int = 3):
        """Initializes the LLM manager with API credentials and system prompt.

        Args:
            api_key (str): OpenAI-compatible API key.
            url (str): Base URL for the OpenAI client.
            model (str): The LLM model name to call.
            system_msg (str): System prompt outlining the assistant's behavior/instructions.
            max_turns (int): Maximum number of recent user turns to keep in context.
        """
        self.model = model
        self.client = OpenAI(base_url=url, api_key=api_key, timeout=120.0)
        self.max_turns = max_turns
        self.context = [{"role": "system", "content": system_msg}]
        self._request_counter = 0
        os.makedirs(LOG_DIR, exist_ok=True)

    def _log_request(self, request_kwargs: dict, response_content: str | None,
                     response_tool_calls: list | None):
        """Saves the request and response to a JSON log file."""
        self._request_counter += 1
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{ts}_{self._request_counter:04d}.json"

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": request_kwargs.get("model"),
            "request": {
                "messages": request_kwargs.get("messages"),
                "tools": [
                    {"name": t["function"]["name"], "description": t["function"]["description"]}
                    for t in (request_kwargs.get("tools") or [])
                ],
            },
            "response": {
                "content": response_content,
                "tool_calls": response_tool_calls,
            },
        }

        try:
            path = os.path.join(LOG_DIR, filename)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
            logger.debug("Logged LLM request to %s", path)
        except Exception as e:
            logger.warning("Could not write LLM log: %s", e)

    def _trim_context(self):
        """Trims context to keep only system message + last N complete turns.

        A turn starts at a user message and includes everything until the
        next user message (assistant replies, tool calls, tool results).
        """
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

    def add_message(self, role: str, text: str):
        """Appends a message to the conversational history context.

        Args:
            role (str): Message role - "user" or "assistant".
            text (str): Message content.
        """
        self.context.append({"role": role, "content": text})
        self._trim_context()

    def add_tool_result(self, tool_call_id: str, content: str):
        """Appends a tool result message to the conversational history.

        Args:
            tool_call_id (str): The ID of the tool call this result responds to.
            content (str): The result content from the tool execution.
        """
        self.context.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })
        self._trim_context()

    def generate_response(self, tools=None):
        """Generates a response from the LLM model.

        Args:
            tools: Optional list of OpenAI function tool schemas.

        Returns:
            ChatCompletionMessage with .content and .tool_calls attributes.
        """
        kwargs = {
            "model": self.model,
            "messages": self.context,
            "stream": False,
        }
        if tools:
            kwargs["tools"] = tools

        completion = self.client.chat.completions.create(**kwargs)
        message = completion.choices[0].message

        tool_calls_data = None
        if message.tool_calls:
            tool_calls_data = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]

        self._log_request(kwargs, message.content, tool_calls_data)

        assistant_msg = {"role": "assistant"}
        if message.content:
            assistant_msg["content"] = message.content
        if tool_calls_data:
            assistant_msg["tool_calls"] = tool_calls_data

        self.context.append(assistant_msg)
        self._trim_context()
        return message
