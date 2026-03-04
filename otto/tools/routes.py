"""Route control tools."""

from otto.tools._registry import mcp, get_client


@mcp.tool()
def set_route(route_id: str) -> dict:
    """Activate/set a route by its ID. Configures all switches along the route."""
    return get_client().set_route(route_id)


@mcp.tool()
def lock_route(route_id: str) -> dict:
    """Lock a route — prevents it from being changed or freed."""
    return get_client().lock_route(route_id)


@mcp.tool()
def unlock_route(route_id: str) -> dict:
    """Unlock a previously locked route."""
    return get_client().unlock_route(route_id)


@mcp.tool()
def free_route(route_id: str) -> dict:
    """Free a route — releases all switches and reservations."""
    return get_client().free_route(route_id)


@mcp.tool()
def test_route(route_id: str) -> dict:
    """Test a route without actually activating it — verifies switch positions."""
    return get_client().test_route(route_id)


@mcp.tool()
def get_route_info(route_id: str) -> dict:
    """Get detailed route information including from/to blocks, state, and switch list."""
    return get_client().get_route_info(route_id)
