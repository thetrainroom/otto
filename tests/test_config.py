"""Tests for otto.config."""

import os
import tempfile

import yaml

from otto.config import load_config, DEFAULTS, _deep_merge


class TestDeepMerge:
    def test_flat(self):
        assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_override(self):
        assert _deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_nested(self):
        base = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 3, "c": 4}}
        result = _deep_merge(base, override)
        assert result == {"x": {"a": 1, "b": 3, "c": 4}}

    def test_no_mutation(self):
        base = {"a": 1}
        override = {"b": 2}
        _deep_merge(base, override)
        assert base == {"a": 1}


class TestLoadConfig:
    def test_defaults_when_no_file(self):
        config = load_config("/nonexistent/path/otto.yaml")
        assert config == DEFAULTS

    def test_default_values(self):
        config = load_config("/nonexistent/path/otto.yaml")
        assert config["rocrail"]["host"] == "localhost"
        assert config["rocrail"]["port"] == 8051
        assert config["personality"] == "swiss_dispatcher"
        assert config["identity"]["gender"] == "neutral"
        assert config["monitoring"]["enabled"] is True

    def test_partial_override(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"rocrail": {"host": "192.168.1.50"}}, f)
            f.flush()
            config = load_config(f.name)

        assert config["rocrail"]["host"] == "192.168.1.50"
        assert config["rocrail"]["port"] == 8051  # default preserved
        os.unlink(f.name)

    def test_env_var(self, monkeypatch):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"personality": "hal9000"}, f)
            f.flush()
            monkeypatch.setenv("OTTO_CONFIG_PATH", f.name)
            config = load_config()

        assert config["personality"] == "hal9000"
        os.unlink(f.name)

    def test_empty_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            config = load_config(f.name)

        assert config == DEFAULTS
        os.unlink(f.name)
