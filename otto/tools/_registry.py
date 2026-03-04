"""Shared MCP instance and accessor functions for all tool modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from otto.layout import LayoutManager
    from otto.monitoring import MonitoringSystem
    from otto.rocrail.client import RocrailClient

mcp = FastMCP("otto")

# Global state — set by mcp_server.main()
_client: RocrailClient | None = None
_layout: LayoutManager | None = None
_monitoring: MonitoringSystem | None = None
_config: dict = {}


def get_client() -> RocrailClient:
    if _client is None or not _client.connected:
        raise RuntimeError("Not connected to Rocrail")
    return _client


def get_layout() -> LayoutManager:
    if _layout is None:
        raise RuntimeError("Layout manager not initialized")
    return _layout


def get_monitoring() -> MonitoringSystem | None:
    return _monitoring


def get_config() -> dict:
    return _config
