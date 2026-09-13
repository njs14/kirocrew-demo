#!/usr/bin/env bash
set -euo pipefail
# Select existing resources; this installer creates no VPC, subnet or ingress rule.
DEMO_BUCKET="${DEMO_S3_BUCKET:-}"
DEMO_REGION="${AWS_REGION:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket) [[ $# -ge 2 ]] || { echo '--bucket requires a value' >&2; exit 2; }; DEMO_BUCKET="$2"; shift 2 ;;
    --region) [[ $# -ge 2 ]] || { echo '--region requires a value' >&2; exit 2; }; DEMO_REGION="$2"; shift 2 ;;
    -h|--help) echo 'Usage: configure-arm-services.sh --bucket EXISTING_DEMO_BUCKET --region AWS_REGION'; exit 0 ;;
    *) echo 'Unknown argument; use --help.' >&2; exit 2 ;;
  esac
done
[[ "$DEMO_BUCKET" =~ ^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$ ]] || { echo 'Supply --bucket with a valid existing demo bucket name.' >&2; exit 2; }
[[ "$DEMO_REGION" =~ ^[a-z]{2}(-[a-z0-9]+)+-[0-9]+$ ]] || { echo 'Supply --region with the bucket AWS region.' >&2; exit 2; }
# Complete these guards before installing binaries or changing configuration.
for DEMO_EXISTING in /etc/kirocrew-demo/mcp.env /var/lib/kirocrew/config.json /home/crew/.kiro/agents/enforcement-demo.json; do
  [[ ! -e "$DEMO_EXISTING" && ! -L "$DEMO_EXISTING" ]] || { echo "Refusing to overwrite existing configuration: $DEMO_EXISTING" >&2; exit 1; }
done
test "$(id -u)" -eq 0
test "$(uname -m)" = aarch64
cd /opt/kirocrew-demo/install
printf '%s  %s\n' 'f582eac0e002b4d11bbd061d41fcb49d1d37626a2c1fe230373fcbf97755df6f' kirocli-aarch64-linux.tar.xz | sha256sum --check --status
python3 - <<'PY'
from pathlib import Path
import tarfile,struct
with tarfile.open('kirocli-aarch64-linux.tar.xz','r:xz') as archive:
    for name in ('kiro-cli','kiro-cli-chat','kiro-cli-term'):
        member=archive.getmember('kirocli/bin/'+name)
        if not member.isfile(): raise SystemExit('Expected regular CLI binary')
        data=archive.extractfile(member).read()
        if data[:6] != b'\x7fELF\x02\x01' or struct.unpack('<H',data[18:20])[0] != 183:
            raise SystemExit('CLI is not AArch64 ELF')
        target=Path('/usr/local/bin')/name
        if target.exists(): raise SystemExit('Refusing to overwrite '+str(target))
        target.write_bytes(data);target.chmod(0o755)
PY
/usr/local/bin/kiro-cli --version
install -d -o root -g root -m 0755 /opt/kirocrew-demo/mcp-enforcement
install -o root -g root -m 0644 mcp-enforcement/{server.py,probe.py,requirements.txt} /opt/kirocrew-demo/mcp-enforcement/
test ! -e /opt/kirocrew-demo/mcp-venv
python3 -m venv /opt/kirocrew-demo/mcp-venv
/opt/kirocrew-demo/mcp-venv/bin/pip install --require-hashes --only-binary=:all: -r /opt/kirocrew-demo/mcp-enforcement/requirements.txt
/opt/kirocrew-demo/mcp-venv/bin/pip check
python3 configure-demo.py
install -d -o crew -g crew -m 0700 /home/crew/.ssh
install -o crew -g crew -m 0600 /home/ubuntu/.ssh/authorized_keys /home/crew/.ssh/authorized_keys
# Exclusive creation closes the preflight-to-write overwrite race.
python3 - "$DEMO_BUCKET" "$DEMO_REGION" <<'PYCONFIG'
import os, sys
fd = os.open('/etc/kirocrew-demo/mcp.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write('DEMO_S3_BUCKET=' + sys.argv[1] + '\nAWS_REGION=' + sys.argv[2] + '\n')
    stream.flush()
    os.fsync(stream.fileno())
PYCONFIG
install -o root -g root -m 0755 kirocrew-demo-wrapper.sh /usr/local/bin/kirocrew-demo
test -f /etc/apparmor.d/abi/4.0
/opt/kirocrew/venv/bin/python3 - <<'PY'
from pathlib import Path
from kiro_crew.service.apparmor import render_profile
Path('/etc/apparmor.d/kirocrew-userns').write_text(render_profile('4.0',Path('/opt/kirocrew/venv/bin/kirocrew')))
PY
chmod 0644 /etc/apparmor.d/kirocrew-userns
apparmor_parser -r /etc/apparmor.d/kirocrew-userns
install -o root -g root -m 0644 kirocrew-demo.service kirocrew-mcp-demo.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now kirocrew-mcp-demo kirocrew-demo
systemctl is-active kirocrew-demo kirocrew-mcp-demo kirocrew-imds-guard
