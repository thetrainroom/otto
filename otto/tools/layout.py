"""Layout query tools — state, topology, search."""

from otto.tools._registry import mcp, get_client, get_layout


@mcp.tool()
def get_layout_state() -> dict:
    """Get the full layout state including all locomotives, blocks, routes, switches, signals, and feedbacks."""
    return get_client().get_layout_state()


@mcp.tool()
def get_topology() -> dict:
    """Get the layout topology as an adjacency graph showing which blocks connect to which other blocks."""
    return get_layout().build_topology()


@mcp.tool()
def find_loco(query: str) -> dict:
    """Find a locomotive by name using fuzzy matching. Returns the best match with details."""
    return get_client().find_loco(query)


@mcp.tool()
def find_route(from_block: str, to_block: str) -> dict:
    """Find available routes between two blocks."""
    return get_client().find_route_between(from_block, to_block)
