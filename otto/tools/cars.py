"""Car and operator (train) control tools — freight operations."""

from otto.tools._registry import mcp, get_client


# --- Cars ---


@mcp.tool()
def set_car_status(car_id: str, status: str) -> dict:
    """Set a car's status.

    Args:
        car_id: The car ID
        status: One of: empty, loaded, maintenance
    """
    return get_client().set_car_status(car_id, status)


@mcp.tool()
def assign_car_waybill(car_id: str, waybill_id: str) -> dict:
    """Assign a waybill to a car for freight operations."""
    return get_client().assign_car_waybill(car_id, waybill_id)


@mcp.tool()
def reset_car_waybill(car_id: str) -> dict:
    """Clear waybill assignment from a car."""
    return get_client().reset_car_waybill(car_id)


@mcp.tool()
def set_car_function(car_id: str, function: int, state: bool) -> dict:
    """Control a car decoder function (interior lights, etc.)

    Args:
        car_id: The car ID
        function: Function number (0-28)
        state: True = on, False = off
    """
    return get_client().set_car_function(car_id, function, state)


@mcp.tool()
def list_cars() -> list[dict]:
    """List all cars with their status, location, and type."""
    return get_client().list_cars()


# --- Operators / Trains ---


@mcp.tool()
def operator_add_car(operator_id: str, car_ids: str) -> dict:
    """Add cars to a train/operator. car_ids is comma-separated."""
    return get_client().operator_add_car(operator_id, car_ids)


@mcp.tool()
def operator_leave_car(operator_id: str, car_ids: str) -> dict:
    """Remove cars from a train/operator. car_ids is comma-separated."""
    return get_client().operator_leave_car(operator_id, car_ids)


@mcp.tool()
def operator_empty_car(operator_id: str, car_ids: str) -> dict:
    """Mark cars as empty in a train/operator."""
    return get_client().operator_empty_car(operator_id, car_ids)


@mcp.tool()
def operator_load_car(operator_id: str, car_ids: str) -> dict:
    """Mark cars as loaded in a train/operator."""
    return get_client().operator_load_car(operator_id, car_ids)


@mcp.tool()
def list_operators() -> list[dict]:
    """List all operators/trains with their locomotive, cars, and location."""
    return get_client().list_operators()
