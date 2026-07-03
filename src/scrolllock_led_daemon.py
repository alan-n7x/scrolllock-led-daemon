#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path

from evdev import InputDevice, ecodes, list_devices

VERSION = "1.0.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


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
        logging.info("Keyboard: %s (%s)", device.path, device.name)
        return device

    for path in list_devices():
        device = InputDevice(path)
        keys = device.capabilities().get(ecodes.EV_KEY, [])

        if ecodes.KEY_SCROLLLOCK in keys:
            logging.debug("Keyboard found: %s (%s)", device.path, device.name)
            return device

    raise RuntimeError("No keyboard with Scroll Lock support found")


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
        logging.debug("Scroll Lock LED: %s", brightness)
        return brightness

    for led in Path("/sys/class/leds").glob("*scrolllock"):
        brightness = led / "brightness"

        if brightness.exists():
            logging.debug("Scroll Lock LED found: %s", brightness)
            return brightness

    raise RuntimeError("No Scroll Lock LED found")


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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Daemon that synchronizes the Scroll Lock key with the keyboard LED."
    )
    parser.add_argument(
        "--device",
        type=str,
        help="Keyboard device path (e.g. /dev/input/event4)",
    )
    parser.add_argument(
        "--led",
        type=str,
        help="LED brightness file (e.g. /sys/class/leds/input4::scrolllock/brightness)",
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
    return parser.parse_args()


def main() -> None:
    """Main entry point of the daemon."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Verbose mode enabled")

    keyboard = find_keyboard(args.device)
    led = find_scrolllock_led(args.led)

    logging.info("Daemon started")

    for event in keyboard.read_loop():
        if event.type != ecodes.EV_KEY:
            continue

        if event.code == ecodes.KEY_SCROLLLOCK and event.value == 1:
            enabled = not read_led(led)
            write_led(led, enabled)

            logging.info("Scroll Lock LED: %s", "on" if enabled else "off")


if __name__ == "__main__":
    main()