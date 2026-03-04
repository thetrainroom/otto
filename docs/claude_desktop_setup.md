# Claude Desktop Setup

## MCP Server Configuration

Add OTTO to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "otto": {
      "command": "otto",
      "env": {
        "OTTO_CONFIG_PATH": "/path/to/otto/config/otto.yaml"
      }
    }
  }
}
```

If `otto` is not on your PATH, use the full path:

```json
{
  "mcpServers": {
    "otto": {
      "command": "/path/to/venv/bin/otto",
      "env": {
        "OTTO_CONFIG_PATH": "/path/to/otto/config/otto.yaml"
      }
    }
  }
}
```

## Restart Claude Desktop

After editing the config, fully quit and relaunch Claude Desktop.

## Verify

Type in Claude Desktop:

> What locomotives are on the layout?

Claude should use the `get_layout_state` tool and return real data from your Rocrail server.

## Using with Voice

1. Start the voice daemon in a terminal: `otto-voice`
2. Press F9 to talk, release to send
3. Your speech is transcribed and typed into Claude Desktop
4. Claude's responses can be spoken aloud via the `speak` tool
