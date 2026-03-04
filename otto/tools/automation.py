"""Automation and schedule tools."""

from otto.tools._registry import mcp, get_client


@mcp.tool()
def start_automation() -> dict:
    """Enable Rocrail automatic mode — trains run their schedules automatically."""
    return get_client().auto_on()


@mcp.tool()
def stop_automation() -> dict:
    """Disable Rocrail automatic mode — trains stop at their next block."""
    return get_client().auto_off()


@mcp.tool()
def get_schedule(schedule_id: str) -> dict:
    """Get details of a schedule including its block stops and timing."""
    return get_client().get_schedule(schedule_id)


@mcp.tool()
def list_schedules() -> list[dict]:
    """List all schedules defined in Rocrail with their IDs and assigned trains."""
    return get_client().list_schedules()


@mcp.tool()
def assign_schedule(loco_id: str, schedule_id: str) -> dict:
    """Assign a Rocrail schedule to a locomotive. Requires auto mode to be active.

    Args:
        loco_id: The locomotive ID
        schedule_id: The schedule ID (use list_schedules to discover available IDs)
    """
    return get_client().assign_schedule(loco_id, schedule_id)
