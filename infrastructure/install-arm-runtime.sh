#!/usr/bin/env bash
set -euo pipefail
# Run as root on Ubuntu 24.04 ARM64 with the reviewed bundle uploaded here.
# This installs the frozen custom repack only; it does not start the gateway,
# install Kiro CLI, authenticate, or download models.
test "$(id -u)" -eq 0
test "$(uname -m)" = aarch64
cd /opt/kirocrew-demo/install
printf '%s  %s\n' \
  '5133df99766a436a0fe346c6c57b4475fa00389a62fe7e464ec8440942e33d39' kirocrew-nightly-snapshot.tar.gz \
  'ec8fbe5784220eb94a51d44b2d28734dbe2d21a1080d1d7645408bb69ac12427' crew-requirements-linux-arm64.lock \
  '237daba5bf5cc2eaaa63100e7a78eaf08f4af61dc0097e2f85fbd629251ea7ad' crew-dist-info.tar.gz | sha256sum --check --status
test ! -e /opt/kirocrew/venv
python3 - <<'PY'
import platform, sys, sqlite3
if sys.version_info[:2] != (3, 12) or platform.machine() != 'aarch64':
    raise SystemExit('Requires CPython 3.12 on Linux aarch64')
with sqlite3.connect(':memory:') as db:
    db.execute('CREATE VIRTUAL TABLE fts_probe USING fts5(content)')
PY
python3 -m venv /opt/kirocrew/venv
/opt/kirocrew/venv/bin/pip install --no-index --find-links wheels --require-hashes --only-binary=:all: -r crew-requirements-linux-arm64.lock
/opt/kirocrew/venv/bin/python3 - <<'PY'
from pathlib import Path, PurePosixPath
import base64, csv, hashlib, json, struct, sysconfig, tarfile

site = Path(sysconfig.get_paths()['purelib'])
excluded = {'linux_x86_64', 'macos_arm64', 'macos_x86_64', 'win_amd64'}
installed, skipped, binaries = [], [], []
for archive, root in [('kirocrew-nightly-snapshot.tar.gz', 'kiro_crew'), ('crew-dist-info.tar.gz', 'kirocrew-0.7.0.dist-info')]:
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        selected = []
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or path.parts[0] != root or not (member.isfile() or member.isdir()):
                raise SystemExit(f'Unsafe archive member: {member.name}')
            if len(path.parts) >= 4 and path.parts[:3] == ('kiro_crew', '_vendor', 'llama_cpp_libs') and path.parts[3] in excluded:
                skipped.append(member.name)
                continue
            if member.isfile():
                data = tar.extractfile(member).read()
                if data[:4] == b'\x7fELF':
                    if data[4:6] != b'\x02\x01' or struct.unpack('<H', data[18:20])[0] != 183:
                        raise SystemExit(f'Non-AArch64 ELF: {member.name}')
                    binaries.append(member.name)
                elif data[:4] in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xfe\xed\xfa\xcf') or data[:2] == b'MZ':
                    raise SystemExit(f'Foreign platform binary: {member.name}')
                installed.append((member.name, hashlib.sha256(data).hexdigest(), len(data)))
            selected.append(member)
        tar.extractall(site, members=selected, filter='data')

launcher = Path('/opt/kirocrew/venv/bin/kirocrew')
launcher.write_text('''#!/opt/kirocrew/venv/bin/python3
from kiro_crew import platform_compat
from kiro_crew._ssl_compat import _ensure_ssl_certs
platform_compat.ensure_utf8_console()
_ensure_ssl_certs()
from kiro_crew._bootstrap import main
main()
''')
launcher.chmod(0o755)
metadata = site / 'kirocrew-0.7.0.dist-info'
(metadata / 'INSTALLER').write_text('kirocrew-demo-arm-repack\n')
provenance = {
    'source_archive_sha256': '5133df99766a436a0fe346c6c57b4475fa00389a62fe7e464ec8440942e33d39',
    'runtime_version': '0.7.0-nightly.20260912t060850',
    'original_distribution_metadata_version': '0.7.0',
    'packaging': 'custom Linux ARM64 repack of frozen installed nightly; not an official Linux release artifact',
    'retained_aarch64_binaries': binaries,
    'excluded_foreign_architecture_members': skipped,
    'source_files': [{'path': name, 'sha256': digest, 'bytes': size} for name, digest, size in installed if name.startswith('kiro_crew/')],
}
(metadata / 'ARM_REPACK.json').write_text(json.dumps(provenance, indent=2) + '\n')
record = metadata / 'RECORD'
with record.open('w', newline='') as stream:
    writer = csv.writer(stream)
    paths = sorted(p for top in (site / 'kiro_crew', metadata) for p in top.rglob('*') if p.is_file() and p != record)
    for path in paths + [launcher]:
        data = path.read_bytes()
        import os
        writer.writerow([os.path.relpath(path, site), 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('='), len(data)])
    writer.writerow([str(record.relative_to(site)), '', ''])
Path('/opt/kirocrew-demo/arm-runtime-installation.json').write_text(json.dumps(provenance, indent=2) + '\n')
PY
chown -R root:root /opt/kirocrew
chmod -R go-w /opt/kirocrew
/opt/kirocrew/venv/bin/pip check
/opt/kirocrew/venv/bin/python3 - <<'PY'
import aiohttp, cryptography, importlib.metadata, jsonschema, lxml.etree, numpy, PIL.Image, platform, sqlite3
import kiro_crew
if kiro_crew.__version__ != '0.7.0-nightly.20260912t060850':
    raise SystemExit('Nightly version differs')
with sqlite3.connect(':memory:') as db:
    db.execute('CREATE VIRTUAL TABLE fts_probe USING fts5(content)')
print('Runtime:', kiro_crew.__version__, 'Architecture:', platform.machine(), 'SQLite:', sqlite3.sqlite_version)
print('Distribution metadata:', importlib.metadata.version('kirocrew'))
PY
/opt/kirocrew/venv/bin/pip freeze > /opt/kirocrew-demo/linux-arm64-dependencies.txt
printf '%s\n' 'ARM runtime installed. Kiro CLI, AppArmor profile, configuration and service start are separate steps.'
