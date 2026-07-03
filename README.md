# Scroll Lock LED Daemon

Small daemon for Linux that synchronizes the Scroll Lock key with the keyboard LED.

## Features

- Detects Scroll Lock key presses.
- Toggles the keyboard Scroll Lock LED.
- Runs as a systemd service.
- Very low CPU usage (event driven).

## Requirements

- Linux
- Python 3.10+
- python3-evdev

## Installation

```bash
git clone https://github.com/SEU_USUARIO/scrolllock-led-daemon.git

cd scrolllock-led-daemon

./scripts/install.sh
```

## Uninstall

```bash
./scripts/uninstall.sh
```

## License

MIT