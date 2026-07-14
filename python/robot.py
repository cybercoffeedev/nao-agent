import sys, qi

class RobotEyes:
    """Manages the NAO robot's face LED animations using ALLeds service."""
    def __init__(self, session: qi.Session):
        """Initializes the visual eye indicators on the robot.

        Args:
            session (qi.Session): Active session connected to the NAO robot.
        """
        session.service("ALAutonomousBlinking").setEnabled(False) # Disable autonomous blinking
        self.leds = session.service("ALLeds")
        self.leds_list = [f"FaceLed{i}" for i in range(8)]
        self.task = qi.PeriodicTask()
        self.task.setCallback(self._tick)
        self.task.setUsPeriod(100000)
        self.mode = None
        self.step = 0

    def _tick(self):
        """Callback step executed periodically by qi.PeriodicTask to update LEDs
        according to the current animation mode.
        """
        if self.mode == "listening":
            self.leds.fadeRGB("FaceLeds", 0x0000FFFF, 0.0)
        elif self.mode == "thinking":
            for i, intensity in enumerate((1.0, 0.6, 0.2, 0.0)):    # LED brightness levels for the rotating "thinking" eye animation
                self.leds.setIntensity(self.leds_list[(self.step - i) % 8], intensity)
            self.step += 1

    def set(self, mode: str | None):
        """Changes the current eye animation mode.

        Args:
            mode (str | None): Target animation mode ("listening", "thinking") or None to deactivate.
        """
        self.task.stop()
        self.mode = mode
        if mode:
            self.step = 0
            self.task.start(True)
        else:
            self.leds.setIntensity("FaceLeds", 1.0)

class Robot:
    """Manages connection and communication with a NAO robot."""
    ACTIONS = {
        "wave_right_hand": {
            "method": "wave_right_hand",
            "description": "Wave your right hand in greeting. Use this when someone greets the robot or waves at it.",
        },
    }

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
        self.audio_recorder = None
        self.tts = None
        self.memory = None
        self.speech_reco = None
        self.eyes = None
        self.motion = None

    def connect_to_robot(self):
        """Establishes tcp session connection to robot and registers AL services."""
        self.session = qi.Session()
        try:
            self.session.connect(f"tcp://{self.ip}:{self.port}")
        except Exception as e:
            print(f"Failed connecting to robot: {e}", file=sys.stderr)
            sys.exit(1)

        self.audio_recorder = self.session.service("ALAudioRecorder")
        self.tts = self.session.service("ALTextToSpeech")
        self.memory = self.session.service("ALMemory")
        self.speech_reco = self.session.service("ALSpeechRecognition")
        self.motion = self.session.service("ALMotion")
        self.eyes = RobotEyes(self.session)

        self.speech_reco.setLanguage("Polish")
        self.speech_reco.pause(True)
        self.speech_reco.setVocabulary(["NAO"], False)
        self.speech_reco.pause(False)

    def wave_right_hand(self):
        """Performs a waving animation with the robot's right arm."""
        is_absolute = True
        names = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RWristYaw"]
        time_lists = [[1.5, 1.75, 2, 2.35, 2.75, 3, 4.5] for _ in range(4)]
        angle_lists = [
            [  -1,   -1,   -1,   -1,   -1,   -1,  1.5], # RShoulderPitch
            [-0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.3], # RShoulderRoll
            [ 1.3,  0.2,  1.2,  0.2,  1.2,  0.2,  0.5], # RElblowRoll
            [ 0.5, -0.5,  0.5, -0.5,  0.5, -0.5,  0.0]  # RWristYaw
        ]
        self.motion.angleInterpolation(names, angle_lists, time_lists, is_absolute)

    def start_audio_recording(self):
        """Starts recording audio through the robot's microphones and subscribes
        to the speech detection module.
        """
        try:
            self.audio_recorder.stopMicrophonesRecording()
        except Exception:
            pass
        self.speech_reco.subscribe("SpeechDetector")
        self.audio_recorder.startMicrophonesRecording(self.remote_wav_path, "wav", 48000, [1, 0, 0, 0])

    def stop_audio_recording(self):
        """Stops microphone audio recording and unsubscribes from the speech detector module.
        """
        self.audio_recorder.stopMicrophonesRecording()
        self.speech_reco.unsubscribe("SpeechDetector")

    def set_eyes(self, mode):
        """Shorthand for controlling the robot's eye animation mode.

        Args:
            mode (str | None): Target animation mode or None to reset.
        """
        self.eyes.set(mode)

    def speak(self, text):
        """Says provided message with built-in TTS.

        Args:
            text (str): The text message to speak.
        """
        self.tts.setLanguage("Polish")
        try:
            self.tts.say(text)
        except Exception as e:
            print(f"Couldn't say the message: {e}", file=sys.stderr)

    def execute_action(self, name: str):
        """Executes a named action from the ACTIONS registry.

        Args:
            name (str): Action key from Robot.ACTIONS.
        """
        if name in self.ACTIONS:
            getattr(self, self.ACTIONS[name]["method"])()
        else:
            print(f"Unknown action: {name}", file=sys.stderr)
