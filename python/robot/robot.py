"""Main robot class that manages connection and delegates to submodules."""

import logging
import threading
from typing import Any

import qi

from .actions import RobotActions
from .audio import RobotAudio
from .eyes import RobotEyes

logger = logging.getLogger(__name__)

RECONNECT_ERROR_KEYWORDS: frozenset[str] = frozenset({"Socket", "not connected"})


class Robot:
    """Main robot class that manages connection and delegates to submodules."""

    def __init__(
        self,
        ip: str,
        port: int,
        username: str,
        password: str,
        local_wav_path: str,
        remote_wav_path: str = "/home/nao/capture.wav",
        ssh_port: int = 22,
    ) -> None:
        """Initialize NAO robot configuration parameters.

        Args:
            ip: IP address of the robot.
            port: Port of the NAOqi service.
            username: SSH/SFTP username.
            password: SSH/SFTP password.
            local_wav_path: File path where wav audio is downloaded locally.
            remote_wav_path: File path where wav audio is recorded on the robot.
            ssh_port: SSH port for file transfer.
        """
        if not ip:
            raise ValueError("ip cannot be empty")

        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.local_wav_path = local_wav_path
        self.remote_wav_path = remote_wav_path
        self.ssh_port = ssh_port
        self.session: qi.Session | None = None
        self.eyes: RobotEyes | None = None
        self.actions: RobotActions | None = None
        self._audio: RobotAudio | None = None
        self._audio_recorder: Any = None
        self._speech_reco: Any = None
        self._memory: Any = None
        self._tts_service: Any = None
        self._reconnect_lock = threading.Lock()

    def connect(self) -> None:
        """Establish tcp session connection to robot and register AL services."""
        self.session = qi.Session()
        try:
            self.session.connect(f"tcp://{self.ip}:{self.port}")
        except Exception as e:
            raise ConnectionError(f"Failed connecting to robot: {e}") from e

        self._memory = self.session.service("ALMemory")
        self._audio_recorder = self.session.service("ALAudioRecorder")
        self._speech_reco = self.session.service("ALSpeechRecognition")
        self._tts_service = self.session.service("ALTextToSpeech")

        self.eyes = RobotEyes(self.session)
        self.actions = RobotActions(self.session)
        self._audio = RobotAudio(
            self._audio_recorder,
            self._speech_reco,
            self._memory,
            self.remote_wav_path,
            ssh_host=self.ip,
            ssh_username=self.username,
            ssh_password=self.password,
            ssh_port=self.ssh_port,
        )
        self._speech_reco.setLanguage("Polish")
        try:
            self._speech_reco.unsubscribe("SpeechDetector")
        except RuntimeError:
            pass
        self._speech_reco.pause(True)
        self._speech_reco.setVocabulary(["NAO"], False)
        self._speech_reco.pause(False)

    def reconnect(self) -> None:
        """Reconnect to robot after socket failure."""
        with self._reconnect_lock:
            logger.warning("Attempting to reconnect to robot...")
            try:
                if self.session:
                    self.session.close()
            except RuntimeError:
                pass
            self.session = None
            self.connect()
            logger.info("Reconnected to robot successfully.")

    def _delegate(self, name: str, component: Any, method: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a method on a component if connected, otherwise log a warning."""
        if component is None:
            logger.warning("Cannot %s - robot not connected", name)
            return False
        return getattr(component, method)(*args, **kwargs)

    def set_eyes(self, mode: str | None) -> None:
        """Shorthand for controlling the robot's eye animation mode."""
        self._delegate("set eyes", self.eyes, "set", mode)

    def speak(self, text: str) -> None:
        """Say provided message with built-in TTS."""
        if self._tts_service is None:
            logger.warning("Cannot speak - robot not connected")
            return
        try:
            self._tts_service.say(text)
        except RuntimeError as e:
            logger.error("Couldn't say the message: %s", e)

    def execute_action(self, name: str, *args: Any, **kwargs: Any) -> str:
        """Execute a named action from the ACTIONS registry.

        Args:
            name: Name of the action to execute.
            *args: Positional arguments for the action.
            **kwargs: Keyword arguments for the action.

        Returns:
            Action result string.
        """
        if self.actions is None:
            return "Robot not connected"
        try:
            return self.actions.execute(name, *args, **kwargs)
        except RuntimeError as e:
            if self.is_socket_error(e):
                logger.warning("Socket lost during action '%s', reconnecting...", name)
                self.reconnect()
                return self.actions.execute(name, *args, **kwargs)
            raise

    def _audio_op(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Execute an audio method if connected, otherwise log a warning."""
        return self._delegate(method, self._audio, method, *args, **kwargs)

    def download_audio(self) -> None:
        """Download recorded audio from robot via SFTP."""
        self._audio_op("download_audio", self.local_wav_path)

    def start_recording(self) -> None:
        """Start recording audio from robot's microphone."""
        self._audio_op("start_recording")

    def stop_recording(self) -> None:
        """Stop recording audio."""
        self._audio_op("stop_recording")

    def is_speech_detected(self) -> bool:
        """Check if speech is currently detected."""
        return self._audio_op("is_speech_detected")

    @staticmethod
    def is_socket_error(error: Exception) -> bool:
        """Check if an error is a socket/connection error."""
        error_str = str(error).lower()
        return any(keyword.lower() in error_str for keyword in RECONNECT_ERROR_KEYWORDS)

    def disconnect(self) -> None:
        """Reset robot state and close the session."""
        try:
            if self.eyes:
                self.eyes.set(None)
        except Exception as e:
            logger.warning("Error resetting eyes: %s", e)
        try:
            if self._audio:
                self._audio.close()
        except Exception as e:
            logger.warning("Error closing SSH connection: %s", e)
        try:
            if self.session:
                self.session.close()
        except Exception as e:
            logger.warning("Error closing session: %s", e)
