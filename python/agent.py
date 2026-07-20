import time, json
import logging
import paramiko
from robot import Robot
from asr import RivaASR
from llm import LLMManager

logger = logging.getLogger(__name__)

class RobotAgent:
    """Central orchestrator for the voice-based chatbot loop."""
    def __init__(self, robot: Robot, asr: RivaASR, llm: LLMManager):
        self.robot = robot
        self.asr = asr
        self.llm = llm

    def listen_for_speech(self, timeout=30):
        """Monitors speech detection, activates eye animations,
        and records audio until silence threshold is reached.
        """
        speech_started = False
        silence_start = None
        start = time.time()

        self.robot.audio.start_recording()
        while True:
            if time.time() - start >= timeout:
                logger.warning("Speech detection timed out")
                self.robot.set_eyes(None)
                break
            speaking = self.robot.audio.is_speech_detected()
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
        self.robot.audio.stop_recording()

    def download_audio_from_robot(self):
        """Download the audio file from the robot via SFTP."""
        try:
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(self.robot.ip, port=22, username=self.robot.username, password=self.robot.password)
                with ssh.open_sftp() as sftp:
                    sftp.get(self.robot.remote_wav_path, self.robot.local_wav_path)
        except Exception as e:
            raise RuntimeError(f"SFTP download failed: {e}") from e

    def _process_response(self, tools):
        """Process LLM response, executing tool calls and speaking results.

        Keeps looping as long as the model returns tool calls, executing
        each tool and feeding results back. Stops when the model returns
        a text response or max iterations is reached.
        """
        try:
            response = self.llm.generate_response(tools)
        except Exception as e:
            logger.error("LLM request failed: %s", e)
            self.robot.set_eyes(None)
            return

        for _ in range(5):
            tool_calls = response.tool_calls

            if not tool_calls:
                self.robot.set_eyes(None)
                if response.content:
                    self.robot.speak(response.content)
                return

            for tc in tool_calls:
                args = json.loads(tc.function.arguments)
                logger.info("Executing tool: %s(%s)", tc.function.name, args)
                result = self.robot.execute_action(tc.function.name, **args)
                self.llm.add_tool_result(tc.id, str(result))

            self.robot.set_eyes("thinking")
            try:
                response = self.llm.generate_response(tools)
            except Exception as e:
                logger.error("LLM request failed: %s", e)
                self.robot.set_eyes(None)
                return
        else:
            logger.warning("Max tool call iterations reached")
            self.robot.set_eyes(None)

    def run(self):
        """Starts the interactive chatbot main loop."""
        self.robot.connect_to_robot()
        tools = self.robot.actions.get_tool_schemas()

        try:
            while True:
                self.listen_for_speech(timeout=30)
                self.download_audio_from_robot()
                self.robot.set_eyes("thinking")

                text = self.asr.transcribe_audio()
                if text:
                    self.llm.add_message("user", text)
                    self._process_response(tools)
                time.sleep(1.0)
        except KeyboardInterrupt:
            pass
