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

    # =========================================================================
    # Layout queries
    # =========================================================================

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
                matches.append({"id": route_id, "from": route.bka, "to": route.bkb, "status": route.status, "free": route.is_free()})
            elif route.bkb == from_block and route.bka == to_block:
                matches.append({"id": route_id, "from": route.bka, "to": route.bkb, "status": route.status, "free": route.is_free(), "note": "reverse direction"})
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

    # =========================================================================
    # Locomotive control
    # =========================================================================

    def set_loco_speed(self, loco_id: str, speed: int) -> dict:
        """Set locomotive speed (0-100)."""
        self._ensure_connected()
        if speed < 0:
            return {"success": False, "error": f"Speed must be 0-100, got {speed}. Use set_loco_direction to reverse."}
        if speed > 100:
            return {"success": False, "error": f"Speed must be 0-100, got {speed}."}
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

    def soft_stop_loco(self, loco_id: str) -> dict:
        """Graceful stop — loco stops at next block in auto mode."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.stop()
            return {"success": True, "loco": loco_id, "action": "soft_stop"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def dispatch_loco(self, loco_id: str, block_id: str | None = None, speed: str = "mid") -> dict:
        """Dispatch a locomotive, optionally to a specific block."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco_block = getattr(loco, "blockid", None)
            if not loco_block:
                return {"success": False, "error": f"Locomotive '{loco_id}' is not placed on any block. Use place_loco first."}
            if block_id:
                loco.gotoblock(block_id)
            loco.dispatch()
            loco.go()
            result = {"success": True, "loco": loco_id, "action": "dispatched", "from_block": loco_block, "destination": block_id or "auto"}
            if loco.mode not in ("auto", "run"):
                result["warning"] = "Auto mode may not be active — loco will not move until automation is started. " "Use start_automation() if needed."
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_loco_direction(self, loco_id: str, direction: str) -> dict:
        """Set locomotive direction: forward, reverse, or toggle."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            if direction == "forward":
                loco.set_direction(True)
            elif direction == "reverse":
                loco.set_direction(False)
            elif direction == "toggle":
                loco.swap()
            else:
                return {"success": False, "error": f"Unknown direction '{direction}'. Use: forward, reverse, toggle"}
            return {"success": True, "loco": loco_id, "direction": direction}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def go_loco_forward(self, loco_id: str, speed: int | None = None) -> dict:
        """Set direction to forward and optionally set speed."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.go_forward(speed)
            return {"success": True, "loco": loco_id, "direction": "forward", "speed": speed}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def go_loco_reverse(self, loco_id: str, speed: int | None = None) -> dict:
        """Set direction to reverse and optionally set speed."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.go_reverse(speed)
            return {"success": True, "loco": loco_id, "direction": "reverse", "speed": speed}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_loco_function(self, loco_id: str, function: int, state: bool) -> dict:
        """Set a decoder function on/off."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.set_function(function, state)
            return {"success": True, "loco": loco_id, "function": function, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def place_loco(self, loco_id: str, block_id: str) -> dict:
        """Place a locomotive on a specific block."""
        self._ensure_connected()
        try:
            self.model.get_lc(loco_id)  # validate loco exists
            block = self.model.get_bk(block_id)
            block.reserve(loco_id)
            return {"success": True, "loco": loco_id, "block": block_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def assign_loco(self, loco_id: str) -> dict:
        """Assign a locomotive to Rocrail automatic control."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.dispatch()
            loco.go()
            return {"success": True, "loco": loco_id, "action": "assigned_to_auto"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def release_loco(self, loco_id: str) -> dict:
        """Release a locomotive from automatic control back to manual."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.stop()
            loco.regularreset()
            return {"success": True, "loco": loco_id, "action": "released_to_manual"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def soft_reset_loco(self, loco_id: str) -> dict:
        """Soft reset a locomotive."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.softreset()
            return {"success": True, "loco": loco_id, "action": "soft_reset"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_loco_class(self, loco_id: str, class_name: str | None = None) -> dict:
        """Set or clear locomotive class."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.set_class(class_name)
            return {"success": True, "loco": loco_id, "class": class_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def assign_train_to_loco(self, loco_id: str, train_id: str) -> dict:
        """Assign a train/operator to a locomotive."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.assign_train(train_id)
            return {"success": True, "loco": loco_id, "train": train_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def release_train_from_loco(self, loco_id: str) -> dict:
        """Release the assigned train/operator from a locomotive."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.release_train()
            return {"success": True, "loco": loco_id, "action": "train_released"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_loco_goto_block(self, loco_id: str, block_id: str) -> dict:
        """Set destination block for a locomotive without dispatching."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.gotoblock(block_id)
            return {"success": True, "loco": loco_id, "destination": block_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Block control
    # =========================================================================

    def set_block_state(self, block_id: str, state: str) -> dict:
        """Set block state: open, closed, or free."""
        self._ensure_connected()
        try:
            block = self.model.get_bk(block_id)
            commands = {
                "open": block.open,
                "closed": block.close,
                "close": block.close,
                "free": block.free,
            }
            cmd = commands.get(state.lower())
            if cmd is None:
                return {"success": False, "error": f"Unknown state '{state}'. Use: open, closed, free"}
            cmd()
            return {"success": True, "block": block_id, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def free_block_override(self, block_id: str) -> dict:
        """Force free a block, overriding any reservations."""
        self._ensure_connected()
        try:
            block = self.model.get_bk(block_id)
            block.free_override()
            return {"success": True, "block": block_id, "action": "free_override"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_block(self, block_id: str) -> dict:
        """Stop the locomotive currently in a block."""
        self._ensure_connected()
        try:
            block = self.model.get_bk(block_id)
            block.stop()
            return {"success": True, "block": block_id, "action": "stop"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def accept_block_ident(self, block_id: str) -> dict:
        """Accept locomotive identification in a block."""
        self._ensure_connected()
        try:
            block = self.model.get_bk(block_id)
            block.accept_ident()
            return {"success": True, "block": block_id, "action": "accept_ident"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_block_info(self, block_id: str) -> dict:
        """Get detailed information about a block."""
        self._ensure_connected()
        try:
            block = self.model.get_bk(block_id)
            return {
                "id": block_id,
                "state": block.state.value if hasattr(block.state, "value") else str(block.state),
                "occupied": block.occ,
                "reserved": block.reserved,
                "loco": block.locid,
                "is_free": block.is_free(),
                "is_closed": block.is_closed(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Route control
    # =========================================================================

    def set_route(self, route_id: str) -> dict:
        """Activate a route."""
        self._ensure_connected()
        try:
            route = self.model.get_st(route_id)
            route.set()
            return {"success": True, "route": route_id, "action": "set"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def lock_route(self, route_id: str) -> dict:
        """Lock a route."""
        self._ensure_connected()
        try:
            route = self.model.get_st(route_id)
            route.lock()
            return {"success": True, "route": route_id, "action": "locked"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def unlock_route(self, route_id: str) -> dict:
        """Unlock a route."""
        self._ensure_connected()
        try:
            route = self.model.get_st(route_id)
            route.unlock()
            return {"success": True, "route": route_id, "action": "unlocked"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def free_route(self, route_id: str) -> dict:
        """Free a route."""
        self._ensure_connected()
        try:
            route = self.model.get_st(route_id)
            route.free()
            return {"success": True, "route": route_id, "action": "freed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_route(self, route_id: str) -> dict:
        """Test a route without activating it."""
        self._ensure_connected()
        try:
            route = self.model.get_st(route_id)
            route.test()
            return {"success": True, "route": route_id, "action": "tested"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_route_info(self, route_id: str) -> dict:
        """Get detailed information about a route."""
        self._ensure_connected()
        try:
            route = self.model.get_st(route_id)
            return {
                "id": route_id,
                "from": route.bka,
                "to": route.bkb,
                "status": route.status,
                "is_free": route.is_free(),
                "is_locked": route.is_locked(),
                "is_set": route.is_set(),
                "switches": [{"id": sw.id, "cmd": str(sw.cmd.value) if hasattr(sw.cmd, "value") else str(sw.cmd)} for sw in route.switches],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Switch control
    # =========================================================================

    def set_switch(self, switch_id: str, position: str) -> dict:
        """Set a switch position (straight/turnout/left/right/flip)."""
        self._ensure_connected()
        try:
            sw = self.model.get_sw(switch_id)
            commands = {
                "straight": sw.straight,
                "turnout": sw.turnout,
                "left": sw.left,
                "right": sw.right,
                "flip": sw.flip,
            }
            cmd = commands.get(position.lower())
            if cmd is None:
                return {"success": False, "error": f"Unknown position '{position}'. Use: straight, turnout, left, right, flip"}
            cmd()
            return {"success": True, "switch": switch_id, "position": position}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def lock_switch(self, switch_id: str) -> dict:
        """Lock a switch in its current position."""
        self._ensure_connected()
        try:
            sw = self.model.get_sw(switch_id)
            sw.lock()
            return {"success": True, "switch": switch_id, "action": "locked"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def unlock_switch(self, switch_id: str) -> dict:
        """Unlock a switch."""
        self._ensure_connected()
        try:
            sw = self.model.get_sw(switch_id)
            sw.unlock()
            return {"success": True, "switch": switch_id, "action": "unlocked"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Signal control
    # =========================================================================

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

    def next_signal_aspect(self, signal_id: str) -> dict:
        """Cycle to the next signal aspect."""
        self._ensure_connected()
        try:
            sg = self.model.get_sg(signal_id)
            sg.next_aspect()
            return {"success": True, "signal": signal_id, "action": "next_aspect"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_signal_aspect_number(self, signal_id: str, aspect_number: int) -> dict:
        """Set a signal to a specific numbered aspect (0-31)."""
        self._ensure_connected()
        try:
            sg = self.model.get_sg(signal_id)
            sg.aspect_number(aspect_number)
            return {"success": True, "signal": signal_id, "aspect_number": aspect_number}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_signal_mode(self, signal_id: str, mode: str) -> dict:
        """Set signal mode: auto or manual."""
        self._ensure_connected()
        try:
            sg = self.model.get_sg(signal_id)
            if mode == "auto":
                sg.auto()
            elif mode == "manual":
                sg.manual()
            else:
                return {"success": False, "error": f"Unknown mode '{mode}'. Use: auto, manual"}
            return {"success": True, "signal": signal_id, "mode": mode}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def blank_signal(self, signal_id: str) -> dict:
        """Blank a signal (turn off all lights)."""
        self._ensure_connected()
        try:
            sg = self.model.get_sg(signal_id)
            sg.blank()
            return {"success": True, "signal": signal_id, "action": "blanked"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Feedback (sensor) control
    # =========================================================================

    def set_feedback(self, feedback_id: str, state: bool) -> dict:
        """Set a feedback sensor state."""
        self._ensure_connected()
        try:
            fb = self.model.get_fb(feedback_id)
            fb.set(state)
            return {"success": True, "feedback": feedback_id, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def flip_feedback(self, feedback_id: str) -> dict:
        """Toggle a feedback sensor state."""
        self._ensure_connected()
        try:
            fb = self.model.get_fb(feedback_id)
            fb.flip()
            return {"success": True, "feedback": feedback_id, "action": "flipped"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_feedbacks(self) -> list[dict]:
        """List all feedback sensors."""
        self._ensure_connected()
        feedbacks = self.model.get_feedbacks()
        return [{"id": fb_id, "state": fb.state} for fb_id, fb in sorted(feedbacks.items())]

    # =========================================================================
    # Output control
    # =========================================================================

    def set_output(self, output_id: str, state: str) -> dict:
        """Set an output: on, off, or flip."""
        self._ensure_connected()
        try:
            co = self.model.get_co(output_id)
            commands = {"on": co.on, "off": co.off, "flip": co.flip}
            cmd = commands.get(state.lower())
            if cmd is None:
                return {"success": False, "error": f"Unknown state '{state}'. Use: on, off, flip"}
            cmd()
            return {"success": True, "output": output_id, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def activate_output(self, output_id: str, duration_ms: int | None = None) -> dict:
        """Activate an output, optionally for a specific duration in milliseconds."""
        self._ensure_connected()
        try:
            co = self.model.get_co(output_id)
            co.active(duration_ms)
            return {"success": True, "output": output_id, "action": "activated", "duration_ms": duration_ms}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_outputs(self) -> list[dict]:
        """List all outputs."""
        self._ensure_connected()
        outputs = self.model.get_outputs()
        return [{"id": co_id, "state": co.state} for co_id, co in sorted(outputs.items())]

    # =========================================================================
    # Staging yard control
    # =========================================================================

    def stage_action(self, stage_id: str, action: str) -> dict:
        """Perform a staging yard action: compress, expand, open, close, open_exit, close_exit, free."""
        self._ensure_connected()
        try:
            stage = self.model.get_stage(stage_id)
            commands = {
                "compress": stage.compress,
                "expand": stage.expand,
                "open": stage.open,
                "close": stage.close,
                "open_exit": stage.open_exit,
                "close_exit": stage.close_exit,
                "free": stage.free,
            }
            cmd = commands.get(action.lower())
            if cmd is None:
                return {"success": False, "error": f"Unknown action '{action}'. Use: compress, expand, open, close, open_exit, close_exit, free"}
            cmd()
            return {"success": True, "stage": stage_id, "action": action}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_stage_info(self, stage_id: str) -> dict:
        """Get detailed staging yard information."""
        self._ensure_connected()
        try:
            stage = self.model.get_stage(stage_id)
            return {
                "id": stage_id,
                "state": stage.state,
                "exit_state": stage.exitstate,
                "entering": stage.entering,
                "reserved": stage.reserved,
                "total_sections": stage.totalsections,
                "total_length": stage.totallength,
                "section_count": stage.get_section_count(),
                "occupied_sections": [{"id": s.idx, "loco": s.lcid} for s in stage.get_occupied_sections()],
                "free_sections": [s.idx for s in stage.get_free_sections()],
                "locomotives": stage.get_locomotives_in_staging(),
                "exit_locomotive": stage.get_exit_locomotive(),
                "front_locomotive": stage.get_front_locomotive(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_stages(self) -> list[dict]:
        """List all staging yards."""
        self._ensure_connected()
        stages = self.model.get_stages()
        result = []
        for stage_id, stage in sorted(stages.items()):
            result.append(
                {
                    "id": stage_id,
                    "state": stage.state,
                    "sections": stage.get_section_count(),
                    "locomotives": stage.get_locomotives_in_staging(),
                }
            )
        return result

    # =========================================================================
    # Car control
    # =========================================================================

    def set_car_status(self, car_id: str, status: str) -> dict:
        """Set car status: empty, loaded, or maintenance."""
        self._ensure_connected()
        try:
            car = self.model.get_car(car_id)
            commands = {"empty": car.empty, "loaded": car.loaded, "maintenance": car.maintenance}
            cmd = commands.get(status.lower())
            if cmd is None:
                return {"success": False, "error": f"Unknown status '{status}'. Use: empty, loaded, maintenance"}
            cmd()
            return {"success": True, "car": car_id, "status": status}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def assign_car_waybill(self, car_id: str, waybill_id: str) -> dict:
        """Assign a waybill to a car."""
        self._ensure_connected()
        try:
            car = self.model.get_car(car_id)
            car.assign_waybill(waybill_id)
            return {"success": True, "car": car_id, "waybill": waybill_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def reset_car_waybill(self, car_id: str) -> dict:
        """Clear waybill assignment from a car."""
        self._ensure_connected()
        try:
            car = self.model.get_car(car_id)
            car.reset_waybill()
            return {"success": True, "car": car_id, "action": "waybill_cleared"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_car_function(self, car_id: str, function: int, state: bool) -> dict:
        """Set a car decoder function on/off."""
        self._ensure_connected()
        try:
            car = self.model.get_car(car_id)
            car.set_function(function, state)
            return {"success": True, "car": car_id, "function": function, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_cars(self) -> list[dict]:
        """List all cars."""
        self._ensure_connected()
        cars = self.model.get_cars()
        return [{"id": car_id, "status": car.status, "location": car.location, "type": car.type} for car_id, car in sorted(cars.items())]

    # =========================================================================
    # Operator (train) control
    # =========================================================================

    def operator_add_car(self, operator_id: str, car_ids: str) -> dict:
        """Add cars to an operator/train. car_ids is comma-separated."""
        self._ensure_connected()
        try:
            op = self.model.get_operator(operator_id)
            op.add_car(car_ids)
            return {"success": True, "operator": operator_id, "action": "cars_added", "cars": car_ids}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def operator_leave_car(self, operator_id: str, car_ids: str) -> dict:
        """Remove cars from an operator/train. car_ids is comma-separated."""
        self._ensure_connected()
        try:
            op = self.model.get_operator(operator_id)
            op.leave_car(car_ids)
            return {"success": True, "operator": operator_id, "action": "cars_removed", "cars": car_ids}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def operator_empty_car(self, operator_id: str, car_ids: str) -> dict:
        """Mark cars as empty in an operator/train."""
        self._ensure_connected()
        try:
            op = self.model.get_operator(operator_id)
            op.empty_car(car_ids)
            return {"success": True, "operator": operator_id, "action": "cars_emptied", "cars": car_ids}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def operator_load_car(self, operator_id: str, car_ids: str) -> dict:
        """Mark cars as loaded in an operator/train."""
        self._ensure_connected()
        try:
            op = self.model.get_operator(operator_id)
            op.load_car(car_ids)
            return {"success": True, "operator": operator_id, "action": "cars_loaded", "cars": car_ids}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_operators(self) -> list[dict]:
        """List all operators/trains."""
        self._ensure_connected()
        operators = self.model.get_operators()
        return [{"id": op_id, "loco": op.lcid, "cars": op.carids, "location": op.location} for op_id, op in sorted(operators.items())]

    # =========================================================================
    # Schedule control
    # =========================================================================

    def get_schedule(self, schedule_id: str) -> dict:
        """Get schedule details."""
        self._ensure_connected()
        try:
            schedule = self.model.get_schedule(schedule_id)
            entries = [{"block": e.block, "hour": e.hour, "minute": e.minute, "arrival_hour": e.ahour, "arrival_minute": e.aminute} for e in schedule.entries]
            return {"id": schedule_id, "train": schedule.trainid, "entries": entries}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_schedules(self) -> list[dict]:
        """List all schedules."""
        self._ensure_connected()
        schedules = self.model.get_schedules()
        return [{"id": s_id, "train": s.trainid, "entries_count": len(s.entries)} for s_id, s in sorted(schedules.items())]

    def assign_schedule(self, loco_id: str, schedule_id: str) -> dict:
        """Assign a schedule to a locomotive."""
        self._ensure_connected()
        try:
            loco = self.model.get_lc(loco_id)
            loco.use_schedule(schedule_id)
            return {"success": True, "loco": loco_id, "schedule": schedule_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Booster control
    # =========================================================================

    def set_booster(self, booster_id: str, state: str) -> dict:
        """Set booster state: on or off."""
        self._ensure_connected()
        try:
            booster = self.model.get_booster(booster_id)
            if state.lower() == "on":
                booster.on()
            elif state.lower() == "off":
                booster.off()
            else:
                return {"success": False, "error": f"Unknown state '{state}'. Use: on, off"}
            return {"success": True, "booster": booster_id, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Variable control
    # =========================================================================

    def set_variable(self, variable_id: str, value: int | None = None, text: str | None = None) -> dict:
        """Set a Rocrail variable value and/or text."""
        self._ensure_connected()
        try:
            var = self.model.get_variable(variable_id)
            var.set_value(value=value, text=text)
            return {"success": True, "variable": variable_id, "value": value, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def randomize_variable(self, variable_id: str) -> dict:
        """Set a variable to a random value."""
        self._ensure_connected()
        try:
            var = self.model.get_variable(variable_id)
            var.random()
            return {"success": True, "variable": variable_id, "action": "randomized"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Weather control
    # =========================================================================

    def weather_action(self, weather_id: str, action: str) -> dict:
        """Control weather effects: go, stop, setweather, weathertheme."""
        self._ensure_connected()
        try:
            weather = self.model.get_weather(weather_id)
            commands = {
                "go": weather.go,
                "stop": weather.stop,
                "setweather": weather.setweather,
                "weathertheme": weather.weathertheme,
            }
            cmd = commands.get(action.lower())
            if cmd is None:
                return {"success": False, "error": f"Unknown action '{action}'. Use: go, stop, setweather, weathertheme"}
            cmd()
            return {"success": True, "weather": weather_id, "action": action}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Text display control
    # =========================================================================

    def set_text(self, text_id: str, format_str: str) -> dict:
        """Set text display format string."""
        self._ensure_connected()
        try:
            text = self.model.get_text(text_id)
            text.set_format(format_str)
            return {"success": True, "text": text_id, "format": format_str}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Location control
    # =========================================================================

    def location_info(self, location_id: str, svalue: str | None = None) -> dict:
        """Set or query location information."""
        self._ensure_connected()
        try:
            loc = self.model.get_location(location_id)
            loc.info(svalue)
            return {"success": True, "location": location_id, "svalue": svalue}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # System control
    # =========================================================================

    def power_on(self) -> dict:
        """Turn track power on."""
        self._ensure_connected()
        try:
            self._pr.power_on()
            return {"success": True, "action": "power_on"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def power_off(self) -> dict:
        """Turn track power off — immediate hardware-level stop."""
        self._ensure_connected()
        try:
            self._pr.power_off()
            return {"success": True, "action": "power_off"}
        except Exception as e:
            return {"success": False, "error": str(e)}

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

    def system_reset(self) -> dict:
        """Reset the Rocrail system."""
        self._ensure_connected()
        try:
            self._pr.reset()
            return {"success": True, "action": "system_reset"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def system_save(self) -> dict:
        """Save the Rocrail plan to disk."""
        self._ensure_connected()
        try:
            self._pr.save()
            return {"success": True, "action": "plan_saved"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def system_shutdown(self) -> dict:
        """Shutdown the Rocrail server."""
        self._ensure_connected()
        try:
            self._pr.shutdown()
            return {"success": True, "action": "server_shutdown"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_clock(self, hour: int | None = None, minute: int | None = None, divider: int | None = None, freeze: bool | None = None) -> dict:
        """Control the Rocrail fast clock."""
        self._ensure_connected()
        try:
            self._pr.set_clock(hour=hour, minute=minute, divider=divider, freeze=freeze)
            return {"success": True, "action": "clock_set", "hour": hour, "minute": minute, "divider": divider, "freeze": freeze}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_of_day(self) -> dict:
        """Execute Rocrail start-of-day operations."""
        self._ensure_connected()
        try:
            self._pr.start_of_day()
            return {"success": True, "action": "start_of_day"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def end_of_day(self) -> dict:
        """Execute Rocrail end-of-day operations."""
        self._ensure_connected()
        try:
            self._pr.end_of_day()
            return {"success": True, "action": "end_of_day"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fire_event(self, event_id: str) -> dict:
        """Fire a custom Rocrail event."""
        self._ensure_connected()
        try:
            self._pr.fire_event(event_id)
            return {"success": True, "event": event_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_loco_in_block(self, block_id: str) -> dict:
        """Auto-detect and start the locomotive in a block or staging block."""
        self._ensure_connected()
        try:
            result = self._pr.start_locomotive_in_block(block_id)
            return {"success": result, "block": block_id, "action": "start_loco_in_block"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Helpers
    # =========================================================================

    def _ensure_connected(self):
        if self._pr is None:
            raise RuntimeError("Not connected to Rocrail. Call connect() first.")
