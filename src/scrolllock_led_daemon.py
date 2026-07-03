#!/usr/bin/env python3

import logging
from pathlib import Path

from evdev import InputDevice, ecodes, list_devices


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def find_keyboard() -> InputDevice:
    for device_path in list_devices():
        device = InputDevice(device_path)
        keys = device.capabilities().get(ecodes.EV_KEY, [])

        if ecodes.KEY_SCROLLLOCK in keys:
            logging.info("Keyboard found: %s (%s)", device.path, device.name)
            return device

    raise RuntimeError("No keyboard with Scroll Lock support found")


def find_scrolllock_led() -> Path:
    for led in Path("/sys/class/leds").glob("*scrolllock"):
        brightness = led / "brightness"

        if brightness.exists():
            logging.info("Scroll Lock LED found: %s", brightness)
            return brightness

    raise RuntimeError("No Scroll Lock LED found")


def read_led(led: Path) -> bool:
    return led.read_text().strip() == "1"


def write_led(led: Path, enabled: bool) -> None:
    led.write_text("1" if enabled else "0")


def main() -> None:
    keyboard = find_keyboard()
    led = find_scrolllock_led()

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