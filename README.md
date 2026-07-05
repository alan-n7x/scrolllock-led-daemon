# Scroll Lock LED Daemon

Daemon for Linux that synchronizes a key press with the keyboard LED.

## Project status

This project is stable and feature-complete.

It is published on:

- PyPI: `pip install scrolllock-led-daemon`
- Launchpad PPA / APT: `sudo apt install scrolllock-led-daemon`

Future work will focus on maintenance, bug fixes, and compatibility updates.

## Features

- Auto-detects keyboard and Scroll Lock LED
- Listens for key presses and toggles the LED
- Runs as a systemd service (`Type=notify`) with watchdog support
- Auto-reconnects if the keyboard is disconnected
- One-shot mode: `--set on/off` and `--toggle` for scripts
- Configurable key (`--key`) and LED (`--led`)
- Configuration file support
- Very low CPU usage (event driven, not polling)
- `--doctor` for system diagnostics
- Structured JSON logging for production observability
- Secure, automated releases with supply chain security (Sigstore)

## Requirements

- Linux
- Python 3.10+
- python3-evdev

## Installation

### Pacote .deb (Debian/Ubuntu — recomendado)

Baixe o `.deb` da [página de releases](https://github.com/alan-n7x/scrolllock-led-daemon/releases):

```bash
sudo apt install ./scrolllock-led-daemon_*.deb
```

Instala automaticamente como serviço systemd com start imediato.

### PyPI (pip)

```bash
pip install scrolllock-led-daemon
```

Apenas o binário — você precisa configurar o systemd e udev manualmente.

### Script manual (desenvolvimento)

```bash
git clone https://github.com/alan-n7x/scrolllock-led-daemon.git
cd scrolllock-led-daemon
./scripts/install.sh
```

## Usage

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

### Diagnostics

```bash
scrolllock-led-daemon --doctor
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

Settings can be persisted in `/etc/scrolllock-led-daemon.conf` or `~/.config/scrolllock-led-daemon/scrolllock-led-daemon.conf`:

```ini
[daemon]
device = /dev/input/event4
led = scrolllock
key = KEY_SCROLLLOCK
verbose = false
```

CLI arguments override config file values.

## Observability

The daemon emits structured JSON logs to stdout (captured by systemd/journald) for easy integration with logging systems like ELK, Datadog, or Splunk, or Splunk.

Example log entries:
```json
{
  "timestamp": "2023-07-05T12:34:56.789Z",
  "level": "INFO",
  "name": "root",
  "message": "LED state changed",
  "event": "led_state_changed",
  "device_path": "/dev/input/event0",
  "device_name": "AT Translated Set 2 keyboard",
  "led_type": "scrolllock",
  "new_state": "on"
}
```

Systemd watchdog is enabled to automatically restart the daemon if it becomes unresponsive.

## Development

### Dependencies

```bash
pip install ".[test]"
```

### Tests

```bash
make test          # or: python -m pytest tests/ -v
```

### Contract tests

```bash
python -m pytest tests/test_evdev_contract.py -v
```

### Syntax check

```bash
make lint          # or: python -m py_compile src/scrolllock_led_daemon.py
```

### Security

Releases are signed using Sigstore's keyless signing via GitHub Actions OIDC, providing cryptographic provenance without managing GPG keys in CI.

Each release includes an in-toto SLSA provenance attestation and SBOM (Software Bill of Materials) for supply chain security verification.

## Uninstallation

### Via .deb

```bash
sudo apt remove scrolllock-led-daemon
```

### Via script manual

```bash
./scripts/uninstall.sh
```

## License

GNU General Public License v3.0

<!-- Test commit for CI/CD pipeline verification - $(date) -->
