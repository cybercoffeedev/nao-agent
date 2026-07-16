import sys
from openai import OpenAI

class LLMManager:
    """Manages LLM conversations via an OpenAI-compatible API."""
    def __init__(self, api_key: str, url: str, model: str, system_msg: str, max_messages: int = 8):
        """Initializes the LLM manager with API credentials and system prompt.

        Args:
            api_key (str): OpenAI-compatible API key.
            url (str): Base URL for the OpenAI client.
            model (str): The LLM model name to call.
            system_msg (str): System prompt outlining the assistant's behavior/instructions.
            max_messages (int): Maximum number of recent messages to keep in context.
        """
        self.model = model
        self.client = OpenAI(base_url=url, api_key=api_key)
        self.max_messages = max_messages
        self.context = [{"role": "system", "content": system_msg}]

    def _trim_context(self):
        """Trims context to keep only system message + max_messages recent messages."""
        if len(self.context) > self.max_messages + 1:
            self.context = [self.context[0]] + self.context[-(self.max_messages):]

    def add_user_message(self, text: str):
        """Appends a new user message to the conversational history context."""
        self.context.append({"role": "user", "content": text})
        self._trim_context()

    def add_assistant_message(self, text: str):
        """Appends an assistant message to the conversational history context."""
        self.context.append({"role": "assistant", "content": text})
        self._trim_context()

    def generate_response(self):
        """Generates a text response from the LLM model."""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.context,
                stream=False,
                max_tokens=8192,
            )
            text = completion.choices[0].message.content or ""
            self.context.append({"role": "assistant", "content": text})
            self._trim_context()
            return text
        except Exception as e:
            print(f"Couldn't generate a message: {e}", file=sys.stderr)
            return ""
