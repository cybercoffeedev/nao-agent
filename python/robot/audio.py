class RobotAudio:
    """Manages robot audio recording and speech recognition."""

    def __init__(self, audio_recorder, speech_reco, memory, remote_wav_path):
        """Initializes audio services.

        Args:
            audio_recorder: ALAudioRecorder service.
            speech_reco: ALSpeechRecognition service.
            memory: ALMemory service.
            remote_wav_path: Path to store audio on robot.
        """
        self.audio_recorder = audio_recorder
        self.speech_reco = speech_reco
        self.memory = memory
        self.remote_wav_path = remote_wav_path

    def start_recording(self):
        """Starts recording audio and subscribes to speech detection."""
        try:
            self.audio_recorder.stopMicrophonesRecording()
        except Exception:
            pass
        self.speech_reco.subscribe("SpeechDetector")
        self.audio_recorder.startMicrophonesRecording(self.remote_wav_path, "wav", 48000, [1, 0, 0, 0])

    def stop_recording(self):
        """Stops recording and unsubscribes from speech detection."""
        self.audio_recorder.stopMicrophonesRecording()
        self.speech_reco.unsubscribe("SpeechDetector")

    def is_speech_detected(self) -> bool:
        """Checks if speech is currently detected."""
        return bool(self.memory.getData("SpeechDetected"))
