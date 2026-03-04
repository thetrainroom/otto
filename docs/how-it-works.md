# OTTO — How It Works

OTTO is an AI voice controller for model railways. It connects Claude Desktop to a Rocrail layout server, exposing full layout control through 87 MCP tools. An optional voice daemon adds push-to-talk speech input and text-to-speech output.

---

## Architecture Overview

```
┌──────────────────────┐    stdio (MCP)    ┌────────────────────┐
│   Claude Desktop     │◄─────────────────►│   OTTO MCP Server  │
│   (LLM + UI)         │                   │   (otto)           │
└──────────────────────┘                   └────────┬───────────┘
        ▲                                           │
        │ clipboard paste                           │ PyRocrail TCP
        │                                           │
┌───────┴──────────────┐                   ┌────────▼───────────┐
│   OTTO Voice Daemon  │                   │   Rocrail Server   │
│   (otto-voice)       │                   │   (any machine)    │
└──────────────────────┘                   └────────────────────┘
        │                                           │
        │ mic + speaker                             │ DCC / hardware
        ▼                                           ▼
   [ Microphone ]                             [ Model Railway ]
   [ Speakers   ]
```

There are three independent processes:

| Process | Command | Role |
|---------|---------|------|
| **Claude Desktop** | GUI app | LLM interface — the brain. Calls MCP tools. |
| **OTTO MCP Server** | `otto` | Bridge between Claude and Rocrail. Runs as an MCP stdio subprocess of Claude Desktop. |
| **OTTO Voice Daemon** | `otto-voice` | Optional. Push-to-talk mic input + TTS speech output. Runs standalone in a terminal. |

Rocrail runs on any machine on the network (typically a dedicated Linux box near the layout). OTTO connects to it over TCP.

---

## Core Components

### 1. MCP Server (`otto/mcp_server.py`)

The main entry point. Claude Desktop launches this as a subprocess using stdio transport.

**Startup sequence:**
1. Parse CLI args (`--host`, `--port`, `--config`)
2. Load configuration from `otto.yaml`
3. Create a `RocrailClient` and connect to Rocrail over TCP
4. Create a `LayoutManager` for topology and state summaries
5. Create a `MonitoringSystem` and start its background thread
6. Import all tool submodules (registers `@mcp.tool()` decorators)
7. Run the FastMCP server on stdio

**Configuration in Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
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

### 2. Rocrail Client (`otto/rocrail/client.py`)

Wraps the [PyRocrail](https://github.com/thetrainroom/py-rocrail) library with a clean API for MCP tools. PyRocrail handles all TCP communication, XML parsing, object models, and state change callbacks. OTTO never deals with raw TCP or Rocrail XML.

**Key patterns:**
- Every method returns a serializable `dict` (e.g. `{"success": True, "loco": "BR89", "speed": 50}`)
- A `_ensure_connected()` guard on every method raises a clear error if not connected
- Enum values from PyRocrail are converted to strings for JSON serialization
- Fuzzy locomotive name matching via `thefuzz` — say "the BR89" and it finds `BR 89`

**What PyRocrail provides:**
- `PyRocrail(host, port)` — TCP connection lifecycle
- `model.export_state()` — full layout state as a dict
- `model.get_locomotives()`, `get_blocks()`, `get_routes()`, `get_switches()`, `get_signals()` — typed objects
- `model.change_callback` — called on every state change from Rocrail
- Object methods: `loco.set_speed()`, `loco.dispatch()`, `route.set()`, `switch.straight()`, `signal.red()`, etc.

### 3. Tool Submodules (`otto/tools/`)

87 MCP tools organized into 15 files by category:

| File | Tools | What they control |
|------|------:|-------------------|
| `layout.py` | 4 | Layout state, topology, fuzzy loco search, route finder |
| `locomotive.py` | 17 | Speed, direction, functions, dispatch, assign, release, place, goto |
| `blocks.py` | 5 | Block state, free override, stop, accept ident, info |
| `routes.py` | 6 | Set, lock, unlock, free, test, info |
| `switches.py` | 3 | Set position (straight/turnout/left/right/flip), lock, unlock |
| `signals.py` | 5 | Set aspect, next aspect, aspect number, mode, blank |
| `feedback.py` | 3 | Set, flip, list feedback sensors |
| `outputs.py` | 3 | Set, activate (with duration), list outputs |
| `staging.py` | 3 | Stage action, info, list staging yards |
| `cars.py` | 5 | Car status, waybill assign/reset, function, list |
| `cars.py` | 5 | Operator add/leave/empty/load car, list operators |
| `automation.py` | 5 | Start/stop auto mode, get/list/assign schedules |
| `system.py` | 10 | Power on/off, clock, save, reset, shutdown, start/end of day, events |
| `extras.py` | 6 | Boosters, variables, weather, text displays, locations |
| `monitoring.py` | 4 | Active movements, acknowledge timeout, report recovered, alerts |
| `voice.py` | 1 | Speak text via TTS |

All tools use a shared registry (`otto/tools/_registry.py`) to access the `RocrailClient`, `LayoutManager`, `MonitoringSystem`, and config. The registry is populated once during startup by `mcp_server.py`.

**How tool registration works:**
Each tool file defines functions with `@mcp.tool()`. When `mcp_server.py` imports the module (e.g. `import otto.tools.locomotive`), the decorators fire and register each function with FastMCP. No manual registration needed.

### 4. Layout Manager (`otto/layout.py`)

Builds a navigable topology graph from Rocrail's route definitions and generates human-readable state summaries.

- `build_topology()` — Returns `{"blocks": {...}, "routes": {...}, "adjacency": {"block1": ["block2", "block3"]}}` by iterating all routes and extracting their from/to blocks
- `get_state_summary()` — Generates a text summary listing all blocks (with occupancy), routes (with status), locomotives (with speed/direction/position), signals, switches, and topology connections

The state summary is embedded in the system prompt via the `otto://layout/context` MCP resource, giving Claude full awareness of the layout.

### 5. Monitoring System (`otto/monitoring.py`)

Tracks train movements and detects anomalies. Three classes:

**`MovementTracker`** — Tracks dispatched locomotives:
- When a loco is dispatched (via the `dispatch_loco` tool), a movement is recorded with from-block, to-block, and expected duration
- When the loco arrives at its destination (detected via PyRocrail's change callback), the movement completes

**`TimingDatabase`** — Learns segment timing from observations:
- Persists to `~/.otto/timing.json`
- Records actual travel times for each block-to-block segment
- Keeps a rolling window of 20 samples per segment
- Estimates expected duration as `mean + 3 * stddev` (once >= 3 samples exist)
- Cold start: falls back to the configured `minimum_timeout` (default 30s)

**`MonitoringSystem`** — Background thread (checks every 2s):
- **Overdue detection**: If a loco exceeds `expected_time * timeout_multiplier`, an alert is generated
- **Silence detection**: If no block changes occur for `silence_threshold` seconds (default 120), an alert is generated
- Hooks into PyRocrail's `model.change_callback` to automatically complete movements when locos arrive

Alerts are exposed via the `get_alerts` MCP tool. Claude can acknowledge timeouts or report recovered locos.

### 6. Personality System (`otto/personality.py`)

Four personality options that change how Claude responds:

| Personality | Style |
|-------------|-------|
| `swiss_dispatcher` (default) | Dry, precise, under 15 words. "BR 89 dispatched to block 3." |
| `enthusiastic` | Excited railfan. "BR 89 is on its way to block 3! How exciting!" |
| `passive_aggressive` | Sarcastic but helpful. "BR 89 dispatched. Not the route I'd have chosen, but sure." |
| `hal9000` | Calm, unsettling. "I have dispatched BR 89. I will be monitoring its progress closely." |

Each personality includes alert templates for timeout, silence, and recovery messages.

The identity system supports gender variants: `neutral` = "OTTO", `female` = "Ottoline", `male` = "Otto".

The system prompt combines: personality rules + identity + full layout state summary.

---

## Voice Pipeline

The voice system is optional and runs as a separate process from the MCP server. It has two directions:

### Speech Input (STT)

```
Microphone → sounddevice → faster-whisper → text → clipboard paste → Claude Desktop
```

1. User presses and holds the hotkey (default: F9)
2. `pynput` keyboard listener detects the press, starts recording via `sounddevice`
3. User releases the key, recording stops
4. Audio is transcribed by `faster-whisper` (runs locally, no API calls)
5. Transcribed text is pasted into Claude Desktop via the system clipboard (`osascript` Cmd+V on macOS)
6. Claude processes the text and calls MCP tools as needed

### Speech Output (TTS)

```
Claude → speak() MCP tool → ~/.otto/speech_queue.txt → Voice Daemon → kokoro-onnx → sounddevice → Speakers
```

1. Claude calls the `speak` tool with text to say
2. The MCP server appends the text to `~/.otto/speech_queue.txt`
3. The voice daemon polls this file every 0.5s
4. Each line is synthesized by `kokoro-onnx` (local TTS, no API calls) and played through speakers
5. The file is cleared after reading

The file-based queue bridges the two separate processes (MCP server and voice daemon) without needing IPC.

### Emergency Voice Commands

Two words bypass Claude entirely for safety-critical speed:

| Word | Action | Latency |
|------|--------|---------|
| **"STOP"** | `power_off()` — cuts track power | ~200ms (transcription only) |
| **"GO"** | `power_on()` — restores track power | ~200ms (transcription only) |

These are detected by simple keyword matching in the voice daemon after transcription. The daemon maintains its own direct TCP connection to Rocrail for this purpose — no round-trip through Claude.

### Voice Components

| File | Class | Purpose |
|------|-------|---------|
| `otto/voice/transcriber.py` | `Transcriber` | Wraps faster-whisper. Lazy-loads model on first use. Records audio via sounddevice. |
| `otto/voice/speaker.py` | `Speaker` | Wraps kokoro-onnx. Lazy-loads model from `~/.otto/models/`. Synthesizes and plays audio. |
| `otto/voice/speech_queue.py` | — | File-based queue at `~/.otto/speech_queue.txt`. `enqueue()` and `dequeue_all()` functions. |
| `otto/voice_daemon.py` | `VoiceDaemon` | Main loop: keyboard listener + recording thread + speech queue poller. |

---

## Configuration

All config lives in `otto.yaml` (default path: `config/otto.yaml`, overridable via `OTTO_CONFIG_PATH` env var or `--config` CLI arg).

```yaml
rocrail:
  host: "192.168.1.100"     # Rocrail server address
  port: 8051                # Rocrail TCP port

voice:
  mode: "push_to_talk"      # push_to_talk | disabled
  key: "f9"                 # hotkey for push-to-talk
  whisper_model: "base"     # tiny | base | small | medium | large-v3
  tts_voice: "af_heart"     # kokoro voice ID
  tts_speed: 1.0

personality: "swiss_dispatcher"  # swiss_dispatcher | enthusiastic | passive_aggressive | hal9000

layout:
  name: "My Layout"
  state_refresh_interval: 5

identity:
  name: "OTTO"
  gender: "neutral"          # neutral | female | male

monitoring:
  enabled: true
  timeout_multiplier: 3.0    # alert if elapsed > expected * multiplier
  minimum_timeout: 30        # cold-start fallback (seconds)
  silence_threshold: 120     # alert after this many seconds without block changes
  repeat_alert_interval: 60  # seconds between repeated timeout alerts
```

`load_config()` in `otto/config.py` deep-merges the YAML file over built-in defaults, so any key can be omitted.

---

## Data Flow Example

Here is what happens when a user says "Send the BR 89 to block 5":

1. **Voice daemon** records audio, transcribes to text: "Send the BR 89 to block 5"
2. **Voice daemon** checks emergency commands — not a match, so pastes text into Claude Desktop
3. **Claude Desktop** receives the text, adds the system prompt (with personality + layout state), sends to Claude
4. **Claude** decides to call the `dispatch_loco` tool with `loco_id="BR 89"` and `block_id="block5"`
5. **MCP server** receives the tool call, routes it to `otto/tools/locomotive.py:dispatch_loco()`
6. **Tool function** calls `get_client().dispatch_loco("BR 89", "block5")`
7. **RocrailClient** fuzzy-matches "BR 89" to the actual loco ID, calls PyRocrail's `loco.gotoblock("block5")` then `loco.dispatch()`
8. **PyRocrail** sends the XML commands over TCP to Rocrail
9. **Rocrail** executes: sets route, throws switches, sets signals, starts the locomotive
10. **MonitoringSystem** records the movement with the learned expected duration
11. **RocrailClient** returns `{"success": True, "loco": "BR 89", ...}`
12. **Claude** formats the result: "BR 89 dispatched to block 5." and calls the `speak` tool
13. **MCP server** writes "BR 89 dispatched to block 5." to `~/.otto/speech_queue.txt`
14. **Voice daemon** picks up the line, synthesizes speech, plays through speakers
15. **Meanwhile**, the monitoring system watches for the loco to arrive at block 5 via PyRocrail's change callback
16. If the loco doesn't arrive within the expected time, an alert is generated for Claude to report

---

## MCP Resource

OTTO exposes one MCP resource:

**`otto://layout/context`** — Returns the full system prompt combining:
- Personality style and response rules
- Identity (name and gender)
- Current layout state summary (all blocks, routes, locomotives, signals, switches, and topology)

Claude Desktop can attach this resource to conversations to give Claude full layout awareness.

---

## File Structure

```
otto/
├── otto/
│   ├── __init__.py              # Package init, version string
│   ├── config.py                # YAML config loading with defaults
│   ├── mcp_server.py            # Main entry point, startup, MCP resource
│   ├── layout.py                # Topology graph builder, state summary
│   ├── personality.py           # 4 personalities, system prompt builder
│   ├── monitoring.py            # Movement tracker, timing DB, anomaly detection
│   ├── voice_daemon.py          # Push-to-talk daemon (separate process)
│   ├── rocrail/
│   │   ├── __init__.py
│   │   └── client.py            # PyRocrail wrapper (~80 methods)
│   ├── tools/
│   │   ├── _registry.py         # Shared MCP instance + accessor functions
│   │   ├── layout.py            # 4 layout query tools
│   │   ├── locomotive.py        # 17 locomotive control tools
│   │   ├── blocks.py            # 5 block tools
│   │   ├── routes.py            # 6 route tools
│   │   ├── switches.py          # 3 switch tools
│   │   ├── signals.py           # 5 signal tools
│   │   ├── feedback.py          # 3 feedback sensor tools
│   │   ├── outputs.py           # 3 output tools
│   │   ├── staging.py           # 3 staging yard tools
│   │   ├── cars.py              # 10 car + operator tools
│   │   ├── automation.py        # 5 automation/schedule tools
│   │   ├── system.py            # 10 system tools
│   │   ├── extras.py            # 6 extra tools (boosters, weather, etc.)
│   │   ├── monitoring.py        # 4 monitoring tools
│   │   └── voice.py             # 1 speak tool
│   └── voice/
│       ├── __init__.py
│       ├── speaker.py           # kokoro-onnx TTS wrapper
│       ├── transcriber.py       # faster-whisper STT wrapper
│       └── speech_queue.py      # File-based TTS bridge
├── config/
│   └── otto.yaml.example        # Configuration template
├── scripts/
│   ├── test_connection.py       # Rocrail connection test
│   └── install_models.py        # TTS model downloader
├── tests/                       # 96 pytest tests
├── docs/
│   ├── how-it-works.md          # This document
│   ├── installation.md          # Install guide
│   ├── claude_desktop_setup.md  # Claude Desktop config
│   └── rocrail_setup.md         # Rocrail prerequisites
├── pyproject.toml               # Package config, dependencies
├── CLAUDE.md                    # Repo guidance for Claude Code sessions
└── .github/workflows/lint.yml   # CI: ruff + black
```

---

## Dependencies

### Core (always installed)
- **PyRocrail** — Rocrail TCP client library (installed separately from local path or PyPI)
- **mcp** — Model Context Protocol SDK (FastMCP)
- **pyyaml** — Configuration file parsing
- **thefuzz** — Fuzzy string matching for locomotive names

### Voice (optional, `pip install 'otto[voice]'`)
- **faster-whisper** — Speech-to-text (Whisper model, runs locally)
- **kokoro-onnx** — Text-to-speech (runs locally, models in `~/.otto/models/`)
- **sounddevice** — Audio recording and playback
- **soundfile** — Audio file I/O
- **pynput** — Keyboard listener for push-to-talk hotkey
- **pyperclip** — Clipboard access for pasting into Claude Desktop
- **numpy** — Audio array processing

No cloud APIs are used for voice — everything runs locally.

---

## Complete Tool Reference

### Layout Query (4 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_layout_state` | — | Full layout state: all locos, blocks, routes, switches, signals, feedbacks |
| `get_topology` | — | Adjacency graph: which blocks connect to which |
| `find_loco` | `query` | Fuzzy match a locomotive by name |
| `find_route` | `from_block`, `to_block` | Find routes between two blocks |

### Locomotive Control (17 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `set_loco_speed` | `loco_id`, `speed` (0-100) | Set speed |
| `set_loco_direction` | `loco_id`, `direction` | Set direction (true=forward) |
| `go_loco_forward` | `loco_id`, `speed` (optional) | Direction forward + optional speed |
| `go_loco_reverse` | `loco_id`, `speed` (optional) | Direction reverse + optional speed |
| `set_loco_function` | `loco_id`, `function`, `state` | Control decoder function (lights, sound, horn) |
| `stop_loco` | `loco_id` | Emergency stop one loco |
| `soft_stop_loco` | `loco_id` | Graceful stop at next block |
| `stop_all` | — | Emergency stop ALL trains |
| `place_loco` | `loco_id`, `block_id` | Place loco on a block (initial placement / recovery) |
| `dispatch_loco` | `loco_id`, `block_id` (opt), `speed` (opt) | Dispatch for automatic operation |
| `assign_loco` | `loco_id` | Assign to Rocrail auto control |
| `release_loco` | `loco_id` | Release from auto control |
| `soft_reset_loco` | `loco_id` | Soft reset internal state |
| `set_loco_class` | `loco_id`, `class_name` | Set/clear locomotive class |
| `assign_train_to_loco` | `loco_id`, `train_id` | Assign train/operator |
| `release_train_from_loco` | `loco_id` | Release train/operator |
| `set_loco_goto_block` | `loco_id`, `block_id` | Set destination without dispatching |

### Block Control (5 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `set_block_state` | `block_id`, `state` | Open or close a block |
| `free_block_override` | `block_id` | Force free a stuck block |
| `stop_block` | `block_id` | Stop loco in this block |
| `accept_block_ident` | `block_id` | Accept loco identification |
| `get_block_info` | `block_id` | Detailed block information |

### Route Control (6 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `set_route` | `route_id` | Activate route (configures switches) |
| `lock_route` | `route_id` | Lock route (prevent changes) |
| `unlock_route` | `route_id` | Unlock route |
| `free_route` | `route_id` | Free route (release switches) |
| `test_route` | `route_id` | Test without activating |
| `get_route_info` | `route_id` | Route details: blocks, switches, state |

### Switch Control (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `set_switch` | `switch_id`, `position` | Set position: straight/turnout/left/right/flip |
| `lock_switch` | `switch_id` | Lock in current position |
| `unlock_switch` | `switch_id` | Unlock |

### Signal Control (5 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `set_signal` | `signal_id`, `aspect` | Set aspect: red/green/yellow/white |
| `next_signal_aspect` | `signal_id` | Cycle to next aspect |
| `set_signal_aspect_number` | `signal_id`, `aspect_number` | Set numbered aspect (0-31) |
| `set_signal_mode` | `signal_id`, `mode` | Set signal mode |
| `blank_signal` | `signal_id` | Turn off all lights |

### Feedback Sensors (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `set_feedback` | `feedback_id`, `state` | Set sensor state |
| `flip_feedback` | `feedback_id` | Toggle sensor |
| `list_feedbacks` | — | List all sensors with state |

### Outputs (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `set_output` | `output_id`, `state` | Control output (lights, accessories) |
| `activate_output` | `output_id`, `duration_ms` (opt) | Activate, optionally for a duration |
| `list_outputs` | — | List all outputs |

### Staging Yards (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `stage_action` | `stage_id`, `action` | Staging yard action |
| `get_stage_info` | `stage_id` | Staging yard details |
| `list_stages` | — | List all staging yards |

### Cars (5 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `set_car_status` | `car_id`, `status` | Set car status |
| `assign_car_waybill` | `car_id`, `waybill_id` | Assign waybill for freight ops |
| `reset_car_waybill` | `car_id` | Clear waybill |
| `set_car_function` | `car_id`, `function`, `state` | Control car decoder function |
| `list_cars` | — | List all cars |

### Operators/Trains (5 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `operator_add_car` | `operator_id`, `car_ids` | Add cars to train |
| `operator_leave_car` | `operator_id`, `car_ids` | Remove cars from train |
| `operator_empty_car` | `operator_id`, `car_ids` | Mark cars empty |
| `operator_load_car` | `operator_id`, `car_ids` | Mark cars loaded |
| `list_operators` | — | List all operators/trains |

### Automation (5 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `start_automation` | — | Enable Rocrail auto mode |
| `stop_automation` | — | Disable auto mode (trains stop at next block) |
| `get_schedule` | `schedule_id` | Schedule details |
| `list_schedules` | — | List all schedules |
| `assign_schedule` | `loco_id`, `schedule_id` | Assign schedule to loco |

### System (10 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `power_on` | — | Track power on |
| `power_off` | — | Track power off (hardware-level stop) |
| `set_clock` | `hour`, `minute`, `divider` (opt), `freeze` (opt) | Control fast clock |
| `system_save` | — | Save Rocrail plan to disk |
| `system_reset` | — | Reset Rocrail system |
| `system_shutdown` | — | Shutdown Rocrail server |
| `start_of_day` | — | Initialize layout for new session |
| `end_of_day` | — | Park trains, prepare for shutdown |
| `fire_event` | `event_id` | Fire a custom Rocrail event |
| `start_loco_in_block` | `block_id` | Auto-detect and start loco in block |

### Extras (6 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `set_booster` | `booster_id`, `state` | Control power district booster |
| `set_variable` | `variable_id`, `value` (opt), `text` (opt) | Set Rocrail variable |
| `randomize_variable` | `variable_id` | Random value within configured range |
| `weather_action` | `weather_id`, `action` | Control weather effects |
| `set_text` | `text_id`, `format_str` | Set text display content |
| `location_info` | `location_id`, `svalue` (opt) | Set/query location info |

### Monitoring (4 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_active_movements` | — | All tracked movements with on-time/overdue status |
| `acknowledge_timeout` | `loco_id` | Silence repeated timeout alerts |
| `report_loco_recovered` | `loco_id`, `block_id` | Clear timeout, update state |
| `get_alerts` | — | Pending monitoring alerts |

### Voice (1 tool)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `speak` | `text` | Queue text for TTS playback |
