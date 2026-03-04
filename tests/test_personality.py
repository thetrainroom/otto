"""Tests for otto.personality."""

from otto.personality import (
    PERSONALITIES,
    Personality,
    _resolve_name,
    get_system_prompt,
)


class TestPersonalities:
    def test_all_defined(self):
        expected = {"swiss_dispatcher", "enthusiastic", "passive_aggressive", "hal9000"}
        assert set(PERSONALITIES.keys()) == expected

    def test_all_have_required_fields(self):
        for name, p in PERSONALITIES.items():
            assert isinstance(p, Personality), f"{name} is not a Personality"
            assert p.name, f"{name} missing name"
            assert p.style, f"{name} missing style"
            assert len(p.rules) > 0, f"{name} has no rules"
            assert "timeout" in p.alert_templates, f"{name} missing timeout template"
            assert "silence" in p.alert_templates, f"{name} missing silence template"
            assert "recovered" in p.alert_templates, f"{name} missing recovered template"


class TestResolveName:
    def test_neutral(self):
        assert _resolve_name({"gender": "neutral", "name": "OTTO"}) == "OTTO"

    def test_female(self):
        assert _resolve_name({"gender": "female"}) == "Ottoline"

    def test_male(self):
        assert _resolve_name({"gender": "male"}) == "Otto"

    def test_default(self):
        assert _resolve_name({}) == "OTTO"

    def test_custom_name_neutral(self):
        assert _resolve_name({"gender": "neutral", "name": "HAL"}) == "HAL"


class TestGetSystemPrompt:
    def test_contains_personality_style(self):
        prompt = get_system_prompt("swiss_dispatcher", {"gender": "neutral"}, "LAYOUT")
        assert "Dry, precise" in prompt

    def test_contains_layout_summary(self):
        prompt = get_system_prompt("enthusiastic", {"gender": "neutral"}, "MY LAYOUT DATA")
        assert "MY LAYOUT DATA" in prompt

    def test_contains_name(self):
        prompt = get_system_prompt("hal9000", {"gender": "female"}, "LAYOUT")
        assert "Ottoline" in prompt

    def test_unknown_personality_falls_back(self):
        prompt = get_system_prompt("nonexistent", {"gender": "neutral"}, "LAYOUT")
        assert "Dry, precise" in prompt  # falls back to swiss_dispatcher

    def test_contains_rules(self):
        prompt = get_system_prompt("swiss_dispatcher", {"gender": "neutral"}, "LAYOUT")
        assert "15 words" in prompt
