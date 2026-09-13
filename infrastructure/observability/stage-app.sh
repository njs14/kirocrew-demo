#!/usr/bin/env bash
# Stage reviewed app bytes. Installation, trust and activation remain separate.
set -euo pipefail
if [[ $(id -u) -ne 0 || $(uname -s) != Linux ]]; then
  echo 'Run as root on the Linux demo host.' >&2
  exit 1
fi
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/app" && pwd)
app_target=/opt/kirocrew-demo/observability-app
install -d -o root -g root -m 0755 "$app_target" "$app_target/backend" "$app_target/ui" "$app_target/ui/dist"
install -o root -g root -m 0644 "$source_dir/app.json" "$app_target/app.json"
install -o root -g root -m 0644 "$source_dir/backend/server.py" "$app_target/backend/server.py"
install -o root -g root -m 0644 "$source_dir/ui/dist/index.mjs" "$app_target/ui/dist/index.mjs"
echo 'Reviewed app files staged. Use the owner dashboard to install, trust and enable demo-observability.'
