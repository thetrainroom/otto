"""Output control tools — lights, accessories, etc."""

from otto.tools._registry import mcp, get_client


@mcp.tool()
def set_output(output_id: str, state: str) -> dict:
    """Control an output (lights, accessories, etc.)

    Args:
        output_id: The output ID
        state: One of: on, off, flip
    """
    return get_client().set_output(output_id, state)


@mcp.tool()
def activate_output(output_id: str, duration_ms: int | None = None) -> dict:
    """Activate an output, optionally for a specific duration in milliseconds."""
    return get_client().activate_output(output_id, duration_ms)


@mcp.tool()
def list_outputs() -> list[dict]:
    """List all outputs with their current state."""
    return get_client().list_outputs()
