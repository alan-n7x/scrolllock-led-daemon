#!/bin/bash

set -e

echo "Installing dependencies..."
sudo apt update
sudo apt install -y python3-evdev

echo "Installing daemon..."
sudo cp src/scrolllock_led_daemon.py /usr/local/bin/scrolllock-led-daemon
sudo chmod +x /usr/local/bin/scrolllock-led-daemon

echo "Installing systemd service..."
sudo cp systemd/scrolllock-led-daemon.service /etc/systemd/system/

echo "Installing man page..."
sudo mkdir -p /usr/local/share/man/man8
sudo cp scrolllock-led-daemon.8 /usr/local/share/man/man8/
sudo mandb &>/dev/null || true

echo "Installing configuration file..."
sudo cp scrolllock-led-daemon.conf /etc/scrolllock-led-daemon.conf

echo "Installing udev rules..."
sudo cp 99-scrolllock-led-daemon.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules || true

echo "Installing bash completion..."
sudo mkdir -p /usr/share/bash-completion/completions
sudo cp completions/scrolllock-led-daemon.bash /usr/share/bash-completion/completions/

sudo systemctl daemon-reload
sudo systemctl enable scrolllock-led-daemon
sudo systemctl restart scrolllock-led-daemon

echo "Done!"