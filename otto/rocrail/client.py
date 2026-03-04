"""Rocrail client wrapper — wraps PyRocrail with a clean API for MCP tools."""

from __future__ import annotations

import logging
from typing import Any, Callable

from thefuzz import process as fuzz_process

from pyrocrail import PyRocrail

logger = logging.getLogger(__name__)


class RocrailClient:
    """High-level wrapper around PyRocrail for OTTO's MCP tools.

    All public methods return serializable dicts suitable for MCP tool responses.
    """

    def __init__(self, host: str = "localhost", port: int = 8051):
        self.host = host
        self.port = port
        self._pr: PyRocrail | None = None
        self._change_callbacks: list[Callable] = []

    @property
    def connected(self) -> bool:
        return self._pr is not None

    @property
    def model(self):
        if self._pr is None:
            raise RuntimeError("Not connected to Rocrail")
        return self._pr.model

    def connect(self) -> dict:
        """Connect to Rocrail server."""
        if self._pr is not None:
            return {"success": True, "message": "Already connected"}

        try:
            self._pr = PyRocrail(
                ip=self.host,
                port=self.port,
                on_disconnect=self._on_disconnect,
            )
            self._pr.start()
            self._pr.model.change_callback = self._dispatch_change
            logger.info("Connected to Rocrail at %s:%d", self.host, self.port)
            return {"success": True, "message": f"Connected to Rocrail at {self.host}:{self.port}"}
        except Exception as e:
            self._pr = None
            logger.error("Failed to connect to Rocrail: %s", e)
            return {"success": False, "error": str(e)}

    def disconnect(self) -> dict:
        """Disconnect from Rocrail server."""
        if self._pr is None:
            return {"success": True, "message": "Not connected"}

        try:
            self._pr.stop()
        except Exception as e:
            logger.warning("Error during disconnect: %s", e)
        finally:
            self._pr = None
        return {"success": True, "message": "Disconnected"}

    def _on_disconnect(self, model):
        logger.warning("Disconnected from Rocrail")
        self._pr = None

    def _dispatch_change(self, obj_type: str, obj_id: str, obj: Any):
        for cb in self._change_callbacks:
            try:
                cb(obj_type, obj_id, obj)
            except Exception:
                logger.exception("Error in change callback")

    def register_change_callback(self, fn: Callable):
        """Register a callback for model state changes."""
        self._change_callbacks.append(fn)

    # --- Layout queries ---

    def get_layout_state(self) -> dict:
        """Get full layout state via PyRocrail's export_state()."""
        self._ensure_connected()
        return self.model.export_state()

    def find_loco(self, query: str) -> dict:
        """Fuzzy-match a locomotive by name/ID."""
        self._ensure_connected()
        locos = self.model.get_locomotives()
        if not locos:
            return {"found": False, "error": "No locomotives on layout"}

        match = fuzz_process.extractOne(query, list(locos.keys()))
        if match is None or match[1] < 60:
            return {"found": False, "error": f"No locomotive matching '{query}'", "available": list(locos.keys())}

        loco_id = match[0]
        loco = locos[loco_id]
        return {
            "found": True,
            "id": loco_id,
            "match_score": match[1],
            "speed": loco.V,
            "direction": "forward" if loco.dir else "reverse",
            "block": getattr(loco, "blockid", ""),
            "destination": getattr(loco, "destblockid", ""),
            "mode": loco.mode,
        }

    def find_route_between(self, from_block: str, to_block: str) -> dict:
        """Find a route between two blocks."""
        self._ensure_connected()
        routes = self.model.get_routes()
        matches = []
        for route_id, route in routes.items():
            if route.bka == from_block and route.bkb == to_block:
                matches.append({
                    "id": route_id,
                    "from": route.bka,
                    "to": route.bkb,
                    "status": route.status,
                    "free": route.is_free(),
                })
            elif route.bkb == from_block and route.bka == to_block:
                matches.append({
                    "id": route_id,
                    "from": route.bka,
                    "to": route.bkb,
                    "status": route.status,
                    "free": route.is_free(),
                    "note": "reverse direction",
                })

        if not matches:
            return {"found": False, "error": f"No route from '{from_block}' to '{to_block}'"}

        return {"found": True, "routes": matches}

    def get_topology(self) -> dict:
        """Build adjacency graph from routes."""
        self._ensure_connected()
        routes = self.model.get_routes()
        adjacency: dict[str, set[str]] = {}

        for route in routes.values():
            if route.bka and route.bkb:
                adjacency.setdefault(route.bka, set()).add(route.bkb)
                adjacency.setdefault(route.bkb, set()).add(route.bka)

        return {block: sorted(neighbors) for block, neighbors in sorted(adjacency.items())}

    # --- Locomotive control ---

    def set_loco_speed(self, loco_id: str, speed: int) -> dict:
        """Set locomotive speed (0-100)."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.set_speed(speed)
            return {"success": True, "loco": loco_id, "speed": speed}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_loco(self, loco_id: str) -> dict:
        """Emergency stop a locomotive."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.emergency_stop()
            return {"success": True, "loco": loco_id, "action": "emergency_stop"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def dispatch_loco(self, loco_id: str, block_id: str | None = None, speed: str = "mid") -> dict:
        """Dispatch a locomotive, optionally to a specific block."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            if block_id:
                loco.gotoblock(block_id)
            loco.dispatch()
            loco.go()
            return {
                "success": True,
                "loco": loco_id,
                "action": "dispatched",
                "destination": block_id or "auto",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Route control ---

    def set_route(self, route_id: str) -> dict:
        """Activate a route."""
        self._ensure_connected()
        try:
            route = self.model.get_st(route_id)
            route.set()
            return {"success": True, "route": route_id, "action": "set"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Switch control ---

    def set_switch(self, switch_id: str, position: str) -> dict:
        """Set a switch position (straight/turnout/left/right)."""
        self._ensure_connected()
        try:
            sw = self.model.get_sw(switch_id)
            commands = {
                "straight": sw.straight,
                "turnout": sw.turnout,
                "left": sw.left,
                "right": sw.right,
            }
            cmd = commands.get(position.lower())
            if cmd is None:
                return {"success": False, "error": f"Unknown position '{position}'. Use: straight, turnout, left, right"}
            cmd()
            return {"success": True, "switch": switch_id, "position": position}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Signal control ---

    def set_signal(self, signal_id: str, aspect: str) -> dict:
        """Set a signal aspect (red/green/yellow/white)."""
        self._ensure_connected()
        try:
            sg = self.model.get_sg(signal_id)
            commands = {
                "red": sg.red,
                "green": sg.green,
                "yellow": sg.yellow,
                "white": sg.white,
            }
            cmd = commands.get(aspect.lower())
            if cmd is None:
                return {"success": False, "error": f"Unknown aspect '{aspect}'. Use: red, green, yellow, white"}
            cmd()
            return {"success": True, "signal": signal_id, "aspect": aspect}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- System control ---

    def emergency_stop_all(self) -> dict:
        """Emergency stop all trains."""
        self._ensure_connected()
        try:
            self._pr.emergency_stop()
            return {"success": True, "action": "emergency_stop_all"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def auto_on(self) -> dict:
        """Enable automatic mode."""
        self._ensure_connected()
        try:
            self._pr.auto_on()
            return {"success": True, "action": "auto_on"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def auto_off(self) -> dict:
        """Disable automatic mode."""
        self._ensure_connected()
        try:
            self._pr.auto_off()
            return {"success": True, "action": "auto_off"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_schedule(self, schedule_id: str) -> dict:
        """Get schedule details."""
        self._ensure_connected()
        try:
            schedule = self.model.get_schedule(schedule_id)
            entries = []
            for entry in schedule.entries:
                entries.append({
                    "block": entry.block,
                    "hour": entry.hour,
                    "minute": entry.minute,
                    "arrival_hour": entry.ahour,
                    "arrival_minute": entry.aminute,
                })
            return {
                "id": schedule_id,
                "train": schedule.trainid,
                "entries": entries,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Helpers ---

    def _ensure_connected(self):
        if self._pr is None:
            raise RuntimeError("Not connected to Rocrail. Call connect() first.")
