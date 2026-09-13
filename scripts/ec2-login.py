#!/usr/bin/env python3
"""Fresh Kiro CLI 2.21.4 sign-in on EC2 through a local SSH callback tunnel.

Uses only Python's standard library, the existing strict SSH alias, and lsof.
The browser URL is printed to a terminal; tokens and account email are not shown.
"""

import argparse
import errno
import json
import os
import secrets
import selectors
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlsplit

from demo_config import load_config, ssh_options


SSH_OPTIONS = [
    "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
    "-o", "ForwardAgent=no", "-o", "IdentitiesOnly=yes",
    "-o", "ControlMaster=no", "-o", "ControlPath=none",
    "-o", "RemoteCommand=none", "-o", "User=crew",
]

# This driver receives no local credentials. Its private temporary directory is
# independent of both the Gateway state and any other login attempt.
REMOTE_DRIVER = r"""
import errno, json, os, pathlib, pty, re, select, shutil, signal
import stat, subprocess, tempfile, time

def emit(kind, **values):
    print(json.dumps(dict(event=kind, **values)), flush=True)

def whoami():
    result = subprocess.run(
        ["/usr/local/bin/kiro-cli", "whoami", "-f", "json"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20,
    )
    if result.returncode:
        return None
    try:
        value = json.loads(result.stdout)
        method = value.get("accountType") if isinstance(value, dict) else None
    except (ValueError, TypeError):
        method = None
    # Deliberately exclude email, IDs, tokens and any unknown response fields.
    return method if method in {
        "SocialGitHub", "SocialGoogle", "BuilderId", "BuilderID",
        "IamIdentityCenter", "IAMIdentityCenter",
    } else "authenticated (method unavailable)"

def start_time(pid):
    return pathlib.Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]

def interrupted(signum, frame):
    raise InterruptedError("login interrupted")

for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
    signal.signal(sig, interrupted)

temporary = None
child = None
master = None
try:
    version = subprocess.run(
        ["/usr/local/bin/kiro-cli", "--version"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20,
    )
    if version.returncode or not re.search(rb"\b2\.21\.4\b", version.stdout):
        emit("error", message="This helper is verified only for remote Kiro CLI 2.21.4.")
        raise SystemExit(2)
    method = whoami()
    if method:
        emit("authenticated", method=method, existing=True)
        raise SystemExit(0)

    temporary = pathlib.Path(tempfile.mkdtemp(prefix="kirocrew-login-"))
    temporary.chmod(0o700)
    marker = {"pid": os.getpid(), "start": start_time(os.getpid()), "nonce": CONFIG["nonce"]}
    marker_path = temporary / "owner.json"
    descriptor = os.open(marker_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(marker, output)
    launcher = temporary / "xdg-open"
    launcher.write_text('''#!/usr/bin/python3
import os, sys
if len(sys.argv) != 2:
    raise SystemExit(1)
try:
    target = os.environ["KIROCREW_LOGIN_URL_FILE"]
    lock = os.open(target + ".lock",
                   os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
except FileExistsError:
    raise SystemExit(0)
os.close(lock)
fd = os.open(target + ".pending",
             os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, "w") as output:
    output.write(sys.argv[1])
os.replace(target + ".pending", target)
''')
    launcher.chmod(0o700)
    emit("started", directory=str(temporary), **marker)
    child, master = pty.fork()
    if child == 0:
        env = dict(os.environ)
        # Kiro CLI 2.21.4 uses these hints to select a separate SSH login
        # interaction. This helper already supplies the protected callback
        # tunnel, so select the browser flow observed under sudo -u crew -H.
        for name in ("SSH_CLIENT", "SSH_CONNECTION", "SSH_TTY"):
            env.pop(name, None)
        env.update({"PATH": str(temporary) + ":" + env.get("PATH", "/usr/bin:/bin"),
                    "KIROCREW_LOGIN_URL_FILE": str(temporary / "url"),
                    "TERM": "xterm-256color"})
        os.execve("/usr/local/bin/kiro-cli", ["kiro-cli", "login"], env)
    deadline = time.monotonic() + CONFIG["timeout"]
    startup_deadline = time.monotonic() + 60
    last_heartbeat = time.monotonic()
    sent_url = False
    while time.monotonic() < deadline:
        finished, status = os.waitpid(child, os.WNOHANG)
        if finished:
            child = None
            method = whoami()
            if method:
                emit("authenticated", method=method, existing=False)
                raise SystemExit(0)
            emit("error", message="The remote login ended without an authenticated account.")
            raise SystemExit(1)
        url_file = temporary / "url"
        if not sent_url and url_file.exists():
            info = url_file.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                raise RuntimeError("unsafe URL file")
            url = url_file.read_text()
            if not url or len(url) > 16384:
                raise RuntimeError("invalid URL size")
            emit("url", url=url)
            sent_url = True
        if not sent_url and time.monotonic() >= startup_deadline:
            emit("error", message="The remote CLI did not launch its browser flow within 60 seconds.")
            raise SystemExit(1)
        if time.monotonic() - last_heartbeat >= 3:
            # A closed SSH output channel triggers cleanup during a disconnect.
            emit("waiting")
            last_heartbeat = time.monotonic()
        ready, _, _ = select.select([master], [], [], 0.2)
        if ready:
            try:
                os.read(master, 65536)  # Discard CLI output; it can contain identity data.
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
    emit("error", message="Sign-in timed out. Run the helper again for a fresh URL.")
    raise SystemExit(1)
except (BrokenPipeError, InterruptedError):
    pass
except Exception:
    # Do not serialize exceptions or CLI output: either could include auth state.
    try:
        emit("error", message="The remote sign-in helper failed; no credentials were copied.")
    except BrokenPipeError:
        pass
finally:
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(sig, signal.SIG_IGN)
    if child:
        try:
            finished, _ = os.waitpid(child, os.WNOHANG)
            if not finished:
                # pty.fork creates a new session for this login and its children.
                os.killpg(child, signal.SIGTERM)
                until = time.monotonic() + 3
                while time.monotonic() < until:
                    finished, _ = os.waitpid(child, os.WNOHANG)
                    if finished:
                        break
                    time.sleep(0.1)
                if not finished:
                    os.killpg(child, signal.SIGKILL)
                    os.waitpid(child, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
    if master is not None:
        os.close(master)
    if temporary is not None:
        shutil.rmtree(temporary)
"""

# The cancellation command checks the private marker and Linux process start
# time before signaling this driver, so it cannot kill an unrelated reused PID.
REMOTE_CANCEL = r'''
import json, os, pathlib, signal, stat, sys
expected = json.load(sys.stdin)
directory = pathlib.Path(expected["directory"])
if directory.parent != pathlib.Path("/tmp") or not directory.name.startswith("kirocrew-login-"):
    raise SystemExit(1)
try:
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise SystemExit(1)
    fd = os.open(directory / "owner.json", os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise SystemExit(1)
        actual = json.load(source)
    if any(actual.get(key) != expected.get(key) for key in ("pid", "start", "nonce")):
        raise SystemExit(1)
    pid = actual["pid"]
    if not isinstance(pid, int) or pid <= 1:
        raise SystemExit(1)
    started = pathlib.Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
    if started == actual["start"]:
        os.kill(pid, signal.SIGTERM)
except FileNotFoundError:
    pass
'''


def validated_callback(url):
    """Accept only the observed Kiro web entry point and an explicit local port."""
    if not isinstance(url, str) or len(url) > 16384 or any(ord(c) < 32 for c in url):
        raise ValueError("Invalid sign-in URL.")
    entry = urlsplit(url)
    if (entry.scheme != "https" or entry.netloc != "app.kiro.dev"
            or entry.path != "/signin" or entry.fragment):
        raise ValueError("The remote CLI returned an unexpected sign-in destination.")
    values = parse_qs(entry.query, keep_blank_values=True).get("redirect_uri", [])
    if len(values) != 1:
        raise ValueError("The remote CLI did not supply one callback URL.")
    callback = urlsplit(values[0])
    port = callback.port
    if (callback.scheme != "http" or callback.hostname not in {"localhost", "127.0.0.1"}
            or not port or callback.netloc != f"{callback.hostname}:{port}"
            or callback.fragment):
        raise ValueError("The remote CLI callback must use an explicit localhost port.")
    return port


def reserve_loopback(port):
    """Check and reserve both localhost address families before starting SSH."""
    reservations = []
    try:
        for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
            try:
                candidate = socket.socket(family, socket.SOCK_STREAM)
            except OSError as error:
                if family == socket.AF_INET6 and error.errno == errno.EAFNOSUPPORT:
                    continue
                raise
            try:
                if family == socket.AF_INET6:
                    candidate.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                candidate.bind((address, port))
                candidate.listen(1)
                reservations.append((candidate, address))
            except OSError as error:
                candidate.close()
                if family == socket.AF_INET6 and error.errno in {errno.EAFNOSUPPORT, errno.EADDRNOTAVAIL}:
                    continue
                raise
        return reservations
    except OSError:
        for candidate, _ in reservations:
            candidate.close()
        raise RuntimeError(f"Callback port {port} is occupied or unavailable; no sign-in URL was shown.") from None


def owned_listeners(process, port, addresses, lsof):
    if process.poll() is not None:
        return False
    result = subprocess.run(
        [lsof, "-nP", "-a", "-p", str(process.pid), "-iTCP:" + str(port),
         "-sTCP:LISTEN", "-Fpn"], capture_output=True, text=True, timeout=5,
    )
    fields = result.stdout.splitlines()
    expected = {"n" + (f"[{address}]" if ":" in address else address) + f":{port}"
                for address in addresses}
    return (result.returncode == 0 and f"p{process.pid}" in fields
            and expected.issubset(set(fields)) and process.poll() is None)


def stop_process(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Explicit deployment JSON; or set KIRO_DEMO_CONFIG")
    parser.add_argument("--timeout", type=int, default=900, metavar="SECONDS",
                        help="maximum sign-in duration, 60–3600 seconds (default: 900)")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        alias = config["ssh"]["gateway_alias"]
        options = [*SSH_OPTIONS, *ssh_options(config)]
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if not 60 <= args.timeout <= 3600:
        parser.error("--timeout must be between 60 and 3600 seconds")
    if not sys.stdout.isatty():
        parser.error("run in an interactive terminal; the sign-in URL must not be redirected to a file")
    ssh = shutil.which("ssh")
    lsof = shutil.which("lsof")
    if not ssh or not lsof:
        parser.error("ssh and lsof are required; install them using your operating system package manager")

    driver = tunnel = None
    ownership = None
    nonce = secrets.token_hex(24)
    deadline = time.monotonic() + args.timeout
    selector = selectors.DefaultSelector()
    try:
        source = "CONFIG = " + repr({"nonce": nonce, "timeout": args.timeout}) + "\n" + REMOTE_DRIVER
        driver = subprocess.Popen(
            [ssh, *options, "-o", "ClearAllForwardings=yes", alias, "python3 -u -"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        driver.stdin.write(source.encode())
        driver.stdin.close()
        selector.register(driver.stdout, selectors.EVENT_READ)
        buffered = b""
        print("Checking Kiro CLI on EC2…", flush=True)
        while time.monotonic() < deadline:
            if tunnel is not None and tunnel.poll() is not None:
                raise RuntimeError("The callback tunnel stopped. Run the helper again for a fresh URL.")
            for key, _ in selector.select(timeout=1):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    raise RuntimeError("The remote sign-in connection ended before authentication was confirmed.")
                buffered += chunk
                if len(buffered) > 131072:
                    raise RuntimeError("Unexpected remote sign-in output.")
                while b"\n" in buffered:
                    raw, buffered = buffered.split(b"\n", 1)
                    try:
                        event = json.loads(raw)
                    except ValueError:
                        raise RuntimeError("Unexpected remote sign-in output.") from None
                    if not isinstance(event, dict):
                        raise RuntimeError("Unexpected remote sign-in output.")
                    kind = event.get("event")
                    if kind == "started":
                        if ownership is not None or event.get("nonce") != nonce:
                            raise RuntimeError("Unexpected remote login ownership marker.")
                        ownership = {key: event[key] for key in ("directory", "pid", "start", "nonce")}
                    elif kind == "url":
                        if tunnel is not None or ownership is None:
                            raise RuntimeError("Unexpected repeated sign-in URL.")
                        url = event.get("url")
                        port = validated_callback(url)
                        reservations = reserve_loopback(port)
                        addresses = [address for _, address in reservations]
                        forward_args = []
                        for address in addresses:
                            bound = f"[{address}]" if ":" in address else address
                            forward_args += ["-L", f"{bound}:{port}:127.0.0.1:{port}"]
                        # SSH must bind the released sockets itself. If anything
                        # wins this small race, ExitOnForwardFailure aborts.
                        for candidate, _ in reservations:
                            candidate.close()
                        tunnel = subprocess.Popen(
                            [ssh, *options, "-N", "-o", "ExitOnForwardFailure=yes",
                             *forward_args, alias],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        )
                        verify_until = min(deadline, time.monotonic() + 15)
                        while time.monotonic() < verify_until:
                            if owned_listeners(tunnel, port, addresses, lsof):
                                break
                            if tunnel.poll() is not None:
                                raise RuntimeError("SSH could not bind the callback port; no sign-in URL was shown.")
                            time.sleep(0.2)
                        else:
                            raise RuntimeError("Could not verify SSH ownership of the callback listener.")
                        print("Open this fresh URL in your browser and choose GitHub:", flush=True)
                        print(url, flush=True)
                        print("Keep this terminal open until authentication is confirmed. Ctrl-C cancels this attempt.", flush=True)
                        url = None
                    elif kind == "authenticated":
                        method = event.get("method", "authenticated (method unavailable)")
                        if method not in {"SocialGitHub", "SocialGoogle", "BuilderId", "BuilderID",
                                          "IamIdentityCenter", "IAMIdentityCenter",
                                          "authenticated (method unavailable)"}:
                            method = "authenticated (method unavailable)"
                        qualifier = "already authenticated" if event.get("existing") else "authenticated"
                        print(f"EC2 Kiro CLI {qualifier}; method: {method}.", flush=True)
                        return 0
                    elif kind == "error":
                        # Only fixed messages from the driver reach this branch.
                        allowed = {
                            "This helper is verified only for remote Kiro CLI 2.21.4.",
                            "The remote login ended without an authenticated account.",
                            "The remote CLI did not launch its browser flow within 60 seconds.",
                            "Sign-in timed out. Run the helper again for a fresh URL.",
                            "The remote sign-in helper failed; no credentials were copied.",
                        }
                        message = event.get("message")
                        raise RuntimeError(message if message in allowed else "Remote sign-in failed.")
            if driver.poll() is not None and not selector.select(timeout=0):
                raise RuntimeError("The remote SSH connection failed; check the configured gateway SSH alias.")
        raise RuntimeError("Sign-in timed out. Run the helper again for a fresh URL.")
    except KeyboardInterrupt:
        print("\nSign-in cancelled.", flush=True)
        return 130
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        # Error text from URL parsing, subprocesses or JSON must not leak auth state.
        error = sys.exc_info()[1]
        print(str(error) if isinstance(error, RuntimeError) else "Sign-in setup failed; no credentials were copied.",
              file=sys.stderr)
        return 1
    finally:
        previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            stop_process(tunnel)
            if ownership is not None:
                try:
                    subprocess.run(
                        [ssh, *options, "-o", "ConnectTimeout=5", "-o", "ClearAllForwardings=yes",
                         alias, "python3 -c " + shlex.quote(REMOTE_CANCEL)],
                        input=json.dumps(ownership).encode(), stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=8,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    pass
            stop_process(driver)
            selector.close()
        finally:
            signal.signal(signal.SIGINT, previous)


if __name__ == "__main__":
    raise SystemExit(main())
