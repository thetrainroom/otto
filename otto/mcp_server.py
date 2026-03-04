"""OTTO MCP server — exposes Rocrail layout control as MCP tools for Claude Desktop."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from otto.config import load_config
from otto.layout import LayoutManager
from otto.monitoring import MonitoringSystem
from otto.personality import get_system_prompt
from otto.rocrail.client import RocrailClient
from otto.voice.speech_queue import enqueue as enqueue_speech

logger = logging.getLogger(__name__)

mcp = FastMCP("otto")

# Global state — initialized in main()
_client: RocrailClient | None = None
_layout: LayoutManager | None = None
_monitoring: MonitoringSystem | None = None
_config: dict = {}


def _get_client() -> RocrailClient:
    if _client is None or not _client.connected:
        raise RuntimeError("Not connected to Rocrail")
    return _client


# ============================================================
# Layout Query Tools
# ============================================================


@mcp.tool()
def get_layout_state() -> dict:
    """Get the full layout state including all locomotives, blocks, routes, switches, signals, and feedbacks."""
    return _get_client().get_layout_state()


@mcp.tool()
def get_topology() -> dict:
    """Get the layout topology as an adjacency graph showing which blocks connect to which other blocks."""
    return _layout.build_topology()


@mcp.tool()
def find_loco(query: str) -> dict:
    """Find a locomotive by name using fuzzy matching. Returns the best match with details."""
    return _get_client().find_loco(query)


@mcp.tool()
def find_route(from_block: str, to_block: str) -> dict:
    """Find available routes between two blocks."""
    return _get_client().find_route_between(from_block, to_block)


# ============================================================
# Control Tools
# ============================================================


@mcp.tool()
def set_route(route_id: str) -> dict:
    """Activate/set a route by its ID. This configures all switches along the route."""
    return _get_client().set_route(route_id)


@mcp.tool()
def dispatch_loco(loco_id: str, block_id: str | None = None, speed: str = "mid") -> dict:
    """Dispatch a locomotive for automatic operation, optionally to a specific destination block.

    Args:
        loco_id: The locomotive ID to dispatch
        block_id: Optional destination block ID
        speed: Speed setting (not used currently, reserved for future)
    """
    client = _get_client()
    result = client.dispatch_loco(loco_id, block_id, speed)

    # Track the movement if monitoring is active and we have from/to blocks
    if result.get("success") and _monitoring and block_id:
        try:
            loco = client.model.get_lc(loco_id)
            from_block = getattr(loco, "blockid", "")
            if from_block:
                _monitoring.track_dispatch(loco_id, from_block, block_id)
        except Exception:
            logger.debug("Could not track dispatch for monitoring")

    return result


@mcp.tool()
def set_loco_speed(loco_id: str, speed: int) -> dict:
    """Set a locomotive's speed (0-100)."""
    return _get_client().set_loco_speed(loco_id, speed)


@mcp.tool()
def stop_loco(loco_id: str) -> dict:
    """Emergency stop a specific locomotive immediately."""
    return _get_client().stop_loco(loco_id)


@mcp.tool()
def stop_all() -> dict:
    """Emergency stop ALL trains on the layout immediately."""
    return _get_client().emergency_stop_all()


@mcp.tool()
def set_switch(switch_id: str, position: str) -> dict:
    """Set a switch/turnout position.

    Args:
        switch_id: The switch ID
        position: One of: straight, turnout, left, right
    """
    return _get_client().set_switch(switch_id, position)


@mcp.tool()
def set_signal(signal_id: str, aspect: str) -> dict:
    """Set a signal aspect.

    Args:
        signal_id: The signal ID
        aspect: One of: red, green, yellow, white
    """
    return _get_client().set_signal(signal_id, aspect)


# ============================================================
# Automation Tools
# ============================================================


@mcp.tool()
def start_automation() -> dict:
    """Enable Rocrail automatic mode — trains run their schedules automatically."""
    return _get_client().auto_on()


@mcp.tool()
def stop_automation() -> dict:
    """Disable Rocrail automatic mode — trains stop at their next block."""
    return _get_client().auto_off()


@mcp.tool()
def get_schedule(schedule_id: str) -> dict:
    """Get details of a schedule including its block stops and timing."""
    return _get_client().get_schedule(schedule_id)


# ============================================================
# Monitoring Tools
# ============================================================


@mcp.tool()
def get_active_movements() -> list[dict]:
    """Get all currently tracked train movements with their on-time/overdue status."""
    if _monitoring is None:
        return []
    return _monitoring.get_active_movements()


@mcp.tool()
def acknowledge_timeout(loco_id: str) -> dict:
    """Acknowledge a timeout alert for a locomotive to silence repeated alerts."""
    if _monitoring is None:
        return {"success": False, "error": "Monitoring not enabled"}
    return _monitoring.acknowledge_timeout(loco_id)


@mcp.tool()
def report_loco_recovered(loco_id: str, block_id: str) -> dict:
    """Report that a timed-out locomotive has been recovered at a specific block."""
    if _monitoring is None:
        return {"success": False, "error": "Monitoring not enabled"}
    return _monitoring.report_recovered(loco_id, block_id)


@mcp.tool()
def get_alerts() -> list[dict]:
    """Get any pending monitoring alerts (timeouts, silence warnings)."""
    if _monitoring is None:
        return []
    return _monitoring.get_pending_alerts()


# ============================================================
# Voice Tool
# ============================================================


@mcp.tool()
def speak(text: str) -> dict:
    """Speak text aloud via the voice daemon's TTS system. The text will be queued for speaking."""
    enqueue_speech(text)
    return {"spoken": text}


# ============================================================
# Resource
# ============================================================


@mcp.resource("otto://layout/context")
def layout_context() -> str:
    """Full layout context including personality system prompt and current state."""
    if _layout is None:
        return "OTTO is not connected to Rocrail."

    layout_summary = _layout.get_state_summary()
    return get_system_prompt(
        _config.get("personality", "swiss_dispatcher"),
        _config.get("identity", {}),
        layout_summary,
    )


# ============================================================
# Main
# ============================================================


def main():
    global _client, _layout, _monitoring, _config

    import argparse

    parser = argparse.ArgumentParser(description="OTTO MCP server")
    parser.add_argument("--host", help="Rocrail host (overrides config)")
    parser.add_argument("--port", type=int, help="Rocrail port (overrides config)")
    parser.add_argument("--config", help="Path to otto.yaml config file")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    _config = load_config(args.config)
    rc = _config["rocrail"]

    # CLI args override config file
    host = args.host or rc["host"]
    port = args.port or rc["port"]

    # Create and connect Rocrail client
    _client = RocrailClient(host=host, port=port)
    result = _client.connect()
    if result["success"]:
        logger.info("Connected to Rocrail: %s", result["message"])
    else:
        logger.warning("Could not connect to Rocrail: %s — tools will return errors", result.get("error"))

    # Create layout manager
    _layout = LayoutManager(_client, layout_name=_config["layout"]["name"])

    # Create monitoring system
    _monitoring = MonitoringSystem(_client, _config)
    _monitoring.start()

    # Run MCP server
    logger.info("Starting OTTO MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
