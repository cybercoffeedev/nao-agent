"""Speech detection - listens for voice and records audio."""

import logging
import time

from robot import Robot

logger = logging.getLogger(__name__)

SILENCE_THRESHOLD: float = 1.5
SPEECH_CHECK_INTERVAL: float = 0.1
MAX_LISTEN_DURATION: float = 30.0


class SpeechDetector:
    """Detects speech and records audio from the robot's microphone."""

    def __init__(self, robot: Robot) -> None:
        """Initialize speech detector.

        Args:
            robot: Robot instance with audio services.
        """
        if robot is None:
            raise ValueError("robot cannot be None")
        self.robot = robot

    def listen(self) -> None:
        """Listen for speech and stop after silence threshold.

        Records audio while speech is detected. Stops when silence
        exceeds SILENCE_THRESHOLD seconds after speech started.
        Times out after MAX_LISTEN_DURATION seconds.
        """
        speech_started = False
        silence_start: float | None = None
        start_time = time.time()

        self.robot.start_recording()
        while True:
            elapsed = time.time() - start_time
            if elapsed >= MAX_LISTEN_DURATION:
                logger.warning("Listen timeout after %.1fs", MAX_LISTEN_DURATION)
                self.robot.set_eyes(None)
                break

            speaking: bool = self.robot.is_speech_detected()
            if speaking:
                if not speech_started:
                    self.robot.set_eyes("listening")
                    speech_started = True
                silence_start = None
            elif speech_started:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= SILENCE_THRESHOLD:
                    self.robot.set_eyes(None)
                    break
            time.sleep(SPEECH_CHECK_INTERVAL)
        self.robot.stop_recording()
