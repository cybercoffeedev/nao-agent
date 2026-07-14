import sys
from openai import OpenAI

class LLMManager:
    """Manages LLM conversations via an OpenAI-compatible API."""
    def __init__(self, api_key: str, url: str, model: str, system_msg: str):
        """Initializes the LLM manager with API credentials and system prompt.

        Args:
            api_key (str): OpenAI-compatible API key.
            url (str): Base URL for the OpenAI client.
            model (str): The LLM model name to call.
            system_msg (str): System prompt outlining the assistant's behavior/instructions.
        """
        self.model = model
        self.client = OpenAI(base_url=url, api_key=api_key)
        self.context = [{"role": "system", "content": system_msg}]

    def add_user_message(self, text: str):
        """Appends a new user message to the conversational history context.

        Args:
            text (str): The text message sent by the user.
        """
        self.context.append({"role": "user", "content": text})

    def generate_response(self):
        """Generates a text response from the LLM model."""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.context,
                stream=False,
                max_tokens=512
            )
            out = completion.choices[0].message.content
            self.context.append({"role": "assistant", "content": out})
            return out
        except Exception as e:
            print(f"Couldn't generate a message: {e}", file=sys.stderr)
