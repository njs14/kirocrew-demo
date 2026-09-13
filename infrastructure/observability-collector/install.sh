#!/usr/bin/env bash
# Deliberately installs only. Activation is a separate reviewed operator action.
set -euo pipefail
test "$(id -u)" -eq 0
cd "$(dirname "$0")"
getent group crew >/dev/null
install -d -o root -g root -m 0755 /opt/kirocrew-demo/observability
install -d -o root -g crew -m 0750 /var/lib/kirocrew-demo-observability
install -o root -g root -m 0644 collector.py /opt/kirocrew-demo/observability/collector.py
install -o root -g root -m 0644 kirocrew-demo-observability.service kirocrew-demo-observability.timer /etc/systemd/system/
systemctl daemon-reload
printf '%s\n' 'Installed. Timer remains unchanged; activate with systemctl enable --now kirocrew-demo-observability.timer.'
