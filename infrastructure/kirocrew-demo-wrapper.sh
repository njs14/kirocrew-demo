#!/usr/bin/env bash
set -euo pipefail
export KIROCREW_HOME=/var/lib/kirocrew
export KIROCREW_PORT=5476
export KIROCREW_BIND=127.0.0.1
export KIROCREW_ALLOWED_LOOPBACK_PORTS=5599
export KIROCREW_TELEMETRY_DISABLED=1
export KIROCREW_SKIP_MODEL_DOWNLOAD=1
exec /opt/kirocrew/venv/bin/kirocrew "$@"
