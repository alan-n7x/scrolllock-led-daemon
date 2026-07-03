# Scroll Lock LED Daemon

Daemon for Linux that synchronizes a key press with the keyboard LED.

## Features

- Auto-detects keyboard and Scroll Lock LED
- Listens for key presses and toggles the LED
- Runs as a systemd service (`Type=notify`)
- Auto-reconnects if the keyboard is disconnected
- One-shot mode: `--set on/off` and `--toggle` for scripts
- `--list` to discover available input devices
- Configurable key (`--key`) and LED (`--led`)
- Configuration file support
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
- `/etc/scrolllock-led-daemon.conf` (example config)

### Manual install

```bash
sudo cp src/scrolllock_led_daemon.py /usr/local/bin/scrolllock-led-daemon
sudo chmod +x /usr/local/bin/scrolllock-led-daemon
```

### Dependencies

```bash
sudo apt install python3-evdev
```

## Usage

```text
Usage: scrolllock-led-daemon [OPTIONS]

Options:
  --device PATH     Keyboard device path (overrides auto-detection)
  --led PATH|NAME   LED brightness file or name (scrolllock, capslock, numlock)
  --key NAME        Key to listen for (default: KEY_SCROLLLOCK)
  --set on|off      Set LED state and exit (one-shot mode)
  --toggle          Toggle LED state and exit (one-shot mode)
  --list            List available input devices and exit
  --config PATH     Path to configuration file
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

### List devices

```bash
scrolllock-led-daemon --list
```

### Custom device

```bash
scrolllock-led-daemon --device /dev/input/event9 --led scrolllock
```

### Custom key

```bash
scrolllock-led-daemon --key KEY_F12 --led capslock
```

## Configuration

Settings can be persisted in `/etc/scrolllock-led-daemon.conf`
or `~/.config/scrolllock-led-daemon/scrolllock-led-daemon.conf`:

```ini
[daemon]
device = /dev/input/event4
led = scrolllock
key = KEY_SCROLLLOCK
verbose = false
```

CLI arguments override config file values.

## Troubleshooting

### Permission denied

If you see:

```
Permission denied while accessing /dev/input/event*
```

Run with `sudo` or install the udev rules:

```bash
sudo ./scripts/install.sh
```

The udev rules give your user access to input devices without root.

### No keyboard found

If auto-detection fails, list available devices:

```bash
scrolllock-led-daemon --list
```

Then use the exact path:

```bash
scrolllock-led-daemon --device /dev/input/event4
```

## Uninstall

```bash
./scripts/uninstall.sh
```

## License

GNU General Public License v3.0
