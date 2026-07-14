import sys
from openai import OpenAI

class LLMManager:
    """Manages LLM conversations via an OpenAI-compatible API."""
    def __init__(self, api_key: str, url: str, model: str, system_msg: str, actions: dict | None = None):
        """Initializes the LLM manager with API credentials and system prompt.

        Args:
            api_key (str): OpenAI-compatible API key.
            url (str): Base URL for the OpenAI client.
            model (str): The LLM model name to call.
            system_msg (str): System prompt outlining the assistant's behavior/instructions.
            actions (dict | None): Robot.ACTIONS dict for auto-generating tool definitions.
        """
        self.model = model
        self.client = OpenAI(base_url=url, api_key=api_key)
        self.context = [{"role": "system", "content": system_msg}]
        self.tools = self._build_tools(actions) if actions else None

    def _build_tools(self, actions: dict) -> list:
        """Converts a Robot.ACTIONS dict into OpenAI tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": info["description"],
                    "parameters": {},
                },
            }
            for name, info in actions.items()
        ]

    def add_user_message(self, text: str):
        """Appends a new user message to the conversational history context.

        Args:
            text (str): The text message sent by the user.
        """
        self.context.append({"role": "user", "content": text})

    def generate_response(self):
        """Generates a response from the LLM model.

        Returns:
            tuple[str, list[str]]: (spoken text, list of action names to execute).
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": self.context,
                "stream": False,
                "max_tokens": 512,
            }
            if self.tools:
                kwargs["tools"] = self.tools

            completion = self.client.chat.completions.create(**kwargs)
            message = completion.choices[0].message

            text = message.content or ""
            tool_calls = [tc.function.name for tc in message.tool_calls] if message.tool_calls else []

            self.context.append({
                "role": "assistant",
                "content": text,
                **({"tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in message.tool_calls
                ]} if message.tool_calls else {}),
            })

            return text, tool_calls
        except Exception as e:
            print(f"Couldn't generate a message: {e}", file=sys.stderr)
            return "", []
