"""Speech recognition using local whisper.cpp HTTP server."""

import logging
import os
import urllib.request
import urllib.error
import json

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

        boundary = "----NaOWhisperBoundary"
        with open(self.local_wav_path, "rb") as f:
            audio_data = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="capture.wav"\r\n'
            f"Content-Type: audio/wav\r\n\r\n"
        ).encode() + audio_data + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="temperature"\r\n\r\n'
            f"0.0\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="temperature_inc"\r\n\r\n'
            f"0.2\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="response_format"\r\n\r\n'
            f"json\r\n"
            f"--{boundary}--\r\n"
        ).encode()

        url = f"{self.whisper_url}/inference"
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                return result.get("text", "").strip()
        except urllib.error.URLError as e:
            logger.error("whisper.cpp request failed: %s", e)
            return ""
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse whisper.cpp response: %s", e)
            return ""
        finally:
            self._cleanup()
