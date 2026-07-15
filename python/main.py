import os, sys
from dotenv import load_dotenv
from robot import Robot
from agent import RobotAgent
from asr import RivaASR
from llm import LLMManager

def load_system_prompt():
    """Reads the system prompt/instruction from data/system_msg.txt.
    
    Returns:
        str: The system message content, or an empty string if the file is not found.
    """
    try:
        return open("data/system_msg.txt").read()
    except FileNotFoundError:
        print("data/system_msg.txt not found", file=sys.stderr)
        return ""

def main():
    """Main entry point of the application. Loads configuration from .env,
    initializes the robot connection, speech recognizer, LLM context, and starts
    the chatbot agent.
    """
    load_dotenv()

    robot = Robot(
        ip=os.environ["ROBOT_IP"],
        port=int(os.getenv("ROBOT_PORT", 9559)),
        username=os.getenv("ROBOT_USERNAME", "nao"),
        password=os.getenv("ROBOT_PASSWORD", "nao"),
        remote_wav_path="/home/nao/capture.wav",
        local_wav_path="./capture.wav"
    )
    asr = RivaASR(
        api_key=os.environ["NVIDIA_API_KEY"],
        function_id=os.environ["ASR_FUNCTION_ID"],
        local_wav_path="./capture.wav",
    )
    llm = LLMManager(
        api_key=os.environ["NVIDIA_API_KEY"],
        url=os.environ["OPENAI_BASE_URL"],
        model=os.environ["MODEL"],
        system_msg=load_system_prompt(),
    )

    RobotAgent(robot, asr, llm).run()

if __name__ == "__main__":
    main()
