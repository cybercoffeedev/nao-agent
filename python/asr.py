import os, wave
import logging
import riva.client

logger = logging.getLogger(__name__)

class RivaASR:
    """Speech recognition using NVIDIA Riva ASR gRPC service."""
    def __init__(self, api_key: str, function_id: str, local_wav_path: str):
        """Initializes the NVIDIA Riva ASR client configuration.

        Args:
            api_key (str): The NVIDIA API key used for authentication.
            function_id (str): NVIDIA Riva function ID used for the ASR service.
            local_wav_path (str): Local path where the wav audio file will be saved.
        """
        self.local_wav_path = local_wav_path
        self.auth = riva.client.Auth(
            uri="grpc.nvcf.nvidia.com:443",
            use_ssl=True,
            metadata_args=[
                ["authorization", f"Bearer {api_key}"],
                ["function-id", function_id]
            ]
        )

    def transcribe_audio(self):
        """Sends the audio file to Riva ASR and returns the recognized text."""
        try:
            with wave.open(self.local_wav_path, 'rb') as wav:
                sample_rate = wav.getframerate()
                channels = wav.getnchannels()
                audio_data = wav.readframes(wav.getnframes())
        except Exception as e:
            logger.error("Error reading WAV file: %s", e)
            return None

        config = riva.client.RecognitionConfig(
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
            sample_rate_hertz=sample_rate,
            language_code="pl-PL",
            max_alternatives=1,
            audio_channel_count=channels,
            enable_automatic_punctuation=True
        )

        try:
            response = riva.client.ASRService(self.auth).offline_recognize(audio_data, config)
            return "".join(r.alternatives[0].transcript for r in response.results)
        except Exception as e:
            logger.error("Riva ASR error: %s", e)
        finally:
            os.remove(self.local_wav_path)
