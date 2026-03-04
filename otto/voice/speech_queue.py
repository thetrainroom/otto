"""File-based TTS bridge — MCP server writes lines, voice daemon reads and speaks."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SPEECH_QUEUE_PATH = Path.home() / ".otto" / "speech_queue.txt"


def enqueue(text: str) -> None:
    """Write a line to the speech queue file for the voice daemon to speak."""
    SPEECH_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SPEECH_QUEUE_PATH, "a") as f:
        f.write(text.strip() + "\n")
    logger.debug("Enqueued speech: %s", text[:50])


def dequeue_all() -> list[str]:
    """Read and clear all pending speech lines."""
    if not SPEECH_QUEUE_PATH.exists():
        return []

    try:
        text = SPEECH_QUEUE_PATH.read_text().strip()
        if not text:
            return []

        # Clear the file
        SPEECH_QUEUE_PATH.write_text("")
        return [line.strip() for line in text.splitlines() if line.strip()]
    except Exception:
        logger.exception("Error reading speech queue")
        return []
