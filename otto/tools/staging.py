"""Staging yard control tools."""

from otto.tools._registry import mcp, get_client


@mcp.tool()
def stage_action(stage_id: str, action: str) -> dict:
    """Perform a staging yard action.

    Args:
        stage_id: The staging yard ID
        action: One of: compress, expand, open, close, open_exit, close_exit, free
            - compress: advance trains to fill gaps
            - expand: activate train in exit section for departure
            - open/close: allow or prevent train entry
            - open_exit/close_exit: allow or prevent train departure
            - free: unreserve the staging block
    """
    return get_client().stage_action(stage_id, action)


@mcp.tool()
def get_stage_info(stage_id: str) -> dict:
    """Get detailed staging yard information including sections, locomotives, and availability."""
    return get_client().get_stage_info(stage_id)


@mcp.tool()
def list_stages() -> list[dict]:
    """List all staging yards with their state and locomotive counts."""
    return get_client().list_stages()
