"""Voice daemon — push-to-talk STT + TTS bridge for Claude Desktop."""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time

logger = logging.getLogger(__name__)


def main():
    """Entry point for otto-voice command."""
    import argparse

    parser = argparse.ArgumentParser(description="OTTO voice daemon")
    parser.add_argument("--config", help="Path to otto.yaml config file")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    from otto.config import load_config

    config = load_config(args.config)
    voice_config = config["voice"]

    if voice_config["mode"] == "disabled":
        logger.info("Voice mode is disabled in config")
        return

    daemon = VoiceDaemon(config)
    daemon.run()


EMERGENCY_COMMANDS = {
    "stop": "power_off",
    "go": "power_on",
}


class VoiceDaemon:
    """Push-to-talk voice daemon that types transcriptions into Claude Desktop."""

    def __init__(self, config: dict):
        self.config = config
        self.voice_config = config["voice"]
        self._recording = False
        self._stop_event = threading.Event()
        self._transcriber = None
        self._speaker = None
        self._rocrail_client = None

    def _ensure_loaded(self):
        if self._transcriber is None:
            from otto.voice.transcriber import Transcriber

            self._transcriber = Transcriber(model_size=self.voice_config["whisper_model"])

        if self._speaker is None:
            from otto.voice.speaker import Speaker

            self._speaker = Speaker(
                voice=self.voice_config["tts_voice"],
                speed=self.voice_config["tts_speed"],
            )

        if self._rocrail_client is None:
            from otto.rocrail.client import RocrailClient

            rc = self.config["rocrail"]
            self._rocrail_client = RocrailClient(host=rc["host"], port=rc["port"])
            result = self._rocrail_client.connect()
            if result["success"]:
                logger.info("Emergency commands: connected to Rocrail at %s:%d", rc["host"], rc["port"])
            else:
                logger.warning("Emergency commands unavailable: %s", result.get("error"))
                self._rocrail_client = None

    def run(self):
        """Start the voice daemon main loop."""
        self._ensure_loaded()

        from pynput import keyboard

        hotkey_name = self.voice_config.get("key", "f9")
        hotkey = getattr(keyboard.Key, hotkey_name, None)
        if hotkey is None:
            logger.error("Unknown hotkey: %s", hotkey_name)
            sys.exit(1)

        logger.info("Voice daemon started. Press %s to talk.", hotkey_name.upper())

        # Start speech queue polling in background
        speech_thread = threading.Thread(target=self._poll_speech_queue, daemon=True)
        speech_thread.start()

        def on_press(key):
            if key == hotkey and not self._recording:
                self._recording = True
                self._stop_event.clear()
                logger.info("Recording started...")
                threading.Thread(target=self._record_and_type, daemon=True).start()

        def on_release(key):
            if key == hotkey and self._recording:
                self._recording = False
                self._stop_event.set()
                logger.info("Recording stopped.")

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                logger.info("Voice daemon stopped.")

    def _record_and_type(self):
        """Record audio, transcribe, and type into Claude Desktop."""
        try:
            text = self._transcriber.record_and_transcribe(self._stop_event)
            if not text:
                logger.info("No speech detected.")
                return

            logger.info("Transcribed: %s", text)

            # Check for emergency commands — bypass LLM entirely
            if self._handle_emergency(text):
                return

            self._paste_text(text)
        except Exception:
            logger.exception("Error during recording/transcription")

    def _handle_emergency(self, text: str) -> bool:
        """Check for emergency voice commands. Returns True if handled."""
        word = text.strip().lower().rstrip(".,!?")

        if word not in EMERGENCY_COMMANDS:
            return False

        action = EMERGENCY_COMMANDS[word]
        logger.warning("EMERGENCY COMMAND: %s -> %s", word, action)

        if self._rocrail_client is None:
            logger.error("Cannot execute emergency command — not connected to Rocrail")
            return True

        if action == "power_off":
            self._rocrail_client.power_off()
            # Speak confirmation in parallel — command already executing
            if self._speaker:
                self._speaker.speak_async("Power off.")
        elif action == "power_on":
            self._rocrail_client.power_on()
            if self._speaker:
                self._speaker.speak_async("Power on.")

        return True

    def _paste_text(self, text: str):
        """Paste text into the active application via clipboard."""
        import pyperclip

        pyperclip.copy(text)
        # Simulate Cmd+V on macOS
        if sys.platform == "darwin":
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'],
                check=False,
            )
        else:
            import pyautogui

            pyautogui.hotkey("ctrl", "v")

    def _poll_speech_queue(self):
        """Poll the speech queue file and speak each line."""
        from otto.voice.speech_queue import dequeue_all

        while True:
            try:
                lines = dequeue_all()
                for line in lines:
                    logger.info("Speaking: %s", line[:50])
                    self._speaker.speak(line)
            except Exception:
                logger.exception("Error in speech queue polling")
            time.sleep(0.5)


if __name__ == "__main__":
    main()
