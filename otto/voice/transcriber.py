"""STT transcriber — wraps faster-whisper for speech-to-text."""

from __future__ import annotations

import logging
import threading

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


class Transcriber:
    """Speech-to-text using faster-whisper."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _ensure_loaded(self):
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_size, compute_type="int8")
            logger.info("Whisper model loaded: %s", self.model_size)
        except ImportError:
            raise ImportError("faster-whisper not installed. Install with: pip install 'otto[voice]'")

    def record_audio(self, stop_event: threading.Event) -> np.ndarray:
        """Record audio from the microphone until stop_event is set."""
        import sounddevice as sd

        frames = []

        def callback(indata, frame_count, time_info, status):
            if status:
                logger.warning("Audio input status: %s", status)
            frames.append(indata.copy())

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback):
            stop_event.wait()

        if not frames:
            return np.array([], dtype="float32")

        return np.concatenate(frames, axis=0).flatten()

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio array to text."""
        self._ensure_loaded()

        if audio.size == 0:
            return ""

        segments, _ = self._model.transcribe(audio, vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments).strip()

    def record_and_transcribe(self, stop_event: threading.Event) -> str:
        """Record audio until stop_event is set, then transcribe."""
        audio = self.record_audio(stop_event)
        if audio.size == 0:
            return ""
        return self.transcribe(audio)
