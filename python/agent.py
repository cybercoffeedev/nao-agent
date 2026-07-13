import sys, time, paramiko
from robot import Robot
from asr import RivaASR
from llm import LLMManager

class RobotAgent:
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
        silence_start_time = None
        silence_duration = 1.5

        self.robot.start_audio_recording()
        while True:
            is_speaking = self.robot.memory.getData("SpeechDetected")
            if is_speaking:
                if not speech_started:
                    print("Robot is listening")
                    if self.robot.eyes:
                        self.robot.eyes.set_animation_mode("listening")
                    speech_started = True
                silence_start_time = None
            else:
                if speech_started:
                    if silence_start_time is None:
                        silence_start_time = time.time()
                    elif time.time() - silence_start_time >= silence_duration:
                        print("Robot stopped listening")
                        if self.robot.eyes:
                            self.robot.eyes.set_animation_mode(None)
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
        """Starts the interactive chatbot main loop, connecting to the robot,
        listening to speech, transcribing, requesting replies, and vocalizing responses.
        """
        self.robot.connect_to_robot()
        print("Chatbot agent is running...")
        while True:
            self.listen_for_speech()
            self.download_audio_from_robot()
            
            if self.robot.eyes:
                self.robot.eyes.set_animation_mode("thinking")
                
            recognized_text = self.asr.transcribe_audio()
            
            if recognized_text is not None:
                self.llm.add_user_message(recognized_text)
                msg = self.llm.generate_response()
                if self.robot.eyes:
                    self.robot.eyes.set_animation_mode(None)
                self.robot.speak(msg)
            else:
                if self.robot.eyes:
                    self.robot.eyes.set_animation_mode(None)
            time.sleep(1.0)
