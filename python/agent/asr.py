"""Speech recognition using local whisper.cpp HTTP server."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)


class WhisperASR:
    """Speech recognition using a local whisper.cpp HTTP server."""

    def __init__(self, whisper_url: str, local_wav_path: str) -> None:
        """Initialize the Whisper ASR client.

        Args:
            whisper_url: Base URL of the whisper.cpp server (e.g. http://127.0.0.1:8080).
            local_wav_path: Local path where the WAV audio file is stored.
        """
        if not whisper_url:
            raise ValueError("whisper_url cannot be empty")

        self.whisper_url = whisper_url.rstrip("/")
        self.local_wav_path = local_wav_path

    def _cleanup(self) -> None:
        """Safely remove the local WAV file if it exists."""
        try:
            if os.path.exists(self.local_wav_path):
                os.remove(self.local_wav_path)
        except OSError as e:
            logger.warning("Could not remove WAV file: %s", e)

    def transcribe_audio(self) -> str:
        """Send the audio file to whisper.cpp and return the recognized text."""
        if not os.path.exists(self.local_wav_path):
            logger.error("WAV file not found: %s", self.local_wav_path)
            return ""

        url = f"{self.whisper_url}/inference"
        try:
            with open(self.local_wav_path, "rb") as f:
                response = httpx.post(
                    url,
                    files={"file": ("capture.wav", f, "audio/wav")},
                    data={
                        "temperature": "0.0",
                        "temperature_inc": "0.2",
                        "response_format": "json",
                    },
                    timeout=60.0,
                )
            response.raise_for_status()
            return response.json().get("text", "").strip()
        except httpx.HTTPError as e:
            logger.error("whisper.cpp request failed: %s", e)
            return ""
        except (ValueError, KeyError) as e:
            logger.error("Failed to parse whisper.cpp response: %s", e)
            return ""
        finally:
            self._cleanup()
