"""Main entry point for the NAO robot agent."""

import logging
from pathlib import Path

from dotenv import load_dotenv

from agent import RobotAgent, LLMManager, RivaASR
from agent.llm import build_system_prompt
from config import Config
from robot import Robot
from robot.actions import get_action_descriptions

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "data" / "system_msg.txt"


def load_user_prompt() -> str:
    """Read user-defined system prompt from data/system_msg.txt."""
    try:
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("data/system_msg.txt not found")
        return ""


def main() -> None:
    """Main entry point of the application."""
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    load_dotenv()

    config = Config.from_env()

    robot = Robot(
        ip=config.robot_ip,
        port=config.robot_port,
        username=config.robot_username,
        password=config.robot_password,
        remote_wav_path=config.remote_wav_path,
        local_wav_path=config.local_wav_path,
        ssh_port=config.ssh_port,
    )
    asr = RivaASR(
        api_key=config.nvidia_api_key,
        function_id=config.asr_function_id,
        local_wav_path=config.local_wav_path,
    )
    llm = LLMManager(
        api_key=config.nvidia_api_key,
        url=config.openai_base_url,
        model=config.model,
        system_msg=build_system_prompt(
            actions=get_action_descriptions(),
            user_prompt=load_user_prompt(),
        ),
    )

    RobotAgent(robot, asr, llm).run()


if __name__ == "__main__":
    main()
