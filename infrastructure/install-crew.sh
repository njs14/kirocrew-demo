#!/usr/bin/env bash
set -euo pipefail
# Run as root on the newly provisioned demo instance, from the uploaded bundle.
# The package is an exact code/assets snapshot of the installed Sep12 nightly.
test "$(id -u)" -eq 0
cd /opt/kirocrew-demo/install
printf '%s  %s\n' '5133df99766a436a0fe346c6c57b4475fa00389a62fe7e464ec8440942e33d39' kirocrew-nightly-snapshot.tar.gz | sha256sum --check --status
python3 -m venv /opt/kirocrew/venv
/opt/kirocrew/venv/bin/pip install --require-hashes --only-binary=:all: -r crew-requirements-linux.lock
site_dir=$(/opt/kirocrew/venv/bin/python3 -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
test ! -d "$site_dir/kiro_crew"
tar -xzf kirocrew-nightly-snapshot.tar.gz --no-same-owner -C "$site_dir"
cat > /opt/kirocrew/venv/bin/kirocrew <<'PY'
#!/opt/kirocrew/venv/bin/python3
from kiro_crew import platform_compat
from kiro_crew._ssl_compat import _ensure_ssl_certs
platform_compat.ensure_utf8_console()
_ensure_ssl_certs()
from kiro_crew._bootstrap import main
main()
PY
chmod 755 /opt/kirocrew/venv/bin/kirocrew
chown -R root:root /opt/kirocrew
chmod -R go-w /opt/kirocrew
/opt/kirocrew/venv/bin/pip freeze > /opt/kirocrew-demo/linux-dependencies.txt
# Download the exact verified official CLI package. Install only the reviewed
# executable payload; skip global shell integrations and interactive setup.
curl --fail --silent --show-error --proto '=https' --tlsv1.2 \
  https://prod.download.cli.kiro.dev/stable/2.21.4/kirocli-x86_64-linux.tar.xz \
  --output kirocli-x86_64-linux.tar.xz
printf '%s  %s\n' 'a7a3c727796582e2d9132a38170e6e82a5296f0bdfbda68c38ffeef7b199382d' kirocli-x86_64-linux.tar.xz | sha256sum --check --status
tar -xJf kirocli-x86_64-linux.tar.xz --no-same-owner
install -o root -g root -m 755 kirocli/bin/kiro-cli kirocli/bin/kiro-cli-chat kirocli/bin/kiro-cli-term /usr/local/bin/
# Render the upstream launcher-specific AppArmor remedy, without weakening the
# host-wide namespace policy or granting userns to the shared Python interpreter.
/opt/kirocrew/venv/bin/python3 - <<'PY'
from kiro_crew.service import apparmor
from pathlib import Path
import subprocess
needed, reason = apparmor.should_install()
print('AppArmor:', reason)
if needed:
 path, problem = apparmor.validate_exec_path('/opt/kirocrew/venv/bin/kirocrew', expected_uid=0)
 if path is None: raise SystemExit(problem)
 profile = apparmor.render_profile(apparmor.detect_abi(), path)
 valid, detail = apparmor.validate(apparmor.parser_path(), profile)
 if not valid: raise SystemExit(detail)
 target = Path('/etc/apparmor.d/kirocrew-userns')
 target.write_text(profile); target.chmod(0o644)
 subprocess.run([apparmor.parser_path(), '-r', '-W', str(target)], check=True)
PY
install -o root -g root -m 644 kirocrew-demo.service /etc/systemd/system/kirocrew-demo.service
systemctl daemon-reload
echo 'Code installed. Configure the dedicated demo home before starting the gateway.'
