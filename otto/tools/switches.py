"""Switch control tools."""

from otto.tools._registry import mcp, get_client


@mcp.tool()
def set_switch(switch_id: str, position: str) -> dict:
    """Set a switch/turnout position.

    Args:
        switch_id: The switch ID
        position: One of: straight, turnout, left, right, flip
    """
    return get_client().set_switch(switch_id, position)


@mcp.tool()
def lock_switch(switch_id: str) -> dict:
    """Lock a switch in its current position — prevents it from being changed."""
    return get_client().lock_switch(switch_id)


@mcp.tool()
def unlock_switch(switch_id: str) -> dict:
    """Unlock a previously locked switch."""
    return get_client().unlock_switch(switch_id)
