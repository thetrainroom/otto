"""Layout topology manager — builds navigable graph and generates human-readable state summaries."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from otto.rocrail.client import RocrailClient

logger = logging.getLogger(__name__)


class LayoutManager:
    """Builds topology graph from PyRocrail model and generates layout context for system prompts."""

    def __init__(self, client: RocrailClient, layout_name: str = "My Layout"):
        self.client = client
        self.layout_name = layout_name

    def build_topology(self) -> dict:
        """Build full topology from routes, blocks, and their connections.

        Returns a dict with blocks, routes, and adjacency graph.
        """
        model = self.client.model
        routes = model.get_routes()
        blocks = model.get_blocks()

        adjacency: dict[str, set[str]] = {}
        route_info = {}

        for route_id, route in routes.items():
            if route.bka and route.bkb:
                adjacency.setdefault(route.bka, set()).add(route.bkb)
                adjacency.setdefault(route.bkb, set()).add(route.bka)

                switch_cmds = []
                for sw_cmd in route.switches:
                    switch_cmds.append({"id": sw_cmd.id, "cmd": sw_cmd.cmd})

                route_info[route_id] = {
                    "from": route.bka,
                    "to": route.bkb,
                    "status": route.status,
                    "free": route.is_free(),
                    "switches": switch_cmds,
                }

        block_info = {}
        for block_id, block in blocks.items():
            block_info[block_id] = {
                "occupied": block.occ,
                "reserved": block.reserved,
                "loco": block.locid,
                "state": str(block.state),
            }
            # Ensure all blocks appear in adjacency
            adjacency.setdefault(block_id, set())

        return {
            "blocks": block_info,
            "routes": route_info,
            "adjacency": {k: sorted(v) for k, v in sorted(adjacency.items())},
        }

    def get_state_summary(self) -> str:
        """Generate a human-readable layout state summary for Claude's system prompt."""
        model = self.client.model
        lines = [f"LAYOUT: {self.layout_name}", ""]

        # Blocks
        blocks = model.get_blocks()
        if blocks:
            lines.append("BLOCKS:")
            for block_id, block in sorted(blocks.items()):
                status_parts = []
                if block.occ:
                    status_parts.append("OCCUPIED")
                if block.reserved:
                    status_parts.append("RESERVED")
                if block.locid:
                    status_parts.append(f"loco={block.locid}")
                status = ", ".join(status_parts) if status_parts else "free"
                lines.append(f"  {block_id}: {status}")
            lines.append("")

        # Routes
        routes = model.get_routes()
        if routes:
            lines.append("ROUTES:")
            for route_id, route in sorted(routes.items()):
                free_str = "FREE" if route.is_free() else route.status.upper()
                lines.append(f"  {route_id}: {route.bka} -> {route.bkb} [{free_str}]")
            lines.append("")

        # Locomotives
        locos = model.get_locomotives()
        if locos:
            lines.append("LOCOMOTIVES:")
            for loco_id, loco in sorted(locos.items()):
                direction = "fwd" if loco.dir else "rev"
                block = getattr(loco, "blockid", "")
                dest = getattr(loco, "destblockid", "")
                parts = [f"speed={loco.V}", f"dir={direction}", f"mode={loco.mode}"]
                if block:
                    parts.append(f"block={block}")
                if dest:
                    parts.append(f"dest={dest}")
                lines.append(f"  {loco_id}: {', '.join(parts)}")
            lines.append("")

        # Signals
        signals = model.get_signals()
        if signals:
            lines.append("SIGNALS:")
            for sig_id, sig in sorted(signals.items()):
                lines.append(f"  {sig_id}: {sig.state}")
            lines.append("")

        # Switches
        switches = model.get_switches()
        if switches:
            lines.append("SWITCHES:")
            for sw_id, sw in sorted(switches.items()):
                lines.append(f"  {sw_id}: {sw.state}")
            lines.append("")

        # Topology summary
        topology = self.client.get_topology()
        if topology:
            lines.append("TOPOLOGY:")
            for block_id, neighbors in topology.items():
                lines.append(f"  {block_id} connects to: {', '.join(neighbors)}")
            lines.append("")

        return "\n".join(lines)
