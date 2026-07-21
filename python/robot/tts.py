"""Manages robot text-to-speech."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RobotTTS:
    """Manages robot text-to-speech."""

    def __init__(self, tts: Any) -> None:
        """Initialize TTS service.

        Args:
            tts: ALTextToSpeech service.
        """
        self.tts = tts

    def speak(self, text: str) -> None:
        """Say provided message with built-in TTS."""
        try:
            self.tts.say(text)
        except Exception as e:
            logger.error("Couldn't say the message: %s", e)
