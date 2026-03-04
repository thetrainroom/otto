"""Monitoring tools — movement tracking, alerts."""

from otto.tools._registry import mcp, get_monitoring


@mcp.tool()
def get_active_movements() -> list[dict]:
    """Get all currently tracked train movements with their on-time/overdue status."""
    monitoring = get_monitoring()
    if monitoring is None:
        return []
    return monitoring.get_active_movements()


@mcp.tool()
def acknowledge_timeout(loco_id: str) -> dict:
    """Acknowledge a timeout alert for a locomotive to silence repeated alerts."""
    monitoring = get_monitoring()
    if monitoring is None:
        return {"success": False, "error": "Monitoring not enabled"}
    return monitoring.acknowledge_timeout(loco_id)


@mcp.tool()
def report_loco_recovered(loco_id: str, block_id: str) -> dict:
    """Report that a timed-out locomotive has been recovered at a specific block."""
    monitoring = get_monitoring()
    if monitoring is None:
        return {"success": False, "error": "Monitoring not enabled"}
    return monitoring.report_recovered(loco_id, block_id)


@mcp.tool()
def get_alerts() -> list[dict]:
    """Get any pending monitoring alerts (timeouts, silence warnings)."""
    monitoring = get_monitoring()
    if monitoring is None:
        return []
    return monitoring.get_pending_alerts()
