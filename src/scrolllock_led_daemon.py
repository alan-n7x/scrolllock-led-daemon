#!/usr/bin/env python3

import argparse
import configparser
import importlib.util
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from ctypes import CDLL
from pathlib import Path

import sdnotify  # pip install sdnotify
from pythonjsonlogger import jsonlogger  # pip install python-json-logger
from evdev import InputDevice, ecodes, list_devices

VERSION = "1.4.6"
_shutdown = threading.Event()

# CONFIGURE STRUCTURED LOGGING
def setup_logging():
    """Configure structured JSON logging for production observability."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Handler for stdout (captured by systemd)
    handler = logging.StreamHandler(sys.stdout)

    # JSON formatter with timestamp and standard fields
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Reduce noise from external libraries
    logging.getLogger('evdev').setLevel(logging.WARNING)
    logging.getLogger('udev').setLevel(logging.WARNING)

    return logger

logger = setup_logging()

CONFIG_PATHS = [
    Path("/etc/scrolllock-led-daemon.conf"),
    Path.home() / ".config" / "scrolllock-led-daemon" / "scrolllock-led-daemon.conf",
]


def _handle_signal(signum: int, frame: object) -> None:
    """Handle termination signals.

    Args:
        signum: Signal number received.
        frame: Current stack frame (unused).
    """
    logger.info("Received signal, shutting down...", extra={
        "signal": signum,
        "event": "shutdown_initiated"
    })
    _shutdown.set()


def _setup_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown.

    Registers handlers for SIGTERM and SIGINT to allow the daemon
    to shut down cleanly.
    """
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)


def _notify_systemd(state: str = "READY=1") -> None:
    """Notify systemd about daemon state changes via sd_notify.

    Args:
        state: Notification string (e.g. "READY=1", "STOPPING=1").
    """
    try:
        CDLL("libsystemd.so.0").sd_notify(0, state.encode())
    except OSError:
        pass  # systemd not available (e.g. when not running as service)


def _resolve_key(key_name: str) -> int:
    """Convert a key name string to an evdev key code.

    Args:
        key_name: Key name (e.g. "KEY_SCROLLLOCK", "KEY_F12").

    Returns:
        The evdev key code.

    Raises:
        ValueError: If the key name is unknown.
    """
    code = getattr(ecodes, key_name, None)
    if code is None:
        raise ValueError(f"Unknown key: {key_name}")
    return code


def run_daemon_loop(keyboard: InputDevice, led: Path, key_code: int) -> None:
    """Run the main event loop, processing key presses.

    Args:
        keyboard: The keyboard InputDevice to listen on.
        led: Path to the LED brightness file.
        key_code: The evdev key code to listen for.
    """
    for event in keyboard.read_loop():
        if _shutdown.is_set():
            break

        if event.type != ecodes.EV_KEY:
            continue

        if event.code == key_code and event.value == 1:
            enabled = not read_led(led)
            write_led(led, enabled)

            # Structured log for business event (LED state change)
            logger.info("LED state changed", extra={
                "event": "led_state_changed",
                "device_path": keyboard.path,
                "device_name": keyboard.name,
                "led_type": "scrolllock",
                "new_state": "on" if enabled else "off",
                "timestamp": time.time()
            })


def find_keyboard(device_path: str | None = None) -> InputDevice:
    """Find the keyboard device.

    Auto-detects by scanning all input devices for Scroll Lock key support.

    Args:
        device_path: Explicit path to the keyboard device.
            When provided, auto-detection is skipped.

    Returns:
        The keyboard InputDevice.

    Raises:
        RuntimeError: If no keyboard with Scroll Lock support is found.
    """
    if device_path:
        device = InputDevice(device_path)
        logger.info("Keyboard configured", extra={
            "event": "keyboard_configured",
            "device_path": device.path,
            "device_name": device.name
        })
        return device

    for path in list_devices():
        try:
            device = InputDevice(path)
        except PermissionError:
            continue

        keys = device.capabilities().get(ecodes.EV_KEY, [])

        if ecodes.KEY_SCROLLLOCK in keys:
            logger.debug("Keyboard discovered", extra={
                "event": "keyboard_discovered",
                "device_path": device.path,
                "device_name": device.name
            })
            return device

    raise RuntimeError(
        "No keyboard with Scroll Lock support found.\n"
        "\n"
        "If running as a normal user, try:\n"
        "    sudo scrolllock-led-daemon\n"
        "\n"
        "Or install the udev rules:\n"
        "    sudo ./scripts/install.sh"
    )


def find_scrolllock_led(led_path: str | None = None) -> Path:
    """Find the Scroll Lock LED brightness file.

    Auto-detects by scanning /sys/class/leds for entries containing
    "scrolllock".

    Args:
        led_path: Explicit path to the LED brightness file.
            When provided, auto-detection is skipped.

    Returns:
        Path to the brightness file.

    Raises:
        RuntimeError: If the explicit path does not exist, or no Scroll Lock
            LED is found during auto-detection.
    """
    if led_path:
        brightness = Path(led_path)
        if not brightness.exists():
            raise RuntimeError(f"LED brightness file not found: {brightness}")
        logger.debug("LED configured", extra={
            "event": "led_configured",
            "led_path": str(brightness)
        })
        return brightness

    for led in Path("/sys/class/leds").glob("*scrolllock"):
        brightness = led / "brightness"

        if brightness.exists():
            logger.debug("LED discovered", extra={
                "event": "led_discovered",
                "led_path": str(brightness)
            })
            return brightness

    raise RuntimeError("No Scroll Lock LED found")


def _check(label: str, status: bool, hint: str = "") -> None:
    """Print a check result line.

    Args:
        label: Description of what was checked.
        status: True for pass, False for fail.
        hint: Optional suggestion on how to fix.
    """
    icon = "✔" if status else "✖"
    print(f"  {icon} {label}")
    if not status and hint:
        for line in hint.strip().split("\n"):
            print(f"     {line}")
        print()


def run_doctor() -> None:
    """Run system diagnostics and print results.

    Checks Python version, evdev availability, input device permissions,
    keyboard detection, LED write access, configuration files, and
    systemd service status.
    """
    print("scrolllock-led-daemon --doctor\n")

    # Python version
    py_ok = sys.version_info >= (3, 10)
    _check(
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        py_ok,
        "Requires Python >= 3.10",
    )

    # evdev
    evdev_ok = importlib.util.find_spec("evdev") is not None
    _check(
        "evdev installed",
        evdev_ok,
        "Install: sudo apt install python3-evdev",
    )

    if not evdev_ok:
        return

    # Permission to read input devices
    input_devices = list_devices()
    can_read_input = False
    permission_hint = ""
    for path in input_devices:
        try:
            InputDevice(path)
            can_read_input = True
            break
        except PermissionError:
            permission_hint = (
                "Run with sudo or install udev rules:\n"
                "    sudo ./scripts/install.sh"
            )
            continue
        except OSError:
            continue

    _check(
        "Permission to read /dev/input/event*",
        can_read_input,
        permission_hint,
    )

    # Keyboard with Scroll Lock
    keyboard = None
    if can_read_input:
        for path in input_devices:
            try:
                dev = InputDevice(path)
                keys = dev.capabilities().get(ecodes.EV_KEY, [])
                if ecodes.KEY_SCROLLLOCK in keys:
                    keyboard = dev
                    break
            except (PermissionError, OSError):
                continue

    _check(
        f"Keyboard found{' (' + keyboard.name + ')' if keyboard else ''}",
        keyboard is not None,
        "Use --device to specify the path manually.",
    )

    # Permission to write LED
    led = find_scrolllock_led()
    can_write_led = led is not None
    if led:
        try:
            led.write_text(led.read_text().strip())
            can_write_led = True
        except PermissionError:
            can_write_led = False

    _check(
        f"Scroll Lock LED{' (' + str(led) + ')' if led else ''}",
        can_write_led,
        "Run with sudo or add user to the input group:\n"
        "    sudo usermod -aG input $USER",
    )

    # Configuration file
    config_loaded = any(p.exists() for p in CONFIG_PATHS)
    config_paths = "\n".join(f"    {p}" for p in CONFIG_PATHS)
    _check(
        "Configuration file",
        config_loaded,
        f"Create one of:\n{config_paths}",
    )

    # systemd service
    svc = Path("/etc/systemd/system/scrolllock-led-daemon.service")
    svc_ok = svc.exists()
    _check(
        "systemd service installed",
        svc_ok,
        "Install: sudo ./scripts/install.sh",
    )

    if svc_ok:
        result = subprocess.run(
            ["systemctl", "is-active", "scrolllock-led-daemon"],
            capture_output=True, text=True, timeout=5,
        )
        active = result.stdout.strip() == "active"
        _check(
            f"systemd service: {result.stdout.strip()}",
            active,
            "Start: sudo systemctl start scrolllock-led-daemon",
        )


def list_input_devices() -> None:
    """List all input devices with their capabilities.

    Detects keyboards with Scroll/Caps/Num/F12 keys and other input
    devices, showing device paths, names, supported keys, and LEDs.
    Handles permission errors gracefully with user-friendly messages.
    """
    keyboards = []
    others = []

    permission_denied = False

    for path in list_devices():
        try:
            device = InputDevice(path)
        except PermissionError:
            permission_denied = True
            continue

        caps = device.capabilities()
        keys = caps.get(ecodes.EV_KEY, [])
        leds = caps.get(ecodes.EV_LED, [])

        led_names = []
        for code in leds:
            name = ecodes.LED.get(code, f"unknown({code})")
            led_names.append(name)

        known_keys = {"KEY_SCROLLLOCK", "KEY_CAPSLOCK", "KEY_NUMLOCK", "KEY_F12"}
        matched = known_keys & {ecodes.KEY.get(k, "") for k in keys}

        entry = {
            "path": device.path,
            "name": device.name,
            "keys": sorted(matched),
            "leds": led_names,
        }

        if matched:
            keyboards.append(entry)
        else:
            others.append(entry)

    if not keyboards and not others:
        if permission_denied:
            print(
                "Permission denied while accessing /dev/input/event*.\n"
                "\n"
                "Try:\n"
                "    sudo scrolllock-led-daemon --list\n"
                "\n"
                "Or install the udev rules:\n"
                "    sudo ./scripts/install.sh"
            )
        else:
            print("No input devices found.")
        return

    if keyboards:
        print("Keyboards with Scroll / Caps / Num / F12 keys\n")
        for kb in keyboards:
            print(f"  Device:  {kb['path']}")
            print(f"  Name:    {kb['name']}")
            print(f"  Keys:    {', '.join(kb['keys']) or 'none'}")
            print(f"  LEDs:    {', '.join(kb['leds']) or 'none'}")
            print()

    print("Other input devices\n")
    for dev in others:
        print(f"  Device:  {dev['path']}")
        print(f"  Name:    {dev['name']}")
        print()


def find_led_by_name(name: str) -> Path:
    """Find an LED brightness file by name suffix.

    Args:
        name: LED name suffix (e.g. "scrolllock", "capslock", "numlock").

    Returns:
        Path to the brightness file.

    Raises:
        RuntimeError: If no matching LED is found.
    """
    for led in Path("/sys/class/leds").glob(f"*{name}"):
        brightness = led / "brightness"
        if brightness.exists():
            return brightness

    raise RuntimeError(f"No LED found matching: {name}")


def read_led(led: Path) -> bool:
    """Read the current LED state.

    Args:
        led: Path to the LED brightness file.

    Returns:
        True if the LED is on, False otherwise.
    """
    return led.read_text().strip() == "1"


def write_led(led: Path, enabled: bool) -> None:
    """Write the LED state.

    Args:
        led: Path to the LED brightness file.
        enabled: True to turn the LED on, False to turn it off.
    """
    led.write_text("1" if enabled else "0")


def load_config(config_path: str | None = None) -> dict:
    """Load configuration from INI files.

    Reads from the system config, user config, and optional custom path.
    Each level overrides the previous.

    Args:
        config_path: Optional explicit config file path.

    Returns:
        Dictionary with config values.
    """
    config = configparser.ConfigParser(interpolation=None)
    paths = CONFIG_PATHS[:]

    if config_path:
        paths.insert(0, Path(config_path))

    for path in paths:
        if path.exists():
            logger.debug("Loading config", extra={
                "event": "config_loaded",
                "config_path": str(path)
            })
            config.read(path)

    result: dict = {}

    if config.has_option("daemon", "device"):
        result["device"] = config.get("daemon", "device")
    if config.has_option("daemon", "led"):
        result["led"] = config.get("daemon", "led")
    if config.has_option("daemon", "key"):
        result["key"] = config.get("daemon", "key")
    if config.has_option("daemon", "verbose"):
        result["verbose"] = config.getboolean("daemon", "verbose")

    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Argument list. Defaults to sys.argv.

    Returns:
        Parsed arguments as a Namespace object.
    """
    parser = argparse.ArgumentParser(
        description="Daemon that synchronizes a key press with the keyboard LED."
    )
    parser.add_argument(
        "--device",
        type=str,
        help="Keyboard device path (e.g. /dev/input/event4)",
    )
    parser.add_argument(
        "--led",
        type=str,
        help=(
            "LED brightness file or name suffix (e.g. /sys/.../brightness, "
            "scrolllock, capslock, numlock)"
        ),
    )
    parser.add_argument(
        "--key",
        type=str,
        default="KEY_SCROLLLOCK",
        help="Key to listen for (default: KEY_SCROLLLOCK)",
    )
    parser.add_argument(
        "--set",
        type=str,
        choices=["on", "off"],
        help="Set LED state and exit (one-shot mode)",
    )
    parser.add_argument(
        "--toggle",
        action="store_true",
        help="Toggle LED state and exit (one-shot mode)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available input devices and exit",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run system diagnostics",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logs",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"scrolllock-led-daemon {VERSION}",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Main entry point of the daemon.

    Parses arguments, loads configuration, and runs in one of four
    modes: daemon, one-shot (--set/--toggle), --list, or --doctor.
    """
    args = parse_args()
    config = load_config(args.config)

    verbose = args.verbose or config.get("verbose", False)
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(message)s",
            force=True,
        )
        logger.debug("Verbose mode enabled")

    if args.list:
        list_input_devices()
        return

    if args.doctor:
        run_doctor()
        return

    device = args.device or config.get("device")
    led_value = args.led or config.get("led")
    key_name = args.key or config.get("key", "KEY_SCROLLLOCK")

    key_code = _resolve_key(key_name)

    if led_value and "/" not in led_value:
        led = find_led_by_name(led_value)
    else:
        led = find_scrolllock_led(led_value)

    if args.set:
        write_led(led, args.set == "on")
        logger.info("LED state set", extra={
            "event": "led_set",
            "state": args.set
        })
        return

    if args.toggle:
        enabled = not read_led(led)
        write_led(led, enabled)
        logger.info("LED state toggled", extra={
            "event": "led_toggled",
            "new_state": "on" if enabled else "off"
        })
        return

    _setup_signal_handlers()

    # Initialize systemd watchdog notification
    notifier = sdnotify.SystemdNotifier()
    last_notify = time.time()

    _notify_systemd("READY=1")
    logger.info("Daemon started", extra={
        "event": "daemon_started",
        "version": VERSION,
        "pid": os.getpid(),
        "host": os.uname().nodename
    })

    watchdog_enabled = False
    watchdog_usec = 0
    try:
        # Check if watchdog is enabled by systemd
        watchdog_usec = int(os.environ.get("WATCHDOG_USEC", "0"))
        watchdog_enabled = watchdog_usec > 0
        if watchdog_enabled:
            logger.info("Systemd watchdog enabled", extra={
                "watchdog_usec": watchdog_usec
            })
    except (ValueError, TypeError):
        pass

    while not _shutdown.is_set():
        try:
            keyboard = find_keyboard(device)
            run_daemon_loop(keyboard, led, key_code)
        except (OSError, RuntimeError) as e:
            if _shutdown.is_set():
                break
            logger.error("Connection lost, reconnecting...", extra={
                "event": "connection_lost",
                "error": str(e),
                "retry_in_seconds": 2
            })
            time.sleep(2)

        # Systemd watchdog heartbeat (notify every 1/3 of watchdog interval)
        if watchdog_enabled and watchdog_usec > 0:
            now = time.time()
            if now - last_notify > (watchdog_usec / 1000000) / 3:
                try:
                    notifier.notify("WATCHDOG=1")
                    last_notify = now
                    logger.debug("Watchdog notified", extra={
                        "event": "watchdog_notify"
                    })
                except Exception as e:
                    logger.warning("Failed to notify watchdog", extra={
                        "event": "watchdog_error",
                        "error": str(e)
                    })

    _notify_systemd("STOPPING=1")
    logger.info("Daemon stopped", extra={
        "event": "daemon_stopped",
        "exit_reason": "normal_shutdown" if _shutdown.is_set() else "error"
    })


if __name__ == "__main__":
    main()
