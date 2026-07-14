import sys, time, paramiko
from robot import Robot
from asr import RivaASR
from llm import LLMManager

class RobotAgent:
    """Central orchestrator for the voice-based chatbot loop."""
    def __init__(self, robot: Robot, asr: RivaASR, llm: LLMManager):
        """Initializes the chatbot agent.

        Args:
            robot (Robot): NAO robot controller instance.
            asr (RivaASR): Speech recognition module instance.
            llm (LLMManager): Language model manager instance.
        """
        self.robot = robot
        self.asr = asr
        self.llm = llm

    def listen_for_speech(self):
        """Monitors the robot's memory for speech detection, activates eye animations,
        and records audio until silence threshold is reached.
        """
        speech_started = False
        silence_start = None

        self.robot.start_audio_recording()
        while True:
            speaking = self.robot.memory.getData("SpeechDetected")
            if speaking:
                if not speech_started:
                    self.robot.set_eyes("listening")
                    speech_started = True
                silence_start = None
            elif speech_started:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= 1.5:
                    self.robot.set_eyes(None)
                    break
            time.sleep(0.1)
        self.robot.stop_audio_recording()

    def download_audio_from_robot(self):
        """Download the audio file from the robot via SFTP."""
        try:
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(self.robot.ip, port=22, username=self.robot.username, password=self.robot.password)
                with ssh.open_sftp() as sftp:
                    sftp.get(self.robot.remote_wav_path, self.robot.local_wav_path)
        except Exception as e:
            print(f"Error downloading file via SFTP: {e}", file=sys.stderr)
            sys.exit(1)

    def run(self):
        """Starts the interactive chatbot main loop."""
        self.robot.connect_to_robot()

        try:
            while True:
                self.listen_for_speech()
                self.download_audio_from_robot()
                self.robot.set_eyes("thinking")

                text = self.asr.transcribe_audio()
                if text:
                    self.llm.add_user_message(text)
                    text, actions = self.llm.generate_response()
                    self.robot.set_eyes(None)
                    self.robot.speak(text)
                    for action in actions:
                        self.robot.execute_action(action)

                self.robot.set_eyes(None)
                time.sleep(1.0)
        except KeyboardInterrupt:
            pass
