"""Robot agent - orchestrates speech, LLM and robot actions."""

import logging
import time

from asr import RivaASR
from llm import LLMManager
from robot import Robot
from speech_detector import SpeechDetector
from step_executor import StepExecutor

logger = logging.getLogger(__name__)


class RobotAgent:
    """Orchestrates speech recognition, LLM and robot actions."""

    def __init__(self, robot: Robot, asr: RivaASR, llm: LLMManager) -> None:
        """Initialize the robot agent.

        Args:
            robot: Robot instance for controlling the NAO robot.
            asr: Speech recognition service.
            llm: Language model manager.
        """
        if robot is None:
            raise ValueError("robot cannot be None")
        if asr is None:
            raise ValueError("asr cannot be None")
        if llm is None:
            raise ValueError("llm cannot be None")

        self.robot = robot
        self.asr = asr
        self.llm = llm
        self.speech_detector = SpeechDetector(robot)
        self.step_executor = StepExecutor(robot, llm)

    def run(self) -> None:
        """Main loop - listen, transcribe, generate, execute."""
        self.robot.connect()

        try:
            while True:
                try:
                    self.speech_detector.listen()
                    self.robot.download_audio()
                    self.robot.set_eyes("thinking")

                    text = self.asr.transcribe_audio()
                    if text:
                        logger.info("User: %s", text)
                        self.llm.add_user_message(text)
                        response = self.llm.generate_response()
                        logger.info("LLM: %s", response[:200] if response else "")
                        self.step_executor.execute(response)
                    time.sleep(1.0)
                except RuntimeError as e:
                    if "Socket" in str(e) or "not connected" in str(e).lower():
                        logger.warning("Socket lost, reconnecting to robot...")
                        self.robot.reconnect()
                    else:
                        raise
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.robot.disconnect()
