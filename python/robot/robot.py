import logging
import qi
from .eyes import RobotEyes
from .actions import RobotActions
from .audio import RobotAudio
from .tts import RobotTTS

logger = logging.getLogger(__name__)

class Robot:
    """Main robot class that manages connection and delegates to submodules."""

    def __init__(self, ip, port, username, password, remote_wav_path, local_wav_path):
        """Initializes NAO robot configuration parameters.

        Args:
            ip (str): IP address of the robot.
            port (int): Port of the NAOqi service.
            username (str): SSH/SFTP username.
            password (str): SSH/SFTP password.
            remote_wav_path (str): File path where wav audio is recorded on the robot.
            local_wav_path (str): File path where wav audio is downloaded locally.
        """
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.remote_wav_path = remote_wav_path
        self.local_wav_path = local_wav_path
        self.session = None
        self.eyes = None
        self.actions = None
        self.audio = None
        self.tts = None
        self._audio_recorder = None
        self._speech_reco = None
        self._memory = None
        self._tts_service = None

    def connect_to_robot(self):
        """Establishes tcp session connection to robot and registers AL services."""
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
        self.audio = RobotAudio(self._audio_recorder, self._speech_reco, self._memory,
                                self.remote_wav_path, ssh_host=self.ip,
                                ssh_username=self.username, ssh_password=self.password)
        self.tts = RobotTTS(self._tts_service)

        self._speech_reco.setLanguage("Polish")
        try:
            self._speech_reco.unsubscribe("SpeechDetector")
        except Exception:
            pass
        self._speech_reco.pause(True)
        self._speech_reco.setVocabulary(["NAO"], False)
        self._speech_reco.pause(False)

    def _reconnect(self):
        """Reconnects to robot after socket failure."""
        logger.warning("Attempting to reconnect to robot...")
        try:
            if self.session:
                self.session.close()
        except Exception:
            pass
        self.session = None
        self.connect_to_robot()
        logger.info("Reconnected to robot successfully.")

    def set_eyes(self, mode):
        """Shorthand for controlling the robot's eye animation mode."""
        self.eyes.set(mode)

    def speak(self, text):
        """Says provided message with built-in TTS."""
        self.tts.speak(text)

    def execute_action(self, name: str, *args, **kwargs):
        """Executes a named action from the ACTIONS registry. Reconnects on socket failure."""
        try:
            return self.actions.execute(name, *args, **kwargs)
        except RuntimeError as e:
            if "Socket" in str(e) or "not connected" in str(e).lower():
                logger.warning("Socket lost during action '%s', reconnecting...", name)
                self._reconnect()
                return self.actions.execute(name, *args, **kwargs)
            raise

    def disconnect(self):
        """Resets robot state and closes the session."""
        try:
            if self.eyes:
                self.eyes.set(None)
        except Exception as e:
            logger.warning("Error resetting eyes: %s", e)
        try:
            if self.session:
                self.session.close()
        except Exception as e:
            logger.warning("Error closing session: %s", e)
