"""Feedback sensor tools."""

from otto.tools._registry import mcp, get_client


@mcp.tool()
def set_feedback(feedback_id: str, state: bool) -> dict:
    """Set a feedback sensor state (True = active, False = inactive)."""
    return get_client().set_feedback(feedback_id, state)


@mcp.tool()
def flip_feedback(feedback_id: str) -> dict:
    """Toggle a feedback sensor state."""
    return get_client().flip_feedback(feedback_id)


@mcp.tool()
def list_feedbacks() -> list[dict]:
    """List all feedback sensors with their current state."""
    return get_client().list_feedbacks()
