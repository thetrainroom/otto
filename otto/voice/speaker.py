"""TTS speaker — wraps kokoro-onnx for text-to-speech synthesis."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

MODELS_DIR = Path.home() / ".otto" / "models"


class Speaker:
    """Text-to-speech using kokoro-onnx."""

    def __init__(self, voice: str = "af_heart", speed: float = 1.0):
        self.voice = voice
        self.speed = speed
        self._kokoro = None

    def _ensure_loaded(self):
        if self._kokoro is not None:
            return

        try:
            import kokoro_onnx

            model_path = MODELS_DIR / "kokoro-v1.0.onnx"
            voices_path = MODELS_DIR / "voices-v1.0.bin"

            if not model_path.exists() or not voices_path.exists():
                raise FileNotFoundError(
                    f"Kokoro model files not found in {MODELS_DIR}. "
                    "Run: python scripts/install_models.py"
                )

            self._kokoro = kokoro_onnx.Kokoro(str(model_path), str(voices_path))
            logger.info("Kokoro TTS loaded (voice=%s, speed=%.1f)", self.voice, self.speed)
        except ImportError:
            raise ImportError("kokoro-onnx not installed. Install with: pip install 'otto[voice]'")

    def speak(self, text: str) -> None:
        """Synthesize and play text, blocking until complete."""
        self._ensure_loaded()

        import numpy as np
        import sounddevice as sd

        samples, sample_rate = self._kokoro.create(text, voice=self.voice, speed=self.speed)
        sd.play(samples, samplerate=sample_rate)
        sd.wait()

    def speak_async(self, text: str) -> threading.Thread:
        """Synthesize and play text in a background thread."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t
