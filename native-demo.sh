#!/bin/bash
set -euo pipefail
DEMO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEMO_PYTHON="${KIRO_DEMO_PYTHON:-}"
if [[ -z "$DEMO_PYTHON" ]]; then
  if [[ -x "$DEMO_ROOT/.venv/bin/python3" ]]; then DEMO_PYTHON="$DEMO_ROOT/.venv/bin/python3"
  else DEMO_PYTHON="$(command -v python3 || true)"; fi
fi
if [[ -z "$DEMO_PYTHON" || ! -x "$DEMO_PYTHON" ]]; then
  echo 'Install Python 3.10+ or set KIRO_DEMO_PYTHON to its absolute executable path. See docs/RUNTIME.md.' >&2
  exit 1
fi
if ! env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin "$DEMO_PYTHON" -B -s -c 'import sys, aiohttp; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
  echo 'The native client requires Python 3.10+ with aiohttp in the selected interpreter. See docs/RUNTIME.md.' >&2
  exit 1
fi
# Retain HOME for the user's existing SSH keys, plus the explicit credential-free
# config selector. AWS credentials and Python module overrides remain excluded.
exec env -i HOME="$HOME" KIRO_DEMO_CONFIG="${KIRO_DEMO_CONFIG:-}" \
  PATH=/usr/bin:/bin:/usr/sbin:/sbin LANG=C.UTF-8 \
  "$DEMO_PYTHON" -B -s "$DEMO_ROOT/scripts/native-backend-demo.py" "$@"
