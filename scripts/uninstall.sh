#!/bin/bash

sudo systemctl disable --now scrolllock-led-daemon

sudo rm -f /etc/systemd/system/scrolllock-led-daemon.service
sudo rm -f /usr/local/bin/scrolllock-led-daemon

sudo systemctl daemon-reload

echo "Removed."