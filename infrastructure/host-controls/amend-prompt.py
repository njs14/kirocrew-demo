#!/usr/bin/env python3
"""Apply a reviewed prompt-only delta, preserving an exclusive root-owned backup.

Run as root with --proposal-base64 and --apply. The proposal contains public
agent JSON and exact expected file/machine hashes. No probe or model is run.
"""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import PurePosixPath
import pwd
import re
import stat
import time


def require(value, code):
    if not value:
        raise ValueError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def directory(path, crew_uid, root_only=False):
    require(isinstance(path, str) and re.fullmatch(r"/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+", path), "invalid_directory")
    require(not {".", ".."}.intersection(path.split("/")), "path_traversal")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in PurePosixPath(path).parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            info = os.fstat(child)
            if info.st_uid not in ({0} if root_only else {0, crew_uid}) or info.st_mode & 0o022:
                os.close(child)
                raise ValueError("unsafe_directory")
            os.close(fd)
            fd = child
        return fd
    except Exception:
        os.close(fd)
        raise


def read_at(parent, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 65536, "unsafe_agent_file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(65537)
        require(len(data) <= 65536, "agent_too_large")
        return data, info
    finally:
        os.close(fd)


def validate_delta(old, new):
    before, after = json.loads(old), json.loads(new)
    require(isinstance(before, dict) and isinstance(after, dict), "invalid_agent_json")
    require(isinstance(before.get("prompt"), str) and isinstance(after.get("prompt"), str), "invalid_prompt")
    require(0 < len(after["prompt"]) <= 10000 and after["prompt"] != before["prompt"], "invalid_prompt_change")
    require({k: v for k, v in before.items() if k != "prompt"} ==
            {k: v for k, v in after.items() if k != "prompt"}, "non_prompt_change_refused")
    require(after.get("name") == "host-controls-demo" and after.get("tools") == ["fs_read", "fs_write", "execute_bash"]
            and after.get("allowedTools") == [] and after.get("mcpServers") == {}
            and after.get("includeMcpJson") is False, "agent_security_shape_changed")


def write_new(parent, name, data, mode):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=parent)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return os.fstat(fd)
    finally:
        os.close(fd)


def apply(proposal):
    require(os.geteuid() == 0, "administrator_required")
    require(proposal.get("kind") == "host_prompt_amendment_proposal", "invalid_proposal")
    crew = pwd.getpwnam("crew")
    target = PurePosixPath(proposal["target"])
    require(str(target) == crew.pw_dir + "/.kiro/agents/host-controls-demo.json", "wrong_agent_target")
    old = proposal["old_agent_json"].encode()
    new = proposal["new_agent_json"].encode()
    require(digest(old) == proposal["old_sha256"] and digest(new) == proposal["new_sha256"], "proposal_hash_mismatch")
    validate_delta(old, new)
    expected = proposal["expected_metadata"]
    require(expected == {"uid": 0, "gid": 0, "mode": 0o644}, "unexpected_expected_metadata")
    machine_dir = directory("/etc", crew.pw_uid, root_only=True)
    try:
        machine, _ = read_at(machine_dir, "machine-id")
    finally:
        os.close(machine_dir)
    require(digest(machine) == proposal["machine_id_sha256"], "wrong_machine")
    parent = directory(str(target.parent), crew.pw_uid)
    backup_parent = None
    lock = None
    result = {"kind": "host_prompt_amendment", "applied": False, "backup_created": False,
              "old_sha256": proposal["old_sha256"], "new_sha256": proposal["new_sha256"],
              "only_prompt_changed": True, "probe_executed": False}
    try:
        backup_parent = directory(proposal["backup_directory"], crew.pw_uid, root_only=True)
        # Use the product's cross-process template writer lock. Its normal
        # writer creates this sidecar on first use; preserve that crew ownership.
        try:
            lock = os.open(".kirocrew-agents.lock", os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except FileNotFoundError:
            try:
                lock = os.open(".kirocrew-agents.lock", os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                               0o600, dir_fd=parent)
            except FileExistsError:
                lock = os.open(".kirocrew-agents.lock", os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            else:
                os.fchown(lock, crew.pw_uid, crew.pw_gid)
                os.fchmod(lock, 0o600)
                os.fsync(parent)
                result["product_lock_created"] = True
        info = os.fstat(lock)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
                info.st_uid in (0, crew.pw_uid) and not info.st_mode & 0o077, "unsafe_agent_lock")
        deadline = time.monotonic() + 10
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                require(time.monotonic() < deadline, "agent_lock_busy")
                time.sleep(0.1)
        current, info = read_at(parent, target.name)
        require(current == old and info.st_uid == 0 and info.st_gid == 0 and
                stat.S_IMODE(info.st_mode) == 0o644, "current_agent_changed")
        backup = "host-controls-demo.prompt-before-" + proposal["old_sha256"] + ".json"
        write_new(backup_parent, backup, old, 0o600)
        result.update(backup_created=True, backup_path=proposal["backup_directory"] + "/" + backup)
        os.fsync(backup_parent)
        stage = ".host-controls-demo.prompt-" + proposal["new_sha256"] + ".pending"
        staged = write_new(parent, stage, new, 0o644)
        result["staged_path"] = str(target.parent) + "/" + stage
        again, info2 = read_at(parent, target.name)
        require(again == old and (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode) ==
                (info2.st_dev, info2.st_ino, info2.st_uid, info2.st_gid, info2.st_mode), "current_agent_changed")
        stage_info = os.stat(stage, dir_fd=parent, follow_symlinks=False)
        require((stage_info.st_dev, stage_info.st_ino) == (staged.st_dev, staged.st_ino), "staged_agent_changed")
        os.replace(stage, target.name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
        actual, info3 = read_at(parent, target.name)
        require(actual == new and info3.st_uid == 0 and info3.st_gid == 0 and
                stat.S_IMODE(info3.st_mode) == 0o644, "amendment_readback_failed")
        result.update(applied=True, target=str(target))
        result.pop("staged_path", None)
        return result
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r"[a-z_]+", str(exc)) else "amendment_failed"
        result["error"] = code
        return result
    finally:
        if lock is not None:
            os.close(lock)
        os.close(parent)
        if backup_parent is not None:
            os.close(backup_parent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal-base64", required=True)
    parser.add_argument("--apply", action="store_true", required=True)
    args = parser.parse_args()
    try:
        require(len(args.proposal_base64) <= 65536, "proposal_too_large")
        proposal = json.loads(base64.b64decode(args.proposal_base64, validate=True))
        result = apply(proposal)
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r"[a-z_]+", str(exc)) else "amendment_preflight_failed"
        result = {"kind": "host_prompt_amendment", "applied": False, "error": code}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
