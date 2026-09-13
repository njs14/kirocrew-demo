#!/usr/bin/python3 -I
"""Mint a demo owner link through the administrator's existing sudo access.

Install as root:root 0755 at /usr/local/bin/kirocrew-owner-token. The desktop
uses the ubuntu SSH alias and this custom binPath. This does not grant crew
sudo access or change KiroCrew's private-member authentication boundary.
"""

from __future__ import annotations

import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys


SERVICE = "kirocrew-demo.service"
INSTALL_PATH = Path("/usr/local/bin/kirocrew-owner-token")
WRAPPER = Path("/usr/local/bin/kirocrew-demo")
PYTHON = Path("/opt/kirocrew/venv/bin/python3")
ENTRYPOINT = Path("/opt/kirocrew/venv/bin/kirocrew")
ENV = {
    "HOME": "/home/crew",
    "PATH": "/opt/kirocrew/venv/bin:/usr/local/bin:/usr/bin:/bin",
    "LANG": "C.UTF-8",
}


class Refused(Exception):
    """A failed prerequisite; messages never contain token output."""


def token_arguments(argv: list[str]) -> list[str]:
    if not argv or argv[0] != "token":
        raise Refused("Only the token subcommand is allowed.")
    options: dict[str, str] = {}
    remaining = argv[1:]
    if len(remaining) % 2:
        raise Refused("Token options require a separate value.")
    for index in range(0, len(remaining), 2):
        key, value = remaining[index:index + 2]
        if key not in {"--ttl", "--embed-parent-port"} or key in options:
            raise Refused("Unsupported or repeated token option.")
        options[key] = value
    ttl = options.get("--ttl", "20h")
    match = re.fullmatch(r"([1-9][0-9]{0,3})([hm])", ttl)
    if not match or int(match[1]) * (60 if match[2] == "h" else 1) > 1200:
        raise Refused("TTL must be from 1 minute through 20 hours.")
    result = ["token", "--ttl", ttl]
    if "--embed-parent-port" in options:
        port = options["--embed-parent-port"]
        if not re.fullmatch(r"[1-9][0-9]{0,4}", port) or not 1 <= int(port) <= 65535:
            raise Refused("Embedding parent port must be from 1 through 65535.")
        result += ["--embed-parent-port", port]
    return result


def trusted_file(path: Path) -> Path:
    """Reject writable executables and writable ancestors, including symlinks."""
    resolved = path.resolve(strict=True)
    for candidate in set((path, *path.parents, resolved, *resolved.parents)):
        info = candidate.lstat()
        if info.st_uid != 0 or (not stat.S_ISLNK(info.st_mode) and info.st_mode & 0o022):
            raise Refused("A management executable or parent is not root-controlled.")
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise Refused("A required management executable is unavailable.")
    return resolved


def service_pid() -> int:
    reply = subprocess.run(
        ["/usr/bin/systemctl", "show", SERVICE, "--no-pager",
         "--property=ActiveState,SubState,MainPID,User"],
        check=True, capture_output=True, text=True, timeout=5, env=ENV,
    )
    fields = dict(line.split("=", 1) for line in reply.stdout.splitlines() if "=" in line)
    raw_pid = fields.get("MainPID", "")
    if (fields.get("ActiveState") != "active" or fields.get("SubState") != "running"
            or fields.get("User") != "crew" or not raw_pid.isdecimal() or int(raw_pid) <= 1):
        raise Refused("The exact demo Gateway service is not running as crew.")
    return int(raw_pid)


def process_identity(pid: int, crew_uid: int) -> tuple[str, int, int]:
    process = Path("/proc") / str(pid)
    status = dict(line.split(":", 1) for line in (process / "status").read_text().splitlines()
                  if ":" in line)
    if [int(value) for value in status.get("Uid", "").split()] != [crew_uid] * 4:
        raise Refused("Gateway process credentials do not match crew.")
    expected_python = PYTHON.resolve(strict=True)
    if (process / "exe").resolve(strict=True) != expected_python:
        raise Refused("Gateway process executable does not match the demo runtime.")
    arguments = (process / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
    if (len(arguments) < 3 or arguments[1:3] != [os.fsencode(ENTRYPOINT), b"gateway"]
            or Path(os.fsdecode(arguments[0])).resolve(strict=True) != expected_python):
        raise Refused("Gateway process command does not match the demo entrypoint.")
    user_namespace = (process / "ns/user").stat()
    owner_namespace = Path("/proc/self/ns/user").stat()
    if (user_namespace.st_dev, user_namespace.st_ino) != (owner_namespace.st_dev, owner_namespace.st_ino):
        raise Refused("Gateway user namespace differs from the administrator's.")
    raw = (process / "stat").read_text()
    start = raw[raw.rfind(")") + 2:].split()[19]
    mount = (process / "ns/mnt").stat()
    return start, mount.st_dev, mount.st_ino


def mint_arguments(pid: int, namespace_fd: int, arguments: list[str]) -> list[str]:
    # The open namespace descriptor pins the verified namespace across PID reuse.
    # No user, network or PID namespace is entered. runuser drops root before
    # the stock wrapper reads configuration or requests the owner token.
    return [
        "/usr/bin/nsenter", "--target", str(pid),
        f"--mount=/proc/self/fd/{namespace_fd}", "--",
        "/usr/sbin/runuser", "-u", "crew", "--",
        "/usr/bin/env", "-i", *(f"{key}={value}" for key, value in ENV.items()),
        str(WRAPPER), *arguments,
    ]


def main(argv: list[str]) -> int:
    arguments = token_arguments(argv)
    if sys.platform != "linux":
        raise Refused("This wrapper runs only on the demo Linux host.")
    if Path(__file__).resolve(strict=True) != INSTALL_PATH:
        raise Refused("Use the root-installed management wrapper.")
    for path in (INSTALL_PATH, WRAPPER, PYTHON, ENTRYPOINT,
                 Path("/usr/bin/systemctl"), Path("/usr/bin/nsenter"),
                 Path("/usr/sbin/runuser"), Path("/usr/bin/env"), Path("/usr/bin/sudo")):
        trusted_file(path)
    if os.geteuid() != 0:
        if os.getuid() != pwd.getpwnam("ubuntu").pw_uid or os.getuid() != os.geteuid():
            raise Refused("Only the existing ubuntu administrator may invoke sudo here.")
        # No sudoers entry is installed. Existing admin rights are required.
        return subprocess.run(["/usr/bin/sudo", "-n", "--", str(INSTALL_PATH), *arguments],
                              env=ENV, check=False).returncode
    crew_uid = pwd.getpwnam("crew").pw_uid
    if crew_uid == 0:
        raise Refused("The crew account must be unprivileged.")
    pid = service_pid()
    before = process_identity(pid, crew_uid)
    namespace_fd = os.open(f"/proc/{pid}/ns/mnt", os.O_RDONLY | os.O_CLOEXEC)
    try:
        pinned = os.fstat(namespace_fd)
        if (pinned.st_dev, pinned.st_ino) != before[1:]:
            raise Refused("Gateway mount namespace changed during verification.")
        if service_pid() != pid or process_identity(pid, crew_uid) != before:
            raise Refused("Gateway restarted during verification; retry the connection.")
        return subprocess.run(mint_arguments(pid, namespace_fd, arguments),
                              pass_fds=(namespace_fd,), env=ENV, cwd="/",
                              check=False).returncode
    finally:
        os.close(namespace_fd)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (Refused, OSError, ValueError, KeyError, subprocess.SubprocessError):
        # Do not include exception objects: a child error must never echo its
        # token-bearing stdout into the desktop's diagnostics log.
        print("Owner token bootstrap refused or unavailable; check the demo management prerequisites.",
              file=sys.stderr)
        raise SystemExit(1)
