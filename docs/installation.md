# OTTO Installation Guide

## Prerequisites

- Python >= 3.12
- Rocrail running with TCP server enabled (default port 8051)
- Claude Desktop (for MCP integration)

## 1. Install PyRocrail

```bash
pip install -e /path/to/py-rocrail/
```

## 2. Install OTTO

```bash
# Core (MCP server only)
pip install -e /path/to/otto/

# With voice support
pip install -e "/path/to/otto/[voice]"
```

## 3. Configure

```bash
cp config/otto.yaml.example config/otto.yaml
# Edit config/otto.yaml with your Rocrail host/port and preferences
```

## 4. Install Voice Models (optional)

```bash
python scripts/install_models.py
```

This downloads kokoro-onnx TTS models to `~/.otto/models/`. The faster-whisper STT model auto-downloads on first use.

## 5. Test Connection

```bash
python scripts/test_connection.py
```

## 6. Configure Claude Desktop

See [Claude Desktop Setup](claude_desktop_setup.md).

## 7. Start

```bash
# MCP server starts automatically via Claude Desktop
# Voice daemon (optional):
otto-voice --config config/otto.yaml
```
