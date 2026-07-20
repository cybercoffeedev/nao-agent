import logging
import paramiko

logger = logging.getLogger(__name__)

class RobotAudio:
    """Manages robot audio recording, speech recognition and file transfer."""

    def __init__(self, audio_recorder, speech_reco, memory, remote_wav_path,
                 ssh_host, ssh_username, ssh_password):
        """Initializes audio services.

        Args:
            audio_recorder: ALAudioRecorder service.
            speech_reco: ALSpeechRecognition service.
            memory: ALMemory service.
            remote_wav_path: Path to store audio on robot.
            ssh_host: Robot IP for SSH/SFTP connection.
            ssh_username: SSH username.
            ssh_password: SSH password.
        """
        self.audio_recorder = audio_recorder
        self.speech_reco = speech_reco
        self.memory = memory
        self.remote_wav_path = remote_wav_path
        self.ssh_host = ssh_host
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password

    def start_recording(self):
        """Starts recording audio and subscribes to speech detection."""
        try:
            self.audio_recorder.stopMicrophonesRecording()
        except Exception:
            logger.debug("No active recording to stop")
        self.speech_reco.subscribe("SpeechDetector")
        self.audio_recorder.startMicrophonesRecording(self.remote_wav_path, "wav", 48000, [1, 0, 0, 0])

    def stop_recording(self):
        """Stops recording and unsubscribes from speech detection."""
        self.audio_recorder.stopMicrophonesRecording()
        self.speech_reco.unsubscribe("SpeechDetector")

    def is_speech_detected(self) -> bool:
        """Checks if speech is currently detected."""
        return bool(self.memory.getData("SpeechDetected"))

    def download_audio(self, local_path: str):
        """Downloads recorded audio from robot via SFTP.

        Args:
            local_path: Local path to save the downloaded WAV file.
        """
        try:
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(self.ssh_host, port=22,
                            username=self.ssh_username, password=self.ssh_password)
                with ssh.open_sftp() as sftp:
                    sftp.get(self.remote_wav_path, local_path)
        except Exception as e:
            raise RuntimeError(f"SFTP download failed: {e}") from e
