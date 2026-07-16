import sys, qi
from .eyes import RobotEyes
from .actions import RobotActions
from .audio import RobotAudio
from .tts import RobotTTS

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

    def connect_to_robot(self):
        """Establishes tcp session connection to robot and registers AL services."""
        self.session = qi.Session()
        try:
            self.session.connect(f"tcp://{self.ip}:{self.port}")
        except Exception as e:
            print(f"Failed connecting to robot: {e}", file=sys.stderr)
            sys.exit(1)

        posture = self.session.service("ALRobotPosture")
        motion = self.session.service("ALMotion")
        memory = self.session.service("ALMemory")
        battery = self.session.service("ALBattery")
        audio_recorder = self.session.service("ALAudioRecorder")
        speech_reco = self.session.service("ALSpeechRecognition")
        tts = self.session.service("ALTextToSpeech")

        self.eyes = RobotEyes(self.session)
        self.background_movement = self.session.service("ALBackgroundMovement")
        self.listening_movement = self.session.service("ALListeningMovement")
        self.basic_awareness = self.session.service("ALBasicAwareness")
        self.actions = RobotActions(posture, motion, memory, battery, self.background_movement, self.listening_movement, self.basic_awareness)
        self.audio = RobotAudio(audio_recorder, speech_reco, memory, self.remote_wav_path)
        self.tts = RobotTTS(tts)

        speech_reco.setLanguage("Polish")
        speech_reco.pause(True)
        speech_reco.setVocabulary(["NAO"], False)
        speech_reco.pause(False)

    def set_eyes(self, mode):
        """Shorthand for controlling the robot's eye animation mode."""
        self.eyes.set(mode)

    def speak(self, text):
        """Says provided message with built-in TTS."""
        self.tts.speak(text)

    def execute_action(self, name: str, *args):
        """Executes a named action from the ACTIONS registry."""
        return self.actions.execute(name, *args)
