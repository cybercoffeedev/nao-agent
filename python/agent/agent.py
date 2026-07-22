"""Robot agent - orchestrates speech, LLM and robot actions."""

import logging
import time

import paramiko

from .asr import RivaASR
from .llm import LLMManager
from robot import Robot
from .speech_detector import SpeechDetector
from .step_executor import StepExecutor

logger = logging.getLogger(__name__)

SOCKET_ERROR_KEYWORDS: frozenset[str] = frozenset({"socket", "not connected", "timed out"})
SFTP_ERROR_TYPES: tuple[type[Exception], ...] = (
    paramiko.SSHException,
    IOError,
    OSError,
)


def _is_socket_error(error: Exception) -> bool:
    """Check if an error indicates a lost socket/connection."""
    error_str = str(error).lower()
    return any(keyword in error_str for keyword in SOCKET_ERROR_KEYWORDS)


def _is_sftp_error(error: Exception) -> bool:
    """Check if an error is related to SFTP/SSH file transfer."""
    if isinstance(error, SFTP_ERROR_TYPES):
        error_str = str(error).lower()
        return "sftp" in error_str or "ssh" in error_str or "file" in error_str
    return False


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
                except ConnectionError as e:
                    logger.warning("Connection lost, reconnecting to robot... %s", e)
                    self.robot.reconnect()
                except RuntimeError as e:
                    if _is_socket_error(e):
                        logger.warning("Socket lost, reconnecting to robot...")
                        self.robot.reconnect()
                    elif _is_sftp_error(e):
                        logger.warning("SFTP error: %s", e)
                    else:
                        raise
                except SFTP_ERROR_TYPES as e:
                    logger.warning("SFTP/SSH error: %s", e)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.step_executor.shutdown()
            self.robot.disconnect()
