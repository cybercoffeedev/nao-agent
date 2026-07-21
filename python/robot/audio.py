"""Manages robot audio recording, speech recognition and file transfer."""

import logging
from typing import Any

import paramiko

logger = logging.getLogger(__name__)


class RobotAudio:
    """Manages robot audio recording, speech recognition and file transfer."""

    def __init__(
        self,
        audio_recorder: Any,
        speech_reco: Any,
        memory: Any,
        remote_wav_path: str,
        ssh_host: str,
        ssh_username: str,
        ssh_password: str,
        ssh_port: int = 22,
    ) -> None:
        """Initialize audio services.

        Args:
            audio_recorder: ALAudioRecorder service.
            speech_reco: ALSpeechRecognition service.
            memory: ALMemory service.
            remote_wav_path: Path to store audio on robot.
            ssh_host: Robot IP for SSH/SFTP connection.
            ssh_username: SSH username.
            ssh_password: SSH password.
            ssh_port: SSH port for file transfer.
        """
        if not ssh_host:
            raise ValueError("ssh_host cannot be empty")

        self.audio_recorder = audio_recorder
        self.speech_reco = speech_reco
        self.memory = memory
        self.remote_wav_path = remote_wav_path
        self.ssh_host = ssh_host
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.ssh_port = ssh_port

    def start_recording(self) -> None:
        """Start recording audio and subscribe to speech detection."""
        try:
            self.audio_recorder.stopMicrophonesRecording()
        except Exception:
            logger.debug("No active recording to stop")
        try:
            self.speech_reco.subscribe("SpeechDetector")
        except Exception as e:
            logger.warning("Failed to subscribe to speech detection: %s", e)
        self.audio_recorder.startMicrophonesRecording(
            self.remote_wav_path, "wav", 48000, [1, 0, 0, 0]
        )

    def stop_recording(self) -> None:
        """Stop recording and unsubscribe from speech detection."""
        try:
            self.audio_recorder.stopMicrophonesRecording()
        except Exception as e:
            logger.debug("Error stopping recording: %s", e)
        try:
            self.speech_reco.unsubscribe("SpeechDetector")
        except Exception as e:
            logger.debug("Error unsubscribing from speech: %s", e)

    def is_speech_detected(self) -> bool:
        """Check if speech is currently detected."""
        return bool(self.memory.getData("SpeechDetected"))

    def download_audio(self, local_path: str) -> None:
        """Download recorded audio from robot via SFTP.

        Args:
            local_path: Local path to save the downloaded WAV file.

        Raises:
            RuntimeError: If SFTP download fails.
        """
        try:
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    self.ssh_host,
                    port=self.ssh_port,
                    username=self.ssh_username,
                    password=self.ssh_password,
                )
                with ssh.open_sftp() as sftp:
                    sftp.get(self.remote_wav_path, local_path)
        except Exception as e:
            raise RuntimeError(f"SFTP download failed: {e}") from e
