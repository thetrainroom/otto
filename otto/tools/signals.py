"""Signal control tools."""

from otto.tools._registry import mcp, get_client


@mcp.tool()
def set_signal(signal_id: str, aspect: str) -> dict:
    """Set a signal aspect.

    Args:
        signal_id: The signal ID
        aspect: One of: red, green, yellow, white
    """
    return get_client().set_signal(signal_id, aspect)


@mcp.tool()
def next_signal_aspect(signal_id: str) -> dict:
    """Cycle a signal to its next aspect."""
    return get_client().next_signal_aspect(signal_id)


@mcp.tool()
def set_signal_aspect_number(signal_id: str, aspect_number: int) -> dict:
    """Set a signal to a specific numbered aspect (0-31) for signals with more than 4 aspects."""
    return get_client().set_signal_aspect_number(signal_id, aspect_number)


@mcp.tool()
def set_signal_mode(signal_id: str, mode: str) -> dict:
    """Set signal mode.

    Args:
        signal_id: The signal ID
        mode: One of: auto, manual
    """
    return get_client().set_signal_mode(signal_id, mode)


@mcp.tool()
def blank_signal(signal_id: str) -> dict:
    """Blank a signal — turns off all lights."""
    return get_client().blank_signal(signal_id)
