# Rocrail Setup for OTTO

## TCP Server

OTTO connects to Rocrail via its built-in TCP server. This is enabled by default.

### Verify TCP Server

1. Open Rocrail
2. Go to **File > Rocrail Properties > Controller**
3. Ensure the TCP port is set (default: **8051**)
4. The host should be accessible from the machine running OTTO

### Network Access

If OTTO runs on a different machine than Rocrail:
- Ensure the Rocrail host is reachable over the network
- Check firewall settings allow TCP connections on port 8051
- Update `config/otto.yaml` with the correct host IP

### Test Connection

```bash
python scripts/test_connection.py
```

This will connect, print a layout summary (locomotive count, block count, topology), and disconnect.

## Layout Requirements

OTTO works best with layouts that have:
- **Named blocks** — OTTO refers to blocks by their Rocrail IDs
- **Defined routes** — routes between blocks enable topology awareness and navigation
- **Locomotive IDs** — used for fuzzy matching when you say locomotive names

No special Rocrail configuration is needed beyond the standard TCP server.
