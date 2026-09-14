#!/usr/bin/env python3
"""Inspect local prerequisites; no AWS, SSH or product sign-in occurs."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("demo_dependencies", ROOT / "scripts/demo-dependencies.py")
dependencies = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dependencies)


def inspect(feature="playback", **kwargs):
    return dependencies.inspect(feature, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", choices=dependencies.FEATURES + tuple(dependencies.ALIASES), default="playback")
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--venv", type=Path)
    parser.add_argument("--python")
    parser.add_argument("--app-path", type=Path)
    parser.add_argument("--with-browser", action="store_true")
    parser.add_argument("--build", default=dependencies.DEFAULT_BUILD)
    args = parser.parse_args()
    try:
        result = inspect(args.feature, root=args.project_root, venv=args.venv, python=args.python,
                         app_path=args.app_path, with_browser=args.with_browser, build=args.build)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
