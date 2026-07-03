#!/usr/bin/env python3

from pathlib import Path
from evdev import InputDevice, ecodes

KEYBOARD_DEVICE = "/dev/input/event4"
LED_PATH = Path("/sys/class/leds/input4::scrolllock/brightness")


def read_led() -> bool:
    return LED_PATH.read_text().strip() == "1"


def write_led(enabled: bool) -> None:
    LED_PATH.write_text("1" if enabled else "0")


def main() -> None:
    device = InputDevice(KEYBOARD_DEVICE)

    for event in device.read_loop():
        if event.type != ecodes.EV_KEY:
            continue

        if event.code == ecodes.KEY_SCROLLLOCK and event.value == 1:
            write_led(not read_led())


if __name__ == "__main__":
    main()
