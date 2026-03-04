"""Locomotive control tools."""

import logging

from otto.tools._registry import mcp, get_client, get_monitoring

logger = logging.getLogger(__name__)


@mcp.tool()
def set_loco_speed(loco_id: str, speed: int) -> dict:
    """Set a locomotive's speed (0-100). Use set_loco_direction to change direction."""
    return get_client().set_loco_speed(loco_id, speed)


@mcp.tool()
def set_loco_direction(loco_id: str, direction: str) -> dict:
    """Set locomotive direction.

    Args:
        loco_id: The locomotive ID
        direction: One of: forward, reverse, toggle
    """
    return get_client().set_loco_direction(loco_id, direction)


@mcp.tool()
def go_loco_forward(loco_id: str, speed: int | None = None) -> dict:
    """Set locomotive direction to forward and optionally set speed in one command."""
    return get_client().go_loco_forward(loco_id, speed)


@mcp.tool()
def go_loco_reverse(loco_id: str, speed: int | None = None) -> dict:
    """Set locomotive direction to reverse and optionally set speed in one command."""
    return get_client().go_loco_reverse(loco_id, speed)


@mcp.tool()
def set_loco_function(loco_id: str, function: int, state: bool) -> dict:
    """Control a decoder function (lights, sound, horn, etc.)

    Args:
        loco_id: The locomotive ID
        function: Function number — 0 = headlights, 1-28 = F1-F28
        state: True = on, False = off
    """
    return get_client().set_loco_function(loco_id, function, state)


@mcp.tool()
def stop_loco(loco_id: str) -> dict:
    """Emergency stop a specific locomotive immediately."""
    return get_client().stop_loco(loco_id)


@mcp.tool()
def soft_stop_loco(loco_id: str) -> dict:
    """Graceful stop — locomotive stops at the next block in auto mode instead of emergency stopping."""
    return get_client().soft_stop_loco(loco_id)


@mcp.tool()
def stop_all() -> dict:
    """Emergency stop ALL trains on the layout immediately."""
    return get_client().emergency_stop_all()


@mcp.tool()
def place_loco(loco_id: str, block_id: str) -> dict:
    """Place a locomotive on a specific block. Used for initial placement or recovery after derailment."""
    return get_client().place_loco(loco_id, block_id)


@mcp.tool()
def dispatch_loco(loco_id: str, block_id: str | None = None, speed: str = "mid") -> dict:
    """Dispatch a locomotive for automatic operation, optionally to a specific destination block.

    Args:
        loco_id: The locomotive ID to dispatch
        block_id: Optional destination block ID
        speed: Speed setting (reserved for future)
    """
    client = get_client()
    result = client.dispatch_loco(loco_id, block_id, speed)

    monitoring = get_monitoring()
    if result.get("success") and monitoring and block_id:
        try:
            loco = client.model.get_lc(loco_id)
            from_block = getattr(loco, "blockid", "")
            if from_block:
                monitoring.track_dispatch(loco_id, from_block, block_id)
        except Exception:
            logger.debug("Could not track dispatch for monitoring")

    return result


@mcp.tool()
def assign_loco(loco_id: str) -> dict:
    """Assign a locomotive to Rocrail automatic control. Rocrail manages the loco according to its schedule or auto plan."""
    return get_client().assign_loco(loco_id)


@mcp.tool()
def release_loco(loco_id: str) -> dict:
    """Release a locomotive from automatic control. Loco stops gracefully and returns to manual mode."""
    return get_client().release_loco(loco_id)


@mcp.tool()
def soft_reset_loco(loco_id: str) -> dict:
    """Soft reset a locomotive — clears internal state without full reset."""
    return get_client().soft_reset_loco(loco_id)


@mcp.tool()
def set_loco_class(loco_id: str, class_name: str | None = None) -> dict:
    """Set or clear a locomotive's class. Pass None to clear."""
    return get_client().set_loco_class(loco_id, class_name)


@mcp.tool()
def assign_train_to_loco(loco_id: str, train_id: str) -> dict:
    """Assign a train/operator to a locomotive."""
    return get_client().assign_train_to_loco(loco_id, train_id)


@mcp.tool()
def release_train_from_loco(loco_id: str) -> dict:
    """Release the assigned train/operator from a locomotive."""
    return get_client().release_train_from_loco(loco_id)


@mcp.tool()
def set_loco_goto_block(loco_id: str, block_id: str) -> dict:
    """Set destination block for a locomotive without dispatching it."""
    return get_client().set_loco_goto_block(loco_id, block_id)
