#!/usr/bin/env python3
"""Test connection to Rocrail server and print layout summary."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from otto.config import load_config
from otto.rocrail.client import RocrailClient


def main():
    config = load_config()
    rc = config["rocrail"]

    print(f"Connecting to Rocrail at {rc['host']}:{rc['port']}...")
    client = RocrailClient(host=rc["host"], port=rc["port"])
    result = client.connect()

    if not result["success"]:
        print(f"Connection failed: {result['error']}")
        sys.exit(1)

    print(result["message"])

    try:
        locos = client.model.get_locomotives()
        blocks = client.model.get_blocks()
        routes = client.model.get_routes()
        switches = client.model.get_switches()
        signals = client.model.get_signals()

        print("\nLayout Summary:")
        print(f"  Locomotives: {len(locos)}")
        print(f"  Blocks:      {len(blocks)}")
        print(f"  Routes:      {len(routes)}")
        print(f"  Switches:    {len(switches)}")
        print(f"  Signals:     {len(signals)}")

        if locos:
            print("\nLocomotives:")
            for loco_id, loco in locos.items():
                direction = "fwd" if loco.dir else "rev"
                block = getattr(loco, "blockid", "?")
                print(f"  {loco_id}: speed={loco.V} dir={direction} block={block} mode={loco.mode}")

        topology = client.get_topology()
        if topology:
            print(f"\nTopology ({len(topology)} blocks connected):")
            for block_id, neighbors in topology.items():
                print(f"  {block_id} -> {', '.join(neighbors)}")
    finally:
        client.disconnect()
        print("\nDisconnected.")


if __name__ == "__main__":
    main()
