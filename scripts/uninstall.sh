#!/bin/bash

sudo systemctl disable --now scrolllock-led-daemon

sudo rm -f /etc/systemd/system/scrolllock-led-daemon.service
sudo rm -f /usr/local/bin/scrolllock-led-daemon
sudo rm -f /usr/local/share/man/man8/scrolllock-led-daemon.8
sudo rm -f /etc/udev/rules.d/99-scrolllock-led-daemon.rules
sudo rm -f /usr/share/bash-completion/completions/scrolllock-led-daemon.bash
sudo rm -f /etc/scrolllock-led-daemon.conf

sudo systemctl daemon-reload
sudo udevadm control --reload-rules || true
sudo mandb &>/dev/null || true

echo "Removed."