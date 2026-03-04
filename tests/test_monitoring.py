"""Tests for otto.monitoring."""

import json
import time

from otto.monitoring import MovementTracker, TimingDatabase, ActiveMovement


class TestMovementTracker:
    def test_start_and_get(self):
        tracker = MovementTracker()
        tracker.start_movement("loco1", "bk1", "bk2", 10.0)
        assert "loco1" in tracker.get_all()
        m = tracker.get_all()["loco1"]
        assert m.from_block == "bk1"
        assert m.to_block == "bk2"

    def test_complete(self):
        tracker = MovementTracker()
        tracker.start_movement("loco1", "bk1", "bk2", 10.0)
        duration = tracker.complete_movement("loco1")
        assert duration is not None
        assert duration >= 0
        assert "loco1" not in tracker.get_all()

    def test_complete_unknown(self):
        tracker = MovementTracker()
        assert tracker.complete_movement("unknown") is None

    def test_overdue_not_immediately(self):
        tracker = MovementTracker()
        tracker.start_movement("loco1", "bk1", "bk2", 100.0)
        assert len(tracker.get_overdue()) == 0

    def test_overdue_after_time(self):
        tracker = MovementTracker()
        tracker.start_movement("loco1", "bk1", "bk2", 5.0)
        m = tracker.get_all()["loco1"]
        m.start_time = time.time() - 10  # simulate 10s elapsed
        overdue = tracker.get_overdue()
        assert len(overdue) == 1
        assert overdue[0].loco_id == "loco1"

    def test_acknowledge(self):
        tracker = MovementTracker()
        tracker.start_movement("loco1", "bk1", "bk2", 5.0)
        assert tracker.acknowledge("loco1") is True
        assert tracker.get_all()["loco1"].acknowledged is True

    def test_acknowledge_unknown(self):
        tracker = MovementTracker()
        assert tracker.acknowledge("unknown") is False

    def test_remove(self):
        tracker = MovementTracker()
        tracker.start_movement("loco1", "bk1", "bk2", 5.0)
        tracker.remove("loco1")
        assert "loco1" not in tracker.get_all()


class TestActiveMovement:
    def test_is_overdue(self):
        m = ActiveMovement("loco1", "bk1", "bk2", 5.0, start_time=time.time() - 10)
        assert m.is_overdue is True

    def test_not_overdue(self):
        m = ActiveMovement("loco1", "bk1", "bk2", 100.0)
        assert m.is_overdue is False

    def test_elapsed(self):
        m = ActiveMovement("loco1", "bk1", "bk2", 5.0, start_time=time.time() - 3)
        assert 2.5 < m.elapsed < 4.0


class TestTimingDatabase:
    def test_record_and_estimate(self, tmp_path, monkeypatch):
        db_path = tmp_path / "timing.json"
        monkeypatch.setattr("otto.monitoring.TIMING_DB_PATH", db_path)

        db = TimingDatabase()
        for d in [10.0, 11.0, 9.5, 10.5, 12.0]:
            db.record("bk1", "bk2", d)

        est = db.estimate("bk1", "bk2")
        assert est > 10.0  # mean + 3*stddev
        assert est < 20.0  # reasonable upper bound

    def test_cold_start_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr("otto.monitoring.TIMING_DB_PATH", tmp_path / "timing.json")
        db = TimingDatabase()
        assert db.estimate("bk99", "bk100") == 30.0

    def test_custom_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr("otto.monitoring.TIMING_DB_PATH", tmp_path / "timing.json")
        db = TimingDatabase()
        assert db.estimate("bk99", "bk100", default=60.0) == 60.0

    def test_insufficient_samples(self, tmp_path, monkeypatch):
        monkeypatch.setattr("otto.monitoring.TIMING_DB_PATH", tmp_path / "timing.json")
        db = TimingDatabase()
        db.record("bk1", "bk2", 10.0)
        db.record("bk1", "bk2", 11.0)
        assert db.estimate("bk1", "bk2") == 30.0  # < 3 samples, use default

    def test_persistence(self, tmp_path, monkeypatch):
        db_path = tmp_path / "timing.json"
        monkeypatch.setattr("otto.monitoring.TIMING_DB_PATH", db_path)

        db1 = TimingDatabase()
        db1.record("bk1", "bk2", 10.0)

        # Load fresh instance — verify file was persisted
        TimingDatabase()
        data = json.loads(db_path.read_text())
        assert "bk1->bk2" in data
        assert len(data["bk1->bk2"]) == 1

    def test_rolling_window(self, tmp_path, monkeypatch):
        monkeypatch.setattr("otto.monitoring.TIMING_DB_PATH", tmp_path / "timing.json")
        db = TimingDatabase()
        for i in range(25):
            db.record("bk1", "bk2", float(i))

        data = json.loads((tmp_path / "timing.json").read_text())
        assert len(data["bk1->bk2"]) == 20  # max samples
