#!/bin/bash
set -euo pipefail
DEMO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEMO_PYTHON="${KIRO_DEMO_PYTHON:-}"
if [[ -z "$DEMO_PYTHON" ]]; then
  if [[ -x "$DEMO_ROOT/.venv/bin/python3" ]]; then DEMO_PYTHON="$DEMO_ROOT/.venv/bin/python3"
  else DEMO_PYTHON="$(command -v python3 || true)"; fi
fi
if [[ -z "$DEMO_PYTHON" || ! -x "$DEMO_PYTHON" ]]; then
  echo 'Install Python 3.12+ or set KIRO_DEMO_PYTHON to its absolute executable path. See docs/RUNTIME.md.' >&2
  exit 1
fi
# Validate the interpreter without inheriting credentials or Python overrides.
if ! env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin "$DEMO_PYTHON" -B -s -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'; then
  echo 'The synthetic controls require Python 3.12+ and the reviewed KiroCrew runtime dependencies. See docs/RUNTIME.md.' >&2
  exit 1
fi
# KIROCREW_HOME is assigned by the runner to a new disposable run directory.
exec env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LANG=C.UTF-8 \
  KIRO_DEMO_BASELINE="${KIRO_DEMO_BASELINE:-}" \
  "$DEMO_PYTHON" -B -s "$DEMO_ROOT/scripts/run-live-demo.py" "$@"
