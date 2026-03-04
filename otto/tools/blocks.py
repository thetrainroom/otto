"""Block control tools."""

from otto.tools._registry import mcp, get_client


@mcp.tool()
def set_block_state(block_id: str, state: str) -> dict:
    """Open or close a block for routing.

    Args:
        block_id: The block ID
        state: One of: open, closed, free
    """
    return get_client().set_block_state(block_id, state)


@mcp.tool()
def free_block_override(block_id: str) -> dict:
    """Force free a stuck block, overriding any reservations or locks."""
    return get_client().free_block_override(block_id)


@mcp.tool()
def stop_block(block_id: str) -> dict:
    """Stop the locomotive currently occupying a block."""
    return get_client().stop_block(block_id)


@mcp.tool()
def accept_block_ident(block_id: str) -> dict:
    """Accept locomotive identification in a block."""
    return get_client().accept_block_ident(block_id)


@mcp.tool()
def get_block_info(block_id: str) -> dict:
    """Get detailed information about a specific block including occupancy, reservation, and state."""
    return get_client().get_block_info(block_id)
