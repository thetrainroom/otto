# Claude Desktop Setup

## Quick Setup

1. Find where `otto` is installed:

```bash
which otto
```

2. Edit Claude Desktop's config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "otto": {
      "command": "/Users/<you>/Library/Python/3.12/bin/otto",
      "args": ["--host", "192.168.1.100"]
    }
  }
}
```

Replace the command path with the output of `which otto` and the host with your Rocrail server's IP.

3. Fully quit Claude Desktop (Cmd+Q) and relaunch.

4. Test by typing: **"What locomotives are on the layout?"**

## Configuration Options

### Option A: Host/port via CLI args

```json
{
  "mcpServers": {
    "otto": {
      "command": "/path/to/otto",
      "args": ["--host", "192.168.1.100", "--port", "8051"]
    }
  }
}
```

### Option B: Config file

```json
{
  "mcpServers": {
    "otto": {
      "command": "/path/to/otto",
      "args": ["--config", "/path/to/otto/config/otto.yaml"]
    }
  }
}
```

### Option C: Environment variable

```json
{
  "mcpServers": {
    "otto": {
      "command": "/path/to/otto",
      "env": {
        "OTTO_CONFIG_PATH": "/path/to/otto/config/otto.yaml"
      }
    }
  }
}
```

## What You Get

Once connected, Claude Desktop has access to 87 tools for full layout control:

- **Ask about the layout** — "What's happening on the layout?" / "Where is the BR 89?"
- **Control locomotives** — "Set BR 89 speed to 40" / "Stop all trains"
- **Manage routes** — "Set route from block 1 to block 5"
- **Control signals & switches** — "Set signal S1 to green" / "Flip switch W3"
- **Automation** — "Start automation" / "Assign schedule Express to BR 89"
- **System** — "Power off" / "Save the layout"
- **Voice** — "Speak: Train arriving at platform 2" (if voice daemon is running)

## Checking Logs

If something isn't working, check the MCP server logs. On macOS, Claude Desktop writes logs to:

```
~/Library/Logs/Claude/
```

Look for lines containing `otto` to see connection status and errors.

## Adding Alongside Other MCP Servers

OTTO can coexist with other MCP servers:

```json
{
  "mcpServers": {
    "otto": {
      "command": "/path/to/otto",
      "args": ["--host", "192.168.1.100"]
    },
    "other-server": {
      "command": "/path/to/other"
    }
  }
}
```
