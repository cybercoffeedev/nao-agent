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
    system_msg = ""
    system_msg_path = "data/system_msg.txt"
    try:
        with open(system_msg_path, 'r') as file:
            system_msg += file.read()
        return system_msg
    except FileNotFoundError:
        print("data/system_msg.txt not found", file=sys.stderr)
        return ""

def main():
    """Main entry point of the application. Loads configuration from .env,
    initializes the robot connection, speech recognizer, LLM context, and starts
    the chatbot agent.
    """
    # Load .env
    load_dotenv()

    ROBOT_IP = os.environ.get("ROBOT_IP")
    ROBOT_PORT = int(os.environ.get("ROBOT_PORT", 9559))
    ROBOT_USER = os.environ.get("ROBOT_USERNAME", "nao")
    ROBOT_PASS = os.environ.get("ROBOT_PASSWORD", "nao")
    NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
    MODEL = os.environ.get("MODEL")
    ASR_FUNCTION_ID = os.environ.get("ASR_FUNCTION_ID")

    WAV_FILENAME = "capture.wav"
    REMOTE_WAV_PATH = f"/home/nao/{WAV_FILENAME}"
    LOCAL_WAV_PATH = f"./{WAV_FILENAME}"

    system_msg = load_system_prompt()
    
    robot = Robot(
        ip=ROBOT_IP,
        port=ROBOT_PORT,
        username=ROBOT_USER,
        password=ROBOT_PASS,
        remote_wav_path=REMOTE_WAV_PATH,
        local_wav_path=LOCAL_WAV_PATH
    )
    asr = RivaASR(
        api_key=NVIDIA_API_KEY,
        function_id=ASR_FUNCTION_ID,
        local_wav_path=LOCAL_WAV_PATH,
    )
    llm = LLMManager(
        api_key=NVIDIA_API_KEY,
        url=OPENAI_BASE_URL,
        model=MODEL,
        system_msg=system_msg
    )

    agent = RobotAgent(robot=robot, asr=asr, llm=llm)
    agent.run()


if __name__ == "__main__":
    main()