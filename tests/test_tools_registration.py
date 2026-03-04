"""Tests that all MCP tools are properly registered."""

from otto.mcp_server import mcp


class TestToolRegistration:
    def _get_tools(self):
        return set(mcp._tool_manager._tools.keys())

    def test_layout_tools(self):
        tools = self._get_tools()
        for name in ("get_layout_state", "get_topology", "find_loco", "find_route"):
            assert name in tools, f"Missing tool: {name}"

    def test_locomotive_tools(self):
        tools = self._get_tools()
        for name in (
            "set_loco_speed",
            "set_loco_direction",
            "set_loco_function",
            "stop_loco",
            "soft_stop_loco",
            "stop_all",
            "place_loco",
            "dispatch_loco",
            "assign_loco",
            "release_loco",
            "go_loco_forward",
            "go_loco_reverse",
            "soft_reset_loco",
            "set_loco_class",
            "assign_train_to_loco",
            "release_train_from_loco",
            "set_loco_goto_block",
        ):
            assert name in tools, f"Missing tool: {name}"

    def test_block_tools(self):
        tools = self._get_tools()
        for name in ("set_block_state", "free_block_override", "stop_block", "accept_block_ident", "get_block_info"):
            assert name in tools, f"Missing tool: {name}"

    def test_route_tools(self):
        tools = self._get_tools()
        for name in ("set_route", "lock_route", "unlock_route", "free_route", "test_route", "get_route_info"):
            assert name in tools, f"Missing tool: {name}"

    def test_switch_tools(self):
        tools = self._get_tools()
        for name in ("set_switch", "lock_switch", "unlock_switch"):
            assert name in tools, f"Missing tool: {name}"

    def test_signal_tools(self):
        tools = self._get_tools()
        for name in ("set_signal", "next_signal_aspect", "set_signal_aspect_number", "set_signal_mode", "blank_signal"):
            assert name in tools, f"Missing tool: {name}"

    def test_feedback_tools(self):
        tools = self._get_tools()
        for name in ("set_feedback", "flip_feedback", "list_feedbacks"):
            assert name in tools, f"Missing tool: {name}"

    def test_output_tools(self):
        tools = self._get_tools()
        for name in ("set_output", "activate_output", "list_outputs"):
            assert name in tools, f"Missing tool: {name}"

    def test_staging_tools(self):
        tools = self._get_tools()
        for name in ("stage_action", "get_stage_info", "list_stages"):
            assert name in tools, f"Missing tool: {name}"

    def test_car_tools(self):
        tools = self._get_tools()
        for name in ("set_car_status", "assign_car_waybill", "reset_car_waybill", "set_car_function", "list_cars"):
            assert name in tools, f"Missing tool: {name}"

    def test_operator_tools(self):
        tools = self._get_tools()
        for name in ("operator_add_car", "operator_leave_car", "operator_empty_car", "operator_load_car", "list_operators"):
            assert name in tools, f"Missing tool: {name}"

    def test_automation_tools(self):
        tools = self._get_tools()
        for name in ("start_automation", "stop_automation", "get_schedule", "list_schedules", "assign_schedule"):
            assert name in tools, f"Missing tool: {name}"

    def test_system_tools(self):
        tools = self._get_tools()
        for name in ("power_on", "power_off", "set_clock", "system_save", "system_reset", "system_shutdown", "start_of_day", "end_of_day", "fire_event", "start_loco_in_block"):
            assert name in tools, f"Missing tool: {name}"

    def test_extras_tools(self):
        tools = self._get_tools()
        for name in ("set_booster", "set_variable", "randomize_variable", "weather_action", "set_text", "location_info"):
            assert name in tools, f"Missing tool: {name}"

    def test_monitoring_tools(self):
        tools = self._get_tools()
        for name in ("get_active_movements", "acknowledge_timeout", "report_loco_recovered", "get_alerts"):
            assert name in tools, f"Missing tool: {name}"

    def test_voice_tools(self):
        tools = self._get_tools()
        assert "speak" in tools

    def test_total_count(self):
        tools = self._get_tools()
        assert len(tools) >= 85, f"Expected at least 85 tools, got {len(tools)}"
