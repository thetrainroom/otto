"""Tests for otto.rocrail.client — uses mocked PyRocrail."""

from unittest.mock import MagicMock, patch

import pytest

from otto.rocrail.client import RocrailClient


@pytest.fixture
def mock_pyrocrail():
    """Create a mock PyRocrail instance with model."""
    with patch("otto.rocrail.client.PyRocrail") as MockPR:
        pr = MockPR.return_value
        pr.model = MagicMock()
        pr.model.change_callback = None
        yield pr, MockPR


@pytest.fixture
def connected_client(mock_pyrocrail):
    """Return a client that's already connected with mocked PyRocrail."""
    pr, MockPR = mock_pyrocrail
    client = RocrailClient("testhost", 9999)
    client.connect()
    return client, pr


class TestConnection:
    def test_connect(self, mock_pyrocrail):
        pr, MockPR = mock_pyrocrail
        client = RocrailClient("myhost", 1234)
        result = client.connect()
        assert result["success"] is True
        assert client.connected is True
        MockPR.assert_called_once_with(ip="myhost", port=1234, on_disconnect=client._on_disconnect)

    def test_connect_already_connected(self, mock_pyrocrail):
        client = RocrailClient()
        client.connect()
        result = client.connect()
        assert result["success"] is True
        assert "Already" in result["message"]

    def test_connect_failure(self):
        with patch("otto.rocrail.client.PyRocrail", side_effect=ConnectionError("refused")):
            client = RocrailClient()
            result = client.connect()
            assert result["success"] is False
            assert "refused" in result["error"]

    def test_disconnect(self, connected_client):
        client, pr = connected_client
        result = client.disconnect()
        assert result["success"] is True
        assert client.connected is False
        pr.stop.assert_called_once()

    def test_disconnect_not_connected(self):
        client = RocrailClient()
        result = client.disconnect()
        assert result["success"] is True


class TestLocoSpeed:
    def test_set_speed(self, connected_client):
        client, pr = connected_client
        loco = MagicMock()
        pr.model.get_lc.return_value = loco

        result = client.set_loco_speed("loco1", 50)
        assert result["success"] is True
        loco.set_speed.assert_called_once_with(50)

    def test_reject_negative(self, connected_client):
        client, pr = connected_client
        result = client.set_loco_speed("loco1", -1)
        assert result["success"] is False
        assert "0-100" in result["error"]

    def test_reject_over_100(self, connected_client):
        client, pr = connected_client
        result = client.set_loco_speed("loco1", 150)
        assert result["success"] is False
        assert "0-100" in result["error"]


class TestLocoDirection:
    def test_forward(self, connected_client):
        client, pr = connected_client
        loco = MagicMock()
        pr.model.get_lc.return_value = loco

        result = client.set_loco_direction("loco1", "forward")
        assert result["success"] is True
        loco.set_direction.assert_called_once_with(True)

    def test_reverse(self, connected_client):
        client, pr = connected_client
        loco = MagicMock()
        pr.model.get_lc.return_value = loco

        result = client.set_loco_direction("loco1", "reverse")
        assert result["success"] is True
        loco.set_direction.assert_called_once_with(False)

    def test_toggle(self, connected_client):
        client, pr = connected_client
        loco = MagicMock()
        pr.model.get_lc.return_value = loco

        result = client.set_loco_direction("loco1", "toggle")
        assert result["success"] is True
        loco.swap.assert_called_once()

    def test_invalid(self, connected_client):
        client, pr = connected_client
        loco = MagicMock()
        pr.model.get_lc.return_value = loco

        result = client.set_loco_direction("loco1", "sideways")
        assert result["success"] is False


class TestLocoFunction:
    def test_set_function(self, connected_client):
        client, pr = connected_client
        loco = MagicMock()
        pr.model.get_lc.return_value = loco

        result = client.set_loco_function("loco1", 0, True)
        assert result["success"] is True
        loco.set_function.assert_called_once_with(0, True)


class TestFindLoco:
    def test_fuzzy_match(self, connected_client):
        client, pr = connected_client
        loco = MagicMock()
        loco.V = 0
        loco.dir = True
        loco.mode = "idle"
        pr.model.get_locomotives.return_value = {"BR103": loco, "NS2418": loco}

        result = client.find_loco("103")
        assert result["found"] is True
        assert result["id"] == "BR103"

    def test_no_match(self, connected_client):
        client, pr = connected_client
        loco = MagicMock()
        loco.V = 0
        loco.dir = True
        loco.mode = "idle"
        pr.model.get_locomotives.return_value = {"BR103": loco}

        result = client.find_loco("zzzzz")
        assert result["found"] is False

    def test_no_locos(self, connected_client):
        client, pr = connected_client
        pr.model.get_locomotives.return_value = {}

        result = client.find_loco("anything")
        assert result["found"] is False


class TestDispatchLoco:
    def test_dispatch_warns_no_auto(self, connected_client):
        client, pr = connected_client
        loco = MagicMock()
        loco.blockid = "bk1"
        loco.mode = "idle"
        pr.model.get_lc.return_value = loco

        result = client.dispatch_loco("loco1", "bk2")
        assert result["success"] is True
        assert "warning" in result

    def test_dispatch_no_block(self, connected_client):
        client, pr = connected_client
        loco = MagicMock()
        loco.blockid = None
        pr.model.get_lc.return_value = loco

        result = client.dispatch_loco("loco1", "bk2")
        assert result["success"] is False
        assert "place_loco" in result["error"]


class TestBlockControl:
    def test_set_block_open(self, connected_client):
        client, pr = connected_client
        block = MagicMock()
        pr.model.get_bk.return_value = block

        result = client.set_block_state("bk1", "open")
        assert result["success"] is True
        block.open.assert_called_once()

    def test_set_block_closed(self, connected_client):
        client, pr = connected_client
        block = MagicMock()
        pr.model.get_bk.return_value = block

        result = client.set_block_state("bk1", "closed")
        assert result["success"] is True
        block.close.assert_called_once()

    def test_set_block_invalid(self, connected_client):
        client, pr = connected_client
        block = MagicMock()
        pr.model.get_bk.return_value = block

        result = client.set_block_state("bk1", "explode")
        assert result["success"] is False

    def test_free_override(self, connected_client):
        client, pr = connected_client
        block = MagicMock()
        pr.model.get_bk.return_value = block

        result = client.free_block_override("bk1")
        assert result["success"] is True
        block.free_override.assert_called_once()


class TestSwitchControl:
    def test_straight(self, connected_client):
        client, pr = connected_client
        sw = MagicMock()
        pr.model.get_sw.return_value = sw

        result = client.set_switch("sw1", "straight")
        assert result["success"] is True
        sw.straight.assert_called_once()

    def test_flip(self, connected_client):
        client, pr = connected_client
        sw = MagicMock()
        pr.model.get_sw.return_value = sw

        result = client.set_switch("sw1", "flip")
        assert result["success"] is True
        sw.flip.assert_called_once()

    def test_lock_unlock(self, connected_client):
        client, pr = connected_client
        sw = MagicMock()
        pr.model.get_sw.return_value = sw

        client.lock_switch("sw1")
        sw.lock.assert_called_once()
        client.unlock_switch("sw1")
        sw.unlock.assert_called_once()


class TestSignalControl:
    def test_set_red(self, connected_client):
        client, pr = connected_client
        sg = MagicMock()
        pr.model.get_sg.return_value = sg

        result = client.set_signal("sg1", "red")
        assert result["success"] is True
        sg.red.assert_called_once()

    def test_blank(self, connected_client):
        client, pr = connected_client
        sg = MagicMock()
        pr.model.get_sg.return_value = sg

        result = client.blank_signal("sg1")
        assert result["success"] is True
        sg.blank.assert_called_once()

    def test_signal_mode(self, connected_client):
        client, pr = connected_client
        sg = MagicMock()
        pr.model.get_sg.return_value = sg

        client.set_signal_mode("sg1", "auto")
        sg.auto.assert_called_once()
        client.set_signal_mode("sg1", "manual")
        sg.manual.assert_called_once()


class TestRouteControl:
    def test_lock_unlock_free(self, connected_client):
        client, pr = connected_client
        route = MagicMock()
        pr.model.get_st.return_value = route

        client.lock_route("rt1")
        route.lock.assert_called_once()
        client.unlock_route("rt1")
        route.unlock.assert_called_once()
        client.free_route("rt1")
        route.free.assert_called_once()

    def test_test_route(self, connected_client):
        client, pr = connected_client
        route = MagicMock()
        pr.model.get_st.return_value = route

        result = client.test_route("rt1")
        assert result["success"] is True
        route.test.assert_called_once()


class TestSystemControl:
    def test_power_on_off(self, connected_client):
        client, pr = connected_client

        client.power_on()
        pr.power_on.assert_called_once()
        client.power_off()
        pr.power_off.assert_called_once()

    def test_auto_on_off(self, connected_client):
        client, pr = connected_client

        client.auto_on()
        pr.auto_on.assert_called_once()
        client.auto_off()
        pr.auto_off.assert_called_once()

    def test_emergency_stop(self, connected_client):
        client, pr = connected_client

        client.emergency_stop_all()
        pr.emergency_stop.assert_called_once()

    def test_save(self, connected_client):
        client, pr = connected_client

        result = client.system_save()
        assert result["success"] is True
        pr.save.assert_called_once()


class TestNotConnected:
    def test_raises_when_not_connected(self):
        client = RocrailClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.set_loco_speed("loco1", 50)
