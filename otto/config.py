"""Configuration loading for OTTO."""

import os
from pathlib import Path

import yaml

DEFAULTS = {
    "rocrail": {
        "host": "localhost",
        "port": 8051,
    },
    "voice": {
        "mode": "push_to_talk",
        "key": "f9",
        "whisper_model": "base",
        "tts_voice": "af_heart",
        "tts_speed": 1.0,
    },
    "personality": "swiss_dispatcher",
    "layout": {
        "name": "My Layout",
        "state_refresh_interval": 5,
    },
    "identity": {
        "name": "OTTO",
        "gender": "neutral",
    },
    "monitoring": {
        "enabled": True,
        "timeout_multiplier": 3.0,
        "minimum_timeout": 30,
        "silence_threshold": 120,
        "repeat_alert_interval": 60,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | None = None) -> dict:
    """Load OTTO configuration from YAML, merging with defaults.

    Resolution order for config path:
    1. Explicit `path` argument
    2. OTTO_CONFIG_PATH environment variable
    3. config/otto.yaml in the current directory
    """
    if path is None:
        path = os.environ.get("OTTO_CONFIG_PATH", "config/otto.yaml")

    config_path = Path(path)
    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
    else:
        user_config = {}

    return _deep_merge(DEFAULTS, user_config)
