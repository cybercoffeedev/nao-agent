import logging
from dotenv import load_dotenv
from config import Config
from robot import Robot
from agent import RobotAgent
from asr import RivaASR
from llm import LLMManager

logger = logging.getLogger(__name__)

def load_system_prompt():
    """Reads the system prompt/instruction from data/system_msg.txt."""
    try:
        with open("data/system_msg.txt") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("data/system_msg.txt not found")
        return ""

def main():
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
        system_msg=load_system_prompt(),
    )

    RobotAgent(robot, asr, llm).run()

if __name__ == "__main__":
    main()
