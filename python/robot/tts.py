import sys

class RobotTTS:
    """Manages robot text-to-speech."""

    def __init__(self, tts):
        """Initializes TTS service.

        Args:
            tts: ALTextToSpeech service.
        """
        self.tts = tts

    def speak(self, text: str):
        """Says provided message with built-in TTS.

        Args:
            text (str): The text message to speak.
        """
        self.tts.setLanguage("Polish")
        try:
            self.tts.say(text)
        except Exception as e:
            print(f"Couldn't say the message: {e}", file=sys.stderr)
