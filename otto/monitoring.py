"""Monitoring system — tracks train movements, learns timing, detects anomalies."""

from __future__ import annotations

import json
import logging
import statistics
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from otto.rocrail.client import RocrailClient

logger = logging.getLogger(__name__)

TIMING_DB_PATH = Path.home() / ".otto" / "timing.json"


@dataclass
class ActiveMovement:
    loco_id: str
    from_block: str
    to_block: str
    expected_seconds: float
    start_time: float = field(default_factory=time.time)
    acknowledged: bool = False
    last_alert_time: float = 0.0

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def is_overdue(self) -> bool:
        return self.elapsed > self.expected_seconds


class MovementTracker:
    """Tracks dispatched locomotive movements and detects overdue arrivals."""

    def __init__(self):
        self._movements: dict[str, ActiveMovement] = {}

    def start_movement(self, loco_id: str, from_block: str, to_block: str, expected_seconds: float):
        self._movements[loco_id] = ActiveMovement(
            loco_id=loco_id,
            from_block=from_block,
            to_block=to_block,
            expected_seconds=expected_seconds,
        )
        logger.info("Tracking %s: %s -> %s (expected %.0fs)", loco_id, from_block, to_block, expected_seconds)

    def complete_movement(self, loco_id: str) -> float | None:
        """Complete a movement, returning actual duration or None if not tracked."""
        movement = self._movements.pop(loco_id, None)
        if movement is None:
            return None
        duration = movement.elapsed
        logger.info("Completed %s: %.1fs (expected %.1fs)", loco_id, duration, movement.expected_seconds)
        return duration

    def get_overdue(self, multiplier: float = 1.0) -> list[ActiveMovement]:
        """Get all movements that have exceeded their expected time * multiplier."""
        return [m for m in self._movements.values() if m.elapsed > m.expected_seconds * multiplier]

    def get_all(self) -> dict[str, ActiveMovement]:
        return dict(self._movements)

    def acknowledge(self, loco_id: str) -> bool:
        if loco_id in self._movements:
            self._movements[loco_id].acknowledged = True
            return True
        return False

    def remove(self, loco_id: str):
        self._movements.pop(loco_id, None)


class TimingDatabase:
    """Learns segment timing from observations. Persists to ~/.otto/timing.json."""

    MAX_SAMPLES = 20

    def __init__(self):
        self._data: dict[str, list[float]] = {}
        self._load()

    def _segment_key(self, from_block: str, to_block: str) -> str:
        return f"{from_block}->{to_block}"

    def _load(self):
        if TIMING_DB_PATH.exists():
            try:
                self._data = json.loads(TIMING_DB_PATH.read_text())
                logger.info("Loaded timing data: %d segments", len(self._data))
            except Exception:
                logger.warning("Failed to load timing database, starting fresh")
                self._data = {}

    def _save(self):
        TIMING_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        TIMING_DB_PATH.write_text(json.dumps(self._data, indent=2))

    def record(self, from_block: str, to_block: str, duration: float):
        """Record a timing observation."""
        key = self._segment_key(from_block, to_block)
        samples = self._data.setdefault(key, [])
        samples.append(duration)
        # Rolling window
        if len(samples) > self.MAX_SAMPLES:
            self._data[key] = samples[-self.MAX_SAMPLES:]
        self._save()
        logger.debug("Recorded timing %s: %.1fs (%d samples)", key, duration, len(self._data[key]))

    def estimate(self, from_block: str, to_block: str, default: float = 30.0) -> float:
        """Estimate expected duration for a segment.

        Returns mean + 3*stddev if >= 3 samples, otherwise default.
        """
        key = self._segment_key(from_block, to_block)
        samples = self._data.get(key, [])
        if len(samples) < 3:
            return default
        mean = statistics.mean(samples)
        stdev = statistics.stdev(samples)
        return mean + 3 * stdev


@dataclass
class Alert:
    alert_type: str  # "timeout" | "silence"
    message: str
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MonitoringSystem:
    """Coordinates movement tracking, timing learning, and anomaly detection."""

    def __init__(self, client: RocrailClient, config: dict):
        self.client = client
        self.config = config.get("monitoring", {})
        self.tracker = MovementTracker()
        self.timing_db = TimingDatabase()
        self._alerts: list[Alert] = []
        self._last_block_change: float = time.time()
        self._running = False
        self._thread: threading.Thread | None = None

        if self.config.get("enabled", True):
            client.register_change_callback(self._on_change)

    def start(self):
        """Start background monitoring thread."""
        if not self.config.get("enabled", True):
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Monitoring system started")

    def stop(self):
        """Stop background monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _on_change(self, obj_type: str, obj_id: str, obj):
        """Handle model state changes from PyRocrail."""
        if obj_type in ("bk", "block"):
            self._last_block_change = time.time()

            # Check if a tracked loco arrived at its destination
            if hasattr(obj, "locid") and obj.locid:
                movement = self.tracker.get_all().get(obj.locid)
                if movement and movement.to_block == obj_id:
                    duration = self.tracker.complete_movement(obj.locid)
                    if duration is not None:
                        self.timing_db.record(movement.from_block, movement.to_block, duration)

    def _monitor_loop(self):
        """Background thread that checks for anomalies every 2 seconds."""
        while self._running:
            try:
                self._check_overdue()
                self._check_silence()
            except Exception:
                logger.exception("Error in monitoring loop")
            time.sleep(2)

    def _check_overdue(self):
        multiplier = self.config.get("timeout_multiplier", 3.0)
        repeat_interval = self.config.get("repeat_alert_interval", 60)
        now = time.time()

        for movement in self.tracker.get_overdue(multiplier):
            if movement.acknowledged:
                continue
            if now - movement.last_alert_time < repeat_interval:
                continue

            movement.last_alert_time = now
            self._alerts.append(Alert(
                alert_type="timeout",
                message=f"{movement.loco_id} overdue: {movement.from_block}->{movement.to_block} "
                        f"(expected {movement.expected_seconds:.0f}s, elapsed {movement.elapsed:.0f}s)",
                data={
                    "loco": movement.loco_id,
                    "from_block": movement.from_block,
                    "to_block": movement.to_block,
                    "expected": movement.expected_seconds,
                    "elapsed": movement.elapsed,
                },
            ))

    def _check_silence(self):
        threshold = self.config.get("silence_threshold", 120)
        silence_duration = time.time() - self._last_block_change

        if silence_duration > threshold:
            # Only alert once per silence period (check last alert)
            if self._alerts and self._alerts[-1].alert_type == "silence":
                return
            self._alerts.append(Alert(
                alert_type="silence",
                message=f"No block changes for {silence_duration:.0f}s",
                data={"seconds": silence_duration},
            ))

    # --- Public API for MCP tools ---

    def track_dispatch(self, loco_id: str, from_block: str, to_block: str):
        """Start tracking a dispatched locomotive."""
        expected = self.timing_db.estimate(
            from_block, to_block,
            default=self.config.get("minimum_timeout", 30),
        )
        self.tracker.start_movement(loco_id, from_block, to_block, expected)

    def get_active_movements(self) -> list[dict]:
        """Get all active movements with status."""
        result = []
        for loco_id, m in self.tracker.get_all().items():
            result.append({
                "loco": loco_id,
                "from": m.from_block,
                "to": m.to_block,
                "elapsed": round(m.elapsed, 1),
                "expected": round(m.expected_seconds, 1),
                "overdue": m.is_overdue,
                "acknowledged": m.acknowledged,
            })
        return result

    def acknowledge_timeout(self, loco_id: str) -> dict:
        if self.tracker.acknowledge(loco_id):
            return {"success": True, "loco": loco_id}
        return {"success": False, "error": f"No active movement for {loco_id}"}

    def report_recovered(self, loco_id: str, block_id: str) -> dict:
        duration = self.tracker.complete_movement(loco_id)
        if duration is not None:
            return {"success": True, "loco": loco_id, "block": block_id, "duration": round(duration, 1)}
        return {"success": False, "error": f"No active movement for {loco_id}"}

    def get_pending_alerts(self) -> list[dict]:
        """Get and clear pending alerts."""
        alerts = [
            {"type": a.alert_type, "message": a.message, "data": a.data, "timestamp": a.timestamp}
            for a in self._alerts
        ]
        self._alerts.clear()
        return alerts
