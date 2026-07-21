"""Speech recognition using NVIDIA Riva ASR gRPC service."""

import logging
import os
import wave

import riva.client

logger = logging.getLogger(__name__)


class RivaASR:
    """Speech recognition using NVIDIA Riva ASR gRPC service."""

    def __init__(self, api_key: str, function_id: str, local_wav_path: str) -> None:
        """Initialize the NVIDIA Riva ASR client configuration.

        Args:
            api_key: The NVIDIA API key used for authentication.
            function_id: NVIDIA Riva function ID used for the ASR service.
            local_wav_path: Local path where the wav audio file will be saved.
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if not function_id:
            raise ValueError("function_id cannot be empty")

        self.local_wav_path = local_wav_path
        self.auth = riva.client.Auth(
            uri="grpc.nvcf.nvidia.com:443",
            use_ssl=True,
            metadata_args=[
                ["authorization", f"Bearer {api_key}"],
                ["function-id", function_id],
            ],
        )

    def _cleanup(self) -> None:
        """Safely remove the local WAV file if it exists."""
        try:
            if os.path.exists(self.local_wav_path):
                os.remove(self.local_wav_path)
        except OSError as e:
            logger.warning("Could not remove WAV file: %s", e)

    def transcribe_audio(self) -> str:
        """Send the audio file to Riva ASR and return the recognized text."""
        try:
            with wave.open(self.local_wav_path, "rb") as wav:
                sample_rate: int = wav.getframerate()
                channels: int = wav.getnchannels()
                audio_data: bytes = wav.readframes(wav.getnframes())
        except Exception as e:
            logger.error("Error reading WAV file: %s", e)
            self._cleanup()
            return ""

        config = riva.client.RecognitionConfig(
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
            sample_rate_hertz=sample_rate,
            language_code="pl-PL",
            max_alternatives=1,
            audio_channel_count=channels,
            enable_automatic_punctuation=True,
        )

        try:
            response = riva.client.ASRService(self.auth).offline_recognize(audio_data, config)
            return "".join(r.alternatives[0].transcript for r in response.results)
        except Exception as e:
            logger.error("Riva ASR error: %s", e)
            return ""
        finally:
            self._cleanup()
