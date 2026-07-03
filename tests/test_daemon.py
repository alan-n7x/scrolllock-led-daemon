import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest


class _Ecodes:
    EV_KEY = 1
    EV_LED = 17
    KEY_SCROLLLOCK = 70
    KEY_CAPSLOCK = 58
    KEY_NUMLOCK = 69
    KEY_F12 = 88
    LED = {0: "LED_NUML", 1: "LED_CAPSL", 2: "LED_SCROLLL"}
    KEY = {70: "KEY_SCROLLLOCK", 58: "KEY_CAPSLOCK", 69: "KEY_NUMLOCK"}


evdev_mock = MagicMock()
evdev_mock.ecodes = _Ecodes()
sys.modules["evdev"] = evdev_mock

from pathlib import Path

from scrolllock_led_daemon import (
    CONFIG_PATHS,
    VERSION,
    _check,
    _resolve_key,
    find_led_by_name,
    load_config,
    parse_args,
    read_led,
    write_led,
)


class TestResolveKey:
    def test_valid_key(self):
        assert _resolve_key("KEY_SCROLLLOCK") == 70
        assert _resolve_key("KEY_F12") == 88
        assert _resolve_key("KEY_CAPSLOCK") == 58

    def test_unknown_key(self):
        with pytest.raises(ValueError, match="Unknown key: KEY_NONEXISTENT"):
            _resolve_key("KEY_NONEXISTENT")


class TestReadWriteLed:
    def test_read_led_on(self):
        with patch.object(Path, "read_text", return_value="1\n"):
            assert read_led(Path("/fake/brightness")) is True

    def test_read_led_off(self):
        with patch.object(Path, "read_text", return_value="0\n"):
            assert read_led(Path("/fake/brightness")) is False

    def test_write_led_on(self):
        m = mock_open()
        with patch.object(Path, "write_text", m):
            write_led(Path("/fake/brightness"), True)
            m.assert_called_once_with("1")

    def test_write_led_off(self):
        m = mock_open()
        with patch.object(Path, "write_text", m):
            write_led(Path("/fake/brightness"), False)
            m.assert_called_once_with("0")


class TestFindLedByName:
    @patch("scrolllock_led_daemon.Path.glob")
    def test_found(self, mock_glob):
        mock_led = MagicMock(spec=Path)
        mock_brightness = MagicMock(spec=Path)
        mock_brightness.exists.return_value = True
        mock_led.__truediv__.return_value = mock_brightness
        mock_glob.return_value = [mock_led]

        result = find_led_by_name("scrolllock")
        assert result == mock_brightness
        mock_glob.assert_called_once_with("*scrolllock")

    @patch("scrolllock_led_daemon.Path.glob")
    def test_not_found(self, mock_glob):
        mock_glob.return_value = []
        with pytest.raises(RuntimeError, match="No LED found matching: scrolllock"):
            find_led_by_name("scrolllock")


class TestCheck:
    def test_pass(self, capsys):
        _check("Python 3.10", True)
        captured = capsys.readouterr()
        assert "✔" in captured.out
        assert "Python 3.10" in captured.out

    def test_fail_without_hint(self, capsys):
        _check("Something", False)
        captured = capsys.readouterr()
        assert "✖" in captured.out

    def test_fail_with_hint(self, capsys):
        _check("Something", False, "Try this fix")
        captured = capsys.readouterr()
        assert "Try this fix" in captured.out


class TestLoadConfig:
    def test_no_config_files(self):
        with patch.object(Path, "exists", return_value=False):
            result = load_config()
            assert result == {}

    def test_loads_values(self):
        from unittest.mock import call

        with patch.object(Path, "exists", return_value=True):
            with patch(
                "scrolllock_led_daemon.configparser.ConfigParser"
            ) as MockConfig:

                instance = MockConfig.return_value
                instance.has_option.side_effect = (
                    lambda section, option: option in ("device", "verbose")
                )
                instance.get.return_value = "/dev/input/event4"
                instance.getboolean.return_value = True

                result = load_config()

                assert result["device"] == "/dev/input/event4"
                assert result["verbose"] is True


class TestParseArgs:
    def test_defaults(self):
        args = parse_args([])
        assert args.key == "KEY_SCROLLLOCK"
        assert args.device is None
        assert args.led is None
        assert args.set is None
        assert args.toggle is False
        assert args.list is False
        assert args.doctor is False
        assert args.config is None
        assert args.verbose is False

    def test_device(self):
        args = parse_args(["--device", "/dev/input/event4"])
        assert args.device == "/dev/input/event4"

    def test_led(self):
        args = parse_args(["--led", "scrolllock"])
        assert args.led == "scrolllock"

    def test_key(self):
        args = parse_args(["--key", "KEY_F12"])
        assert args.key == "KEY_F12"

    def test_set_on(self):
        args = parse_args(["--set", "on"])
        assert args.set == "on"

    def test_set_off(self):
        args = parse_args(["--set", "off"])
        assert args.set == "off"

    def test_set_invalid(self):
        with pytest.raises(SystemExit):
            parse_args(["--set", "maybe"])

    def test_toggle(self):
        args = parse_args(["--toggle"])
        assert args.toggle is True

    def test_list(self):
        args = parse_args(["--list"])
        assert args.list is True

    def test_doctor(self):
        args = parse_args(["--doctor"])
        assert args.doctor is True

    def test_config(self):
        args = parse_args(["--config", "/etc/my.conf"])
        assert args.config == "/etc/my.conf"

    def test_verbose(self):
        args = parse_args(["--verbose"])
        assert args.verbose is True

    def test_version(self):
        with pytest.raises(SystemExit):
            parse_args(["--version"])

    def test_help(self):
        with pytest.raises(SystemExit):
            parse_args(["--help"])
