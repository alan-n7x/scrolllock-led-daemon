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

sudo systemctl daemon-reload
sudo systemctl enable scrolllock-led-daemon
sudo systemctl restart scrolllock-led-daemon

echo "Done!"