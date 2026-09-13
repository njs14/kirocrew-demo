#!/usr/bin/env python3
"""Check local prerequisites without connecting to AWS, SSH or an application."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def inspect(feature: str) -> dict:
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("python", sys.version_info >= (3, 12), "Python 3.12+; current " + platform.python_version())
    if feature in {"preview", "all"}:
        check("preview_platform", sys.platform in {"darwin", "linux"},
              "The restricted preview server supports macOS and Linux. The exported HTML/media can be served by another static server.")
        receipt = ROOT / "output/kirocrew-recorded-demos-build.json"
        try:
            build = json.loads(receipt.read_text())
            missing, changed = [], []
            for item in build["serveFiles"].values():
                path = ROOT / item["path"]
                if not path.resolve().is_relative_to(ROOT) or path.is_symlink() or not path.is_file():
                    missing.append(item["path"])
                    continue
                data = path.read_bytes()
                if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                    changed.append(item["path"])
            check("recorded_artifacts", not missing and not changed,
                  {"files": len(build["serveFiles"]), "missing": missing, "changed": changed})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            check("recorded_artifacts", False, "Cannot read the recorded edition: " + type(exc).__name__)
    requirements = {
        "record": ["ffmpeg", "ffprobe", "node"],
        "cloud": ["aws", "ssh"],
        "native": ["ssh"],
    }
    selected = requirements if feature == "all" else {feature: requirements.get(feature, [])}
    for group, commands in selected.items():
        for command in commands:
            path = shutil.which(command)
            check(group + ":" + command, path is not None, path or "Install " + command + " and place it on PATH.")
    return {"feature": feature, "platform": sys.platform,
            "scope": "Local prerequisites and recorded artifact hashes only; no remote connection or authentication check.",
            "passed": all(c["passed"] for c in checks), "checks": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", choices=["preview", "record", "cloud", "native", "all"], default="preview")
    result = inspect(parser.parse_args().feature)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
