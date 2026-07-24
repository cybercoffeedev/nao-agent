"""Manages robot audio recording, speech recognition and file transfer."""

import json
import logging
import threading
from pathlib import Path
from typing import Any

import paramiko

logger = logging.getLogger(__name__)

KNOWN_HOSTS_PATH = Path(__file__).parent.parent.parent / "data" / "known_hosts.json"


class _SavedHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """Accepts unknown hosts on first connection, verifies on subsequent ones.

    Stores accepted host keys in a JSON file so that future connections
    can verify the host identity and detect potential MITM attacks.
    """

    def __init__(self, hosts_path: Path = KNOWN_HOSTS_PATH) -> None:
        self._hosts_path = hosts_path
        self._keys: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load known hosts from disk."""
        try:
            if self._hosts_path.exists():
                self._keys = json.loads(self._hosts_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load known hosts: %s", e)

    def _save(self) -> None:
        """Persist known hosts to disk atomically."""
        try:
            self._hosts_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._hosts_path.with_suffix(".tmp")
            tmp_path.write_text(
                json.dumps(self._keys, indent=2), encoding="utf-8"
            )
            tmp_path.replace(self._hosts_path)
        except OSError as e:
            logger.warning("Could not save known hosts: %s", e)

    def missing_host_key(
        self, client: paramiko.SSHClient, hostname: str, key: paramiko.PKey
    ) -> None:
        """Handle a host key that is not yet in known_hosts."""
        fp = key.get_fingerprint().hex()

        if hostname in self._keys:
            if self._keys[hostname] == fp:
                return
            raise paramiko.SSHException(
                f"Host key for {hostname} has changed! "
                f"Expected {self._keys[hostname]}, got {fp}. "
                f"Possible MITM attack."
            )

        logger.warning(
            "Accepting new host key for %s (fingerprint: %s)", hostname, fp
        )
        self._keys[hostname] = fp
        self._save()


class RobotAudio:
    """Manages robot audio recording, speech recognition and file transfer."""

    def __init__(
        self,
        audio_recorder: Any,
        speech_reco: Any,
        memory: Any,
        remote_wav_path: str,
        ssh_host: str,
        ssh_username: str,
        ssh_password: str,
        ssh_port: int = 22,
    ) -> None:
        """Initialize audio services.

        Args:
            audio_recorder: ALAudioRecorder service.
            speech_reco: ALSpeechRecognition service.
            memory: ALMemory service.
            remote_wav_path: Path to store audio on robot.
            ssh_host: Robot IP for SSH/SFTP connection.
            ssh_username: SSH username.
            ssh_password: SSH password.
            ssh_port: SSH port for file transfer.
        """
        if not ssh_host:
            raise ValueError("ssh_host cannot be empty")

        self.audio_recorder = audio_recorder
        self.speech_reco = speech_reco
        self.memory = memory
        self.remote_wav_path = remote_wav_path
        self.ssh_host = ssh_host
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.ssh_port = ssh_port

        self._ssh: paramiko.SSHClient | None = None
        self._lock = threading.Lock()
        self._host_key_policy = _SavedHostKeyPolicy()

    def _get_ssh(self) -> paramiko.SSHClient:
        """Return an active SSH connection, creating one if needed."""
        if self._ssh is not None:
            try:
                transport = self._ssh.get_transport()
                if transport and transport.is_active():
                    return self._ssh
            except (paramiko.SSHException, OSError):
                pass
            logger.debug("SSH connection stale, reconnecting...")
            self._close_ssh()

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(self._host_key_policy)
        ssh.connect(
            self.ssh_host,
            port=self.ssh_port,
            username=self.ssh_username,
            password=self.ssh_password,
        )
        self._ssh = ssh
        return ssh

    def _close_ssh(self) -> None:
        """Close the current SSH connection if open."""
        if self._ssh is not None:
            try:
                self._ssh.close()
            except (paramiko.SSHException, OSError):
                pass
            self._ssh = None

    def start_recording(self) -> None:
        """Start recording audio and subscribe to speech detection."""
        try:
            self.audio_recorder.stopMicrophonesRecording()
        except RuntimeError:
            logger.debug("No active recording to stop")
        self.speech_reco.subscribe("SpeechDetector")
        self.audio_recorder.startMicrophonesRecording(
            self.remote_wav_path, "wav", 48000, [1, 0, 0, 0]
        )

    def stop_recording(self) -> None:
        """Stop recording and unsubscribe from speech detection."""
        self.audio_recorder.stopMicrophonesRecording()
        self.speech_reco.unsubscribe("SpeechDetector")

    def is_speech_detected(self) -> bool:
        """Check if speech is currently detected."""
        return bool(self.memory.getData("SpeechDetected"))

    def download_audio(self, local_path: str) -> None:
        """Download recorded audio from robot via SFTP.

        Args:
            local_path: Local path to save the downloaded WAV file.

        Raises:
            RuntimeError: If SFTP download fails.
        """
        with self._lock:
            try:
                ssh = self._get_ssh()
                with ssh.open_sftp() as sftp:
                    sftp.get(self.remote_wav_path, local_path)
            except (paramiko.SSHException, OSError) as e:
                self._close_ssh()
                raise RuntimeError(f"SFTP download failed: {e}") from e

    def close(self) -> None:
        """Close the persistent SSH connection."""
        with self._lock:
            self._close_ssh()
