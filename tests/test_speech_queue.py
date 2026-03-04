"""Tests for otto.voice.speech_queue."""

from otto.voice.speech_queue import enqueue, dequeue_all


class TestSpeechQueue:
    def test_enqueue_dequeue(self, tmp_path, monkeypatch):
        queue_path = tmp_path / "speech_queue.txt"
        monkeypatch.setattr("otto.voice.speech_queue.SPEECH_QUEUE_PATH", queue_path)

        enqueue("Hello world")
        enqueue("Second line")

        lines = dequeue_all()
        assert lines == ["Hello world", "Second line"]

    def test_dequeue_clears(self, tmp_path, monkeypatch):
        queue_path = tmp_path / "speech_queue.txt"
        monkeypatch.setattr("otto.voice.speech_queue.SPEECH_QUEUE_PATH", queue_path)

        enqueue("Test")
        dequeue_all()
        assert dequeue_all() == []

    def test_dequeue_empty(self, tmp_path, monkeypatch):
        queue_path = tmp_path / "speech_queue.txt"
        monkeypatch.setattr("otto.voice.speech_queue.SPEECH_QUEUE_PATH", queue_path)
        assert dequeue_all() == []

    def test_strips_whitespace(self, tmp_path, monkeypatch):
        queue_path = tmp_path / "speech_queue.txt"
        monkeypatch.setattr("otto.voice.speech_queue.SPEECH_QUEUE_PATH", queue_path)

        enqueue("  padded text  ")
        lines = dequeue_all()
        assert lines == ["padded text"]

    def test_skips_blank_lines(self, tmp_path, monkeypatch):
        queue_path = tmp_path / "speech_queue.txt"
        monkeypatch.setattr("otto.voice.speech_queue.SPEECH_QUEUE_PATH", queue_path)

        queue_path.write_text("line1\n\n\nline2\n")
        lines = dequeue_all()
        assert lines == ["line1", "line2"]

    def test_creates_parent_dirs(self, tmp_path, monkeypatch):
        queue_path = tmp_path / "sub" / "dir" / "queue.txt"
        monkeypatch.setattr("otto.voice.speech_queue.SPEECH_QUEUE_PATH", queue_path)

        enqueue("Test")
        assert queue_path.exists()
