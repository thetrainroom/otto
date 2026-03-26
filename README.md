# OTTO — AI Controller for Model Railways

OTTO connects your AI assistant to a [Rocrail](https://wiki.rocrail.net/) model railway layout via [MCP](https://modelcontextprotocol.io/) (Model Context Protocol). Ask questions, control locomotives, set routes, flip switches — all through natural language.

```
┌──────────────────────┐    stdio (MCP)    ┌────────────────────┐
│   AI Client          │◄─────────────────►│   OTTO MCP Server  │
│   (Claude, ChatGPT,  │                   │   (otto)           │
│    Gemini, etc.)      │                   └────────┬───────────┘
└──────────────────────┘                            │
                                                    │ PyRocrail TCP
                                                    │
                                            ┌───────▼────────────┐
                                            │   Rocrail Server   │
                                            │   (any machine)    │
                                            └────────┬───────────┘
                                                     │ DCC / hardware
                                                     ▼
                                                [ Model Railway ]
```

## What Can It Do?

OTTO exposes **87 MCP tools** covering full layout control:

- **Layout** — state overview, topology, block occupancy
- **Locomotives** — speed, direction, functions (lights, sound, horn)
- **Routes** — set, list, and manage routes between blocks
- **Switches & Signals** — flip turnouts, set signal aspects
- **Automation** — start/stop auto mode, assign schedules
- **Monitoring** — movement tracking, timing, anomaly detection
- **System** — power on/off, save layout, emergency stop

## Quick Start

```bash
# Install
git clone git@github.com:thetrainroom/otto.git
cd otto
python3.12 -m pip install -e .

# Configure
cp config/otto.yaml.example config/otto.yaml
# Edit config/otto.yaml — set rocrail.host to your Rocrail server's IP

# Test connection
python3.12 scripts/test_connection.py
```

Then add OTTO to your MCP client. For **Claude Desktop**, edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "otto": {
      "command": "/path/to/otto",
      "args": ["--host", "192.168.1.100"]
    }
  }
}
```

Replace `/path/to/otto` with the output of `which otto` and the IP with your Rocrail server's address.

See the full [Installation Guide](docs/installation.md) for detailed instructions, including setup for ChatGPT Desktop and other MCP clients.

## Compatible MCP Clients

OTTO uses standard MCP stdio transport and works with any compatible client:

- [Claude Desktop](https://claude.ai/download)
- [ChatGPT Desktop](https://openai.com/chatgpt/desktop/)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLI)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- [Cursor](https://www.cursor.com/)
- [VS Code](https://code.visualstudio.com/) (with Copilot)
- [Windsurf](https://windsurf.com/)

## Voice Control (Optional)

OTTO includes an optional voice daemon with push-to-talk speech input and text-to-speech responses. All voice processing runs locally (no cloud APIs).

```bash
# Install with voice support
python3.12 -m pip install -e ".[voice]"

# Download TTS models
python3.12 scripts/install_models.py

# Start the voice daemon
otto-voice --config config/otto.yaml
```

See the [Installation Guide](docs/installation.md#voice-setup-optional) for details.

## Documentation

- [Installation & Setup](docs/installation.md) — full install guide with multi-client setup
- [How It Works](docs/how-it-works.md) — architecture, tool reference, and internals
- [Rocrail Setup](docs/rocrail_setup.md) — configuring Rocrail for OTTO
- [Claude Desktop Setup](docs/claude_desktop_setup.md) — Claude Desktop-specific config

## Requirements

- Python 3.12+
- [Rocrail](https://wiki.rocrail.net/) with TCP server enabled
- An MCP-compatible AI client

## License

[MIT](LICENSE)
