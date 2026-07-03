# Scroll Lock LED Daemon

Daemon for Linux that synchronizes the Scroll Lock key with the keyboard LED.

## Features

- Auto-detects keyboard and Scroll Lock LED
- Listens for Scroll Lock key presses and toggles the LED
- Runs as a systemd service (`Type=notify`)
- Auto-reconnects if the keyboard is disconnected
- One-shot mode: `--set on/off` and `--toggle` for scripts
- Very low CPU usage (event driven, not polling)

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

The script installs:
- `/usr/local/bin/scrolllock-led-daemon`
- `/etc/systemd/system/scrolllock-led-daemon.service`
- `/usr/local/share/man/man8/scrolllock-led-daemon.8`
- `/etc/udev/rules.d/99-scrolllock-led-daemon.rules`
- `/usr/share/bash-completion/completions/scrolllock-led-daemon.bash`

## Usage

```text
Usage: scrolllock-led-daemon [OPTIONS]

Options:
  --device PATH     Keyboard device path (overrides auto-detection)
  --led PATH        LED brightness file (overrides auto-detection)
  --set on|off      Set LED state and exit (one-shot mode)
  --toggle          Toggle LED state and exit (one-shot mode)
  --verbose         Enable debug logs
  --version         Show version
  --help            Show help
```

### Daemon mode (default)

```bash
sudo systemctl start scrolllock-led-daemon
```

### One-shot mode

```bash
scrolllock-led-daemon --set on
scrolllock-led-daemon --set off
scrolllock-led-daemon --toggle
```

### Custom device

```bash
scrolllock-led-daemon --device /dev/input/event9 --led /sys/class/leds/input8::scrolllock/brightness
```

## Uninstall

```bash
./scripts/uninstall.sh
```

## License

MIT
