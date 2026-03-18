"""Extra tools — boosters, variables, weather, text, locations."""

from otto.tools._registry import mcp, get_client

# --- Boosters ---


@mcp.tool()
def set_booster(booster_id: str, state: str) -> dict:
    """Control a power district booster.

    Args:
        booster_id: The booster ID
        state: One of: on, off
    """
    return get_client().set_booster(booster_id, state)


# --- Variables ---


@mcp.tool()
def set_variable(variable_id: str, value: int | None = None, text: str | None = None) -> dict:
    """Set a Rocrail variable's numeric value and/or text."""
    return get_client().set_variable(variable_id, value=value, text=text)


@mcp.tool()
def randomize_variable(variable_id: str) -> dict:
    """Set a Rocrail variable to a random value within its configured range."""
    return get_client().randomize_variable(variable_id)


# --- Weather ---


@mcp.tool()
def weather_action(weather_id: str, action: str) -> dict:
    """Control weather effects on the layout.

    Args:
        weather_id: The weather ID
        action: One of: go, stop, setweather, weathertheme
    """
    return get_client().weather_action(weather_id, action)


# --- Text displays ---


@mcp.tool()
def set_text(text_id: str, format_str: str) -> dict:
    """Set the content of a text display element on the layout."""
    return get_client().set_text(text_id, format_str)


# --- Locations ---


@mcp.tool()
def location_info(location_id: str, svalue: str | None = None) -> dict:
    """Set or query location information."""
    return get_client().location_info(location_id, svalue)


@mcp.tool()
def list_locations() -> list[dict]:
    """List all locations with their blocks and occupancy settings."""
    return get_client().list_locations()


@mcp.tool()
def set_location_minocc(location_id: str, minocc: int) -> dict:
    """Set the minimum occupancy for a location (minimum trains that must remain).

    Args:
        location_id: The location ID
        minocc: Minimum number of trains that must remain in the location
    """
    return get_client().set_location_minocc(location_id, minocc)


@mcp.tool()
def set_location_maxocc(location_id: str, maxocc: int) -> dict:
    """Set the maximum occupancy for a location (maximum trains allowed).

    Args:
        location_id: The location ID
        maxocc: Maximum number of trains allowed in the location
    """
    return get_client().set_location_maxocc(location_id, maxocc)
