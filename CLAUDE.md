# OTTO — AI Voice Controller for Model Railways

## What is OTTO?
OTTO exposes Rocrail layout control as MCP tools for Claude Desktop, with an optional voice pipeline (push-to-talk STT + TTS).

## Architecture
- **PyRocrail** (`pyrocrail`) handles all Rocrail TCP communication — OTTO wraps it, no raw TCP
- **MCP Server** (`otto/mcp_server.py`) — FastMCP with `@mcp.tool()` decorators, stdio transport
- **Voice Daemon** (`otto/voice_daemon.py`) — separate process, push-to-talk with pynput, types into Claude Desktop via clipboard paste

## Key Files
- `otto/mcp_server.py` — MCP entry point, all tool definitions
- `otto/rocrail/client.py` — PyRocrail wrapper with clean dict-returning API
- `otto/layout.py` — topology graph builder, human-readable state summaries
- `otto/personality.py` — response style definitions, system prompt builder
- `otto/monitoring.py` — movement tracking, timing database, anomaly detection
- `otto/config.py` — YAML config with defaults
- `otto/voice/speaker.py` — kokoro-onnx TTS
- `otto/voice/transcriber.py` — faster-whisper STT
- `otto/voice/speech_queue.py` — file-based TTS bridge between MCP and voice daemon

## Dependencies
- PyRocrail: installed separately as `pip install -e /path/to/py-rocrail/`
- Core: `mcp`, `pyyaml`, `thefuzz`
- Voice (optional): `faster-whisper`, `kokoro-onnx`, `sounddevice`, `soundfile`, `pyautogui`, `pynput`, `numpy`, `pyperclip`

## Running
- MCP server: `otto` (configured in Claude Desktop's `claude_desktop_config.json`)
- Voice daemon: `otto-voice --config config/otto.yaml`
- Test connection: `python scripts/test_connection.py`

## Config
Copy `config/otto.yaml.example` to `config/otto.yaml`. Key settings:
- `rocrail.host/port` — Rocrail server address
- `personality` — response style (swiss_dispatcher, enthusiastic, passive_aggressive, hal9000)
- `identity.gender` — neutral="OTTO", female="Ottoline", male="Otto"
- `monitoring.enabled` — movement tracking and timeout alerts
