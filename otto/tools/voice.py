"""Voice tools — TTS speech queue."""

from otto.tools._registry import mcp
from otto.voice.speech_queue import enqueue as enqueue_speech


@mcp.tool()
def speak(text: str) -> dict:
    """Speak text aloud via the voice daemon's TTS system. The text will be queued for speaking."""
    enqueue_speech(text)
    return {"spoken": text}
