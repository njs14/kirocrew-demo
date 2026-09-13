#!/usr/bin/env python3
"""Enable bounded local metrics in the dedicated demo; preserve other settings."""
import json, os, pwd, stat, tempfile
from pathlib import Path

if os.geteuid() != 0:
    raise SystemExit('Run as root on the dedicated EC2 demo')
path = Path('/var/lib/kirocrew/config.json')
crew = pwd.getpwnam('crew')
info = path.lstat()
if not stat.S_ISREG(info.st_mode) or info.st_uid != crew.pw_uid or path.resolve() != path:
    raise SystemExit('Unexpected demo config owner/type/path')
raw = path.read_bytes()
config = json.loads(raw)
if config.get('default_agent') != 'enforcement-demo':
    raise SystemExit('Dedicated demo identity did not match')
fields = dict(enabled=True, local_dir='', export_interval_seconds=10,
              retention_days=7, max_total_mb=64, otlp_endpoint='', beacon_enabled=False)
config.setdefault('telemetry', {}).update(fields)
backup = path.with_name('config.before-observability.json')
if not backup.exists():
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(raw)
fd, tmp = tempfile.mkstemp(prefix='.metrics-config-', dir=path.parent)
try:
    os.fchown(fd, crew.pw_uid, crew.pw_gid)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(config, out, indent=2)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, path)
finally:
    Path(tmp).unlink(missing_ok=True)
print(json.dumps({'telemetry': fields, 'other_sections_preserved': True}))
