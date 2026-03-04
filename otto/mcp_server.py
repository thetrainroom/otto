"""OTTO MCP server — exposes Rocrail layout control as MCP tools for Claude Desktop."""

from __future__ import annotations

import logging

from otto.config import load_config
from otto.layout import LayoutManager
from otto.monitoring import MonitoringSystem
from otto.personality import get_system_prompt
from otto.rocrail.client import RocrailClient
from otto.tools._registry import mcp
import otto.tools._registry as _registry

# Import all tool modules — this registers their @mcp.tool() decorators
import otto.tools.layout  # noqa: F401
import otto.tools.locomotive  # noqa: F401
import otto.tools.blocks  # noqa: F401
import otto.tools.routes  # noqa: F401
import otto.tools.switches  # noqa: F401
import otto.tools.signals  # noqa: F401
import otto.tools.feedback  # noqa: F401
import otto.tools.outputs  # noqa: F401
import otto.tools.staging  # noqa: F401
import otto.tools.cars  # noqa: F401
import otto.tools.automation  # noqa: F401
import otto.tools.system  # noqa: F401
import otto.tools.extras  # noqa: F401
import otto.tools.monitoring  # noqa: F401
import otto.tools.voice  # noqa: F401

logger = logging.getLogger(__name__)


# ============================================================
# Resource
# ============================================================


@mcp.resource("otto://layout/context")
def layout_context() -> str:
    """Full layout context including personality system prompt and current state."""
    if _registry._layout is None:
        return "OTTO is not connected to Rocrail."

    layout_summary = _registry._layout.get_state_summary()
    return get_system_prompt(
        _registry._config.get("personality", "swiss_dispatcher"),
        _registry._config.get("identity", {}),
        layout_summary,
    )


# ============================================================
# Main
# ============================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="OTTO MCP server")
    parser.add_argument("--host", help="Rocrail host (overrides config)")
    parser.add_argument("--port", type=int, help="Rocrail port (overrides config)")
    parser.add_argument("--config", help="Path to otto.yaml config file")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = load_config(args.config)
    rc = config["rocrail"]

    # CLI args override config file
    host = args.host or rc["host"]
    port = args.port or rc["port"]

    # Set global state in registry
    _registry._config = config
    _registry._client = RocrailClient(host=host, port=port)

    result = _registry._client.connect()
    if result["success"]:
        logger.info("Connected to Rocrail: %s", result["message"])
    else:
        logger.warning("Could not connect to Rocrail: %s — tools will return errors", result.get("error"))

    _registry._layout = LayoutManager(_registry._client, layout_name=config["layout"]["name"])

    _registry._monitoring = MonitoringSystem(_registry._client, config)
    _registry._monitoring.start()

    # Run MCP server
    logger.info("Starting OTTO MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
