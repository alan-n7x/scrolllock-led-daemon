import sys
import types
from unittest.mock import MagicMock, mock_open, patch

import pytest


class _Ecodes:
    EV_KEY = 1
    EV_SYN = 0
    EV_LED = 17
    KEY_SCROLLLOCK = 70
    KEY_CAPSLOCK = 58
    KEY_NUMLOCK = 69
    KEY_F12 = 88
    LED = {0: "LED_NUML", 1: "LED_CAPSL", 2: "LED_SCROLLL"}
    KEY = {70: "KEY_SCROLLLOCK", 58: "KEY_CAPSLOCK", 69: "KEY_NUMLOCK"}


class _Event:
    def __init__(self, type_, code, value):
        self.type = type_
        self.code = code
        self.value = value


evdev_mock = MagicMock()
evdev_mock.ecodes = _Ecodes()
sys.modules["evdev"] = evdev_mock

from pathlib import Path


def _make_device(path="/dev/input/event3", name="My Keyboard", keys=None, leds=None):
    """Helper to create a mock InputDevice with capabilities."""
    dev = MagicMock()
    dev.path = path
    dev.name = name
    caps = {}
    if keys is not None:
        caps[_Ecodes.EV_KEY] = keys
    if leds is not None:
        caps[_Ecodes.EV_LED] = leds
    dev.capabilities.return_value = caps
    return dev


@pytest.fixture(autouse=True)
def _reset_shutdown():
    from scrolllock_led_daemon import _shutdown

    _shutdown.clear()
    yield

from scrolllock_led_daemon import (
    CONFIG_PATHS,
    VERSION,
    _check,
    _resolve_key,
    find_keyboard,
    find_led_by_name,
    find_scrolllock_led,
    list_input_devices,
    load_config,
    main,
    parse_args,
    read_led,
    run_daemon_loop,
    run_doctor,
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


class TestFindKeyboard:
    @patch("scrolllock_led_daemon.InputDevice")
    def test_with_device_path(self, mock_input_device):
        mock_input_device.return_value = _make_device(
            "/dev/input/event4", "Custom KB", keys=[_Ecodes.KEY_SCROLLLOCK]
        )
        result = find_keyboard("/dev/input/event4")
        assert result.path == "/dev/input/event4"
        mock_input_device.assert_called_once_with("/dev/input/event4")

    @patch("scrolllock_led_daemon.list_devices")
    @patch("scrolllock_led_daemon.InputDevice")
    def test_auto_detect_found(self, mock_input_device, mock_list_devices):
        mock_list_devices.return_value = ["/dev/input/event3", "/dev/input/event5"]
        devices = {
            "/dev/input/event3": _make_device("/dev/input/event3", "Mouse", keys=[]),
            "/dev/input/event5": _make_device(
                "/dev/input/event5", "KB", keys=[_Ecodes.KEY_SCROLLLOCK]
            ),
        }
        mock_input_device.side_effect = lambda path: devices[path]

        result = find_keyboard()
        assert result.path == "/dev/input/event5"

    @patch("scrolllock_led_daemon.list_devices")
    @patch("scrolllock_led_daemon.InputDevice")
    def test_auto_detect_skips_permission_error(
        self, mock_input_device, mock_list_devices
    ):
        mock_list_devices.return_value = ["/dev/input/event3", "/dev/input/event5"]
        mock_input_device.side_effect = [
            PermissionError("denied"),
            _make_device("/dev/input/event5", "KB", keys=[_Ecodes.KEY_SCROLLLOCK]),
        ]

        result = find_keyboard()
        assert result.path == "/dev/input/event5"

    @patch("scrolllock_led_daemon.list_devices")
    @patch("scrolllock_led_daemon.InputDevice")
    def test_not_found_raises(self, mock_input_device, mock_list_devices):
        mock_list_devices.return_value = ["/dev/input/event3"]
        mock_input_device.return_value = _make_device(
            "/dev/input/event3", "Mouse", keys=[]
        )

        with pytest.raises(RuntimeError, match="No keyboard with Scroll Lock"):
            find_keyboard()


class TestRunDaemonLoop:
    def test_toggles_led_on_key_press(self):
        from scrolllock_led_daemon import _shutdown

        keyboard = MagicMock()
        events = [
            _Event(_Ecodes.EV_KEY, _Ecodes.KEY_SCROLLLOCK, 1),
        ]
        keyboard.read_loop.return_value = events

        led = MagicMock(spec=Path)
        led.read_text.return_value = "0\n"

        run_daemon_loop(keyboard, led, _Ecodes.KEY_SCROLLLOCK)

        led.read_text.assert_called_once()
        led.write_text.assert_called_once_with("1")
        assert not _shutdown.is_set()

    def test_skips_non_key_events(self):
        keyboard = MagicMock()
        events = [
            _Event(_Ecodes.EV_SYN, 0, 0),
            _Event(_Ecodes.EV_KEY, _Ecodes.KEY_SCROLLLOCK, 1),
        ]
        keyboard.read_loop.return_value = events

        led = MagicMock(spec=Path)
        led.read_text.return_value = "0\n"

        run_daemon_loop(keyboard, led, _Ecodes.KEY_SCROLLLOCK)
        assert led.write_text.call_count == 1

    def test_skips_wrong_key(self):
        keyboard = MagicMock()
        events = [
            _Event(_Ecodes.EV_KEY, _Ecodes.KEY_F12, 1),
        ]
        keyboard.read_loop.return_value = events

        led = MagicMock(spec=Path)

        run_daemon_loop(keyboard, led, _Ecodes.KEY_SCROLLLOCK)
        led.write_text.assert_not_called()

    def test_skips_key_release(self):
        keyboard = MagicMock()
        events = [
            _Event(_Ecodes.EV_KEY, _Ecodes.KEY_SCROLLLOCK, 0),
        ]
        keyboard.read_loop.return_value = events

        led = MagicMock(spec=Path)

        run_daemon_loop(keyboard, led, _Ecodes.KEY_SCROLLLOCK)
        led.write_text.assert_not_called()

    def test_breaks_on_shutdown(self):
        from scrolllock_led_daemon import _shutdown

        keyboard = MagicMock()
        keyboard.read_loop.return_value = iter(
            [_Event(_Ecodes.EV_KEY, _Ecodes.KEY_SCROLLLOCK, 1)]
        )

        led = MagicMock(spec=Path)
        _shutdown.set()

        run_daemon_loop(keyboard, led, _Ecodes.KEY_SCROLLLOCK)
        led.write_text.assert_not_called()

    def test_toggles_led_off(self):
        keyboard = MagicMock()
        events = [
            _Event(_Ecodes.EV_KEY, _Ecodes.KEY_SCROLLLOCK, 1),
        ]
        keyboard.read_loop.return_value = events

        led = MagicMock(spec=Path)
        led.read_text.return_value = "1\n"

        run_daemon_loop(keyboard, led, _Ecodes.KEY_SCROLLLOCK)

        led.read_text.assert_called_once()
        led.write_text.assert_called_once_with("0")


class TestListInputDevices:
    @patch("scrolllock_led_daemon.list_devices")
    @patch("scrolllock_led_daemon.InputDevice")
    def test_lists_keyboards_and_others(self, mock_input_device, mock_list_devices):
        mock_list_devices.return_value = ["/dev/input/event3", "/dev/input/event5"]
        devices = {
            "/dev/input/event3": _make_device(
                "/dev/input/event3",
                "My Keyboard",
                keys=[_Ecodes.KEY_SCROLLLOCK, _Ecodes.KEY_CAPSLOCK],
                leds=[2],
            ),
            "/dev/input/event5": _make_device(
                "/dev/input/event5", "Mouse", keys=[]
            ),
        }
        mock_input_device.side_effect = lambda path: devices[path]

        list_input_devices()

    @patch("scrolllock_led_daemon.list_devices")
    @patch("scrolllock_led_daemon.InputDevice")
    def test_permission_denied(self, mock_input_device, mock_list_devices):
        mock_list_devices.return_value = ["/dev/input/event3"]
        mock_input_device.side_effect = PermissionError("denied")

        with patch("builtins.print") as mock_print:
            list_input_devices()
            output = "".join(c[0][0] for c in mock_print.call_args_list)
            assert "Permission denied" in output

    @patch("scrolllock_led_daemon.list_devices", return_value=[])
    def test_no_devices(self, mock_list_devices):
        with patch("builtins.print") as mock_print:
            list_input_devices()
            output = "".join(c[0][0] for c in mock_print.call_args_list)
            assert "No input devices found" in output


class TestRunDoctor:
    @patch("scrolllock_led_daemon.importlib.util.find_spec")
    @patch("scrolllock_led_daemon.list_devices")
    @patch("scrolllock_led_daemon.InputDevice")
    @patch("scrolllock_led_daemon.find_scrolllock_led")
    @patch("scrolllock_led_daemon.Path.exists")
    @patch("scrolllock_led_daemon.subprocess.run")
    def test_all_checks_pass(
        self,
        mock_subprocess,
        mock_exists,
        mock_find_led,
        mock_input_device,
        mock_list_devices,
        mock_find_spec,
    ):
        mock_find_spec.return_value = MagicMock()
        mock_list_devices.return_value = ["/dev/input/event3"]
        mock_input_device.return_value = _make_device(
            "/dev/input/event3",
            "My Keyboard",
            keys=[_Ecodes.KEY_SCROLLLOCK],
        )
        led = MagicMock(spec=Path)
        led.read_text.return_value = "0\n"
        mock_find_led.return_value = led
        mock_exists.return_value = True
        mock_subprocess.return_value = MagicMock(stdout="active\n")

        with patch("builtins.print") as mock_print:
            run_doctor()
            output = "".join(
                c[0][0] for c in mock_print.call_args_list if c[0]
            )
            assert "scrolllock-led-daemon --doctor" in output

    @patch("scrolllock_led_daemon.importlib.util.find_spec", return_value=None)
    def test_evdev_not_installed(self, mock_find_spec):
        with patch("builtins.print") as mock_print:
            run_doctor()
            output = "".join(
                c[0][0] for c in mock_print.call_args_list if c[0]
            )
            assert "evdev" in output


class TestMain:
    @patch("scrolllock_led_daemon.parse_args")
    @patch("scrolllock_led_daemon.list_input_devices")
    def test_list_mode(self, mock_list, mock_parse):
        mock_parse.return_value = MagicMock(
            list=True,
            doctor=False,
            device=None,
            led=None,
            key="KEY_SCROLLLOCK",
            set=None,
            toggle=False,
            config=None,
            verbose=False,
        )
        main()
        mock_list.assert_called_once()

    @patch("scrolllock_led_daemon.parse_args")
    @patch("scrolllock_led_daemon.run_doctor")
    def test_doctor_mode(self, mock_doctor, mock_parse):
        mock_parse.return_value = MagicMock(
            list=False,
            doctor=True,
            device=None,
            led=None,
            key="KEY_SCROLLLOCK",
            set=None,
            toggle=False,
            config=None,
            verbose=False,
        )
        main()
        mock_doctor.assert_called_once()

    @patch("scrolllock_led_daemon.parse_args")
    @patch("scrolllock_led_daemon.load_config", return_value={})
    @patch("scrolllock_led_daemon._resolve_key")
    @patch("scrolllock_led_daemon.find_scrolllock_led")
    @patch("scrolllock_led_daemon.write_led")
    def test_set_on(
        self, mock_write, mock_find_led, mock_resolve, mock_config, mock_parse
    ):
        mock_parse.return_value = MagicMock(
            list=False,
            doctor=False,
            device=None,
            led=None,
            key="KEY_SCROLLLOCK",
            set="on",
            toggle=False,
            config=None,
            verbose=False,
        )
        mock_find_led.return_value = MagicMock(spec=Path)
        main()
        mock_write.assert_called_once_with(mock_find_led.return_value, True)

    @patch("scrolllock_led_daemon.parse_args")
    @patch("scrolllock_led_daemon.load_config", return_value={})
    @patch("scrolllock_led_daemon._resolve_key")
    @patch("scrolllock_led_daemon.find_scrolllock_led")
    @patch("scrolllock_led_daemon.write_led")
    def test_set_off(
        self, mock_write, mock_find_led, mock_resolve, mock_config, mock_parse
    ):
        mock_parse.return_value = MagicMock(
            list=False,
            doctor=False,
            device=None,
            led=None,
            key="KEY_SCROLLLOCK",
            set="off",
            toggle=False,
            config=None,
            verbose=False,
        )
        mock_find_led.return_value = MagicMock(spec=Path)
        main()
        mock_write.assert_called_once_with(mock_find_led.return_value, False)

    @patch("scrolllock_led_daemon.parse_args")
    @patch("scrolllock_led_daemon.load_config", return_value={})
    @patch("scrolllock_led_daemon._resolve_key")
    @patch("scrolllock_led_daemon.find_scrolllock_led")
    @patch("scrolllock_led_daemon.read_led")
    @patch("scrolllock_led_daemon.write_led")
    def test_toggle(
        self, mock_write, mock_read, mock_find_led, mock_resolve, mock_config, mock_parse
    ):
        mock_parse.return_value = MagicMock(
            list=False,
            doctor=False,
            device=None,
            led=None,
            key="KEY_SCROLLLOCK",
            set=None,
            toggle=True,
            config=None,
            verbose=False,
        )
        mock_find_led.return_value = MagicMock(spec=Path)
        mock_read.return_value = False
        main()
        mock_write.assert_called_once_with(mock_find_led.return_value, True)
