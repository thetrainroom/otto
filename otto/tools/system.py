"""System control tools — power, clock, save, reset, events."""

from otto.tools._registry import mcp, get_client


# --- Power ---


@mcp.tool()
def power_on() -> dict:
    """Turn track power on. Restores power after a power_off or emergency stop."""
    return get_client().power_on()


@mcp.tool()
def power_off() -> dict:
    """Turn track power off immediately. Hardware-level stop — the most reliable way to stop everything."""
    return get_client().power_off()


# --- Clock ---


@mcp.tool()
def set_clock(hour: int | None = None, minute: int | None = None, divider: int | None = None, freeze: bool | None = None) -> dict:
    """Control the Rocrail fast clock.

    Args:
        hour: Set clock hour (0-23)
        minute: Set clock minute (0-59)
        divider: Clock speed multiplier (e.g. 10 = 10x real time)
        freeze: True to pause the clock, False to resume
    """
    return get_client().set_clock(hour=hour, minute=minute, divider=divider, freeze=freeze)


# --- System operations ---


@mcp.tool()
def system_save() -> dict:
    """Save the Rocrail plan to disk."""
    return get_client().system_save()


@mcp.tool()
def system_reset() -> dict:
    """Reset the Rocrail system."""
    return get_client().system_reset()


@mcp.tool()
def system_shutdown() -> dict:
    """Shutdown the Rocrail server process. WARNING: This stops Rocrail entirely."""
    return get_client().system_shutdown()


@mcp.tool()
def start_of_day() -> dict:
    """Execute Rocrail start-of-day operations — initializes layout for a new session."""
    return get_client().start_of_day()


@mcp.tool()
def end_of_day() -> dict:
    """Execute Rocrail end-of-day operations — parks trains and prepares for shutdown."""
    return get_client().end_of_day()


@mcp.tool()
def fire_event(event_id: str) -> dict:
    """Fire a custom Rocrail event by its ID."""
    return get_client().fire_event(event_id)


@mcp.tool()
def start_loco_in_block(block_id: str) -> dict:
    """Auto-detect and start the locomotive in a block or staging block."""
    return get_client().start_loco_in_block(block_id)
