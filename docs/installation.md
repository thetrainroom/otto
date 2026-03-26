# OTTO Installation & Setup Guide

## Prerequisites

- **Python 3.12+**
- **Rocrail** running with TCP server enabled (default port 8051)
- **An MCP-compatible AI client** — OTTO uses the standard MCP stdio transport, so it works with any client that supports MCP, including:
  - [Claude Desktop](https://claude.ai/download)
  - [ChatGPT Desktop](https://openai.com/chatgpt/desktop/)
  - [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLI)
  - [Gemini CLI](https://github.com/google-gemini/gemini-cli)
  - [Cursor](https://www.cursor.com/)
  - [VS Code](https://code.visualstudio.com/) (with Copilot)
  - [Windsurf](https://windsurf.com/)

---

## Step 1: Install OTTO

```bash
# Clone the repo
git clone git@github.com:thetrainroom/otto.git
cd otto

# Install core (MCP server only)
python3.12 -m pip install -e .

# Or with voice support (push-to-talk + TTS)
python3.12 -m pip install -e ".[voice]"
```

This creates two commands:
- `otto` — the MCP server
- `otto-voice` — the voice daemon (only with `[voice]` extras)

Find where they were installed:

```bash
which otto
# Typical output: /Users/<you>/Library/Python/3.12/bin/otto
```

## Step 2: Create Configuration

```bash
cp config/otto.yaml.example config/otto.yaml
```

Edit `config/otto.yaml`:

```yaml
rocrail:
  host: "192.168.1.100"     # IP of your Rocrail server
  port: 8051                # Rocrail TCP port (default 8051)

voice:
  mode: "push_to_talk"      # push_to_talk | disabled
  key: "f9"                 # hotkey for push-to-talk

personality: "swiss_dispatcher"  # swiss_dispatcher | enthusiastic | passive_aggressive | hal9000

layout:
  name: "My Layout"

identity:
  name: "OTTO"
  gender: "neutral"          # neutral | female | male
```

The only required change is `rocrail.host` — set it to the IP of the machine running Rocrail. Everything else has sensible defaults.

You can also set the config path via environment variable:

```bash
export OTTO_CONFIG_PATH=/path/to/otto.yaml
```

## Step 3: Test the Connection

Make sure Rocrail is running, then:

```bash
python3.12 scripts/test_connection.py
```

You should see a layout summary with locomotive count, block count, routes, etc. If it fails, check that:
- Rocrail is running and its TCP server is enabled
- The host IP and port are correct in `otto.yaml`
- No firewall is blocking TCP port 8051

## Step 4: Configure Your MCP Client

OTTO works with any MCP-compatible client. Below are setup instructions for the most common ones.

### Claude Desktop

Edit the config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add OTTO to the `mcpServers` section:

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

Replace:
- `/Users/<you>/Library/Python/3.12/bin/otto` with the output of `which otto`
- `192.168.1.100` with your Rocrail server's IP address

### Alternative: Use config file instead of CLI args

```json
{
  "mcpServers": {
    "otto": {
      "command": "/Users/<you>/Library/Python/3.12/bin/otto",
      "args": ["--config", "/path/to/otto/config/otto.yaml"]
    }
  }
}
```

### ChatGPT Desktop

Go to **Settings → MCP Servers → Add Server**, then enter:

- **Name:** otto
- **Command:** the output of `which otto`
- **Arguments:** `--host 192.168.1.100` (your Rocrail IP)

### Other clients

For any MCP client, the key information is:
- **Command:** the path from `which otto`
- **Arguments:** `--host <rocrail-ip>` or `--config /path/to/otto.yaml`
- **Transport:** stdio (the default)

Refer to your client's documentation for how to add MCP servers.

### All CLI options

| Argument | Description |
|----------|-------------|
| `--host` | Rocrail host IP (overrides config file) |
| `--port` | Rocrail TCP port (overrides config file) |
| `--config` | Path to `otto.yaml` config file |

## Step 5: Restart Your Client

Restart your MCP client to pick up the new server configuration. For Claude Desktop, fully quit (Cmd+Q on macOS) and relaunch.

## Step 6: Verify It Works

In your MCP client, type:

> What locomotives are on the layout?

The AI should call the `get_layout_state` tool and return real data from your Rocrail server — locomotive names, which blocks they're in, their speeds, etc.

Try a few more commands:

> Show me the layout topology

> Stop all trains

> Set the speed of BR 89 to 30

---

## Voice Setup (Optional)

### Install Voice Models

The TTS system (kokoro-onnx) needs model files:

```bash
python3.12 scripts/install_models.py
```

This downloads models to `~/.otto/models/`. The STT model (faster-whisper) downloads automatically on first use.

### Start the Voice Daemon

In a separate terminal:

```bash
otto-voice --config config/otto.yaml
```

Or with verbose logging:

```bash
otto-voice --config config/otto.yaml -v
```

### Using Voice

1. Make sure Claude Desktop is in focus
2. Press and hold **F9** (or your configured hotkey)
3. Speak your command
4. Release F9
5. Your speech is transcribed and typed into Claude Desktop
6. Claude processes it and responds
7. If Claude calls the `speak` tool, you'll hear the response through your speakers

### Emergency Voice Commands

Two words work instantly without going through Claude:

| Say | Effect |
|-----|--------|
| **"STOP"** | Cuts track power immediately |
| **"GO"** | Restores track power |

These are handled directly by the voice daemon for minimum latency (~200ms).

---

## Troubleshooting

### "Not connected to Rocrail"

- Check Rocrail is running and TCP server is enabled
- Verify host/port in config or CLI args
- Test with: `python3.12 scripts/test_connection.py`

### Claude Desktop doesn't show OTTO tools

- Check `claude_desktop_config.json` syntax (valid JSON?)
- Verify the path to `otto` is correct (`which otto`)
- Fully restart Claude Desktop (Cmd+Q, relaunch)
- Check Claude Desktop logs for MCP startup errors

### Voice daemon can't connect

- The voice daemon connects to Rocrail independently for emergency commands
- Ensure `otto.yaml` has the correct Rocrail host/port
- If Rocrail is unreachable, voice still works for transcription — only emergency commands are disabled

### "kokoro model files not found"

Run `python3.12 scripts/install_models.py` to download TTS models.

---

## Updating

Since OTTO is installed as an editable package (`pip install -e .`), any code changes take effect immediately. Just restart Claude Desktop to pick up changes in the MCP server.

```bash
cd /path/to/otto
git pull
# No reinstall needed — restart Claude Desktop
```

If `pyproject.toml` dependencies changed:

```bash
python3.12 -m pip install -e .
```
