import sys, qi

class RobotEyes:
    def __init__(self, session: qi.Session):
        """Initializes the visual eye indicators on the robot using ALLeds service.

        Args:
            session (qi.Session): Active session connected to the NAO robot.
        """
        self.leds = session.service("ALLeds")
        self.eye_leds = [
            "FaceLed0",
            "FaceLed1",
            "FaceLed2",
            "FaceLed3",
            "FaceLed4",
            "FaceLed5",
            "FaceLed6",
            "FaceLed7"
        ]
        self.task = qi.PeriodicTask()
        self.task.setCallback(self._animation_step)
        self.task.setUsPeriod(100000)
        self.mode = None
        self.step = 0

    def _animation_step(self):
        """Callback step executed periodically by qi.PeriodicTask to update LEDs
        according to the current animation mode.
        """
        match self.mode:
            case "listening":
                self.leds.fadeRGB("FaceLeds", 0x0000FFFF, 0.0)
            case "thinking":
                self.leds.setIntensity("FaceLeds", 0.0)

                main_led = self.eye_leds[self.step % 8]
                fade_led_1 = self.eye_leds[(self.step - 1) % 8]
                fade_led_2 = self.eye_leds[(self.step - 1) % 8]

                self.leds.setIntensity(main_led.strip(), 1.0)
                self.leds.setIntensity(fade_led_1.strip(), 0.7)
                self.leds.setIntensity(fade_led_2.strip(), 0.5)

                self.step += 1

    def set_animation_mode(self, mode: str | None):
        """Changes the current eye animation mode.

        Args:
            mode (str | None): Target animation mode ("listening", "thinking") or None to deactivate.
        """
        self.task.stop()
        self.mode = mode
        
        match mode:
            case "listening":
                self.task.start(True)
            case "thinking":
                self.step = 0
                self.task.start(True)
            case None:
                self.leds.setIntensity("FaceLeds", 1.0)

class Robot:
    def __init__(self, ip: str, port: int, username: str, password: str, remote_wav_path: str, local_wav_path: str):
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
        self.leds = None
        self.eyes = None

    def connect_to_robot(self):
        """Establishes tcp session connection to robot, registers AL services,
        and pauses speech recognition to initialize vocabulary.
        """
        self.session = qi.Session()
        try:
            self.session.connect(f"tcp://{self.ip}:{self.port}")
            print("Connected to robot.")
        except Exception as e:
            print(f"Failed connecting to robot: {e}", file=sys.stderr)
            sys.exit(1)

        self.audio_recorder = self.session.service("ALAudioRecorder")
        self.tts = self.session.service("ALTextToSpeech")
        self.memory = self.session.service("ALMemory")
        self.speech_reco = self.session.service("ALSpeechRecognition")
        self.leds = self.session.service("ALLeds")
        self.eyes = RobotEyes(self.session)

        self.speech_reco.setLanguage("Polish")
        
        while True:
            try:
                self.speech_reco.pause(True)
                self.speech_reco.setVocabulary(["NAO"], False)  # Needed for reco to work
                self.speech_reco.pause(False)
            except: 
                continue
            finally: 
                break

    def start_audio_recording(self):
        """Starts recording audio through the robot's microphones and subscribes
        to the speech detection module.
        """
        channels = [1, 0, 0, 0]
        try:
            self.audio_recorder.stopMicrophonesRecording()
        except Exception:
            pass
        self.speech_reco.subscribe("SpeechDetector")
        self.audio_recorder.startMicrophonesRecording(self.remote_wav_path, "wav", 48000, channels)

    def stop_audio_recording(self):
        """Stops microphone audio recording and unsubscribes from the speech detector module.
        """
        self.audio_recorder.stopMicrophonesRecording()
        self.speech_reco.unsubscribe("SpeechDetector")

    def speak(self, text: str):
        """Says provided message with built-in TTS.

        Args:
            text (str): The text message to speak.
        """
        self.tts.setLanguage("Polish")
        try:
            self.tts.say(text)
        except Exception as e:
            print(f"Couldn't say the message: {e}", file=sys.stderr)
