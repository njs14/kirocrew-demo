"""Install only the reviewed observability App Kit through its owning Gateway.

Tokens and cookies exist only in memory. This module has no CLI that can print
raw HTTP/SSH replies. A successful API check is not native UI acceptance.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import tempfile
from urllib.parse import parse_qs, urlsplit

from demo_config import ROOT, ssh_options

APP = "demo-observability"
STAGED = "/opt/kirocrew-demo/observability-app"
INSTALLED = "/var/lib/kirocrew/apps/demo-observability"
PACKAGE = "/opt/kirocrew/venv/lib/python3.12/site-packages/kiro_crew"
FILES = ("app.json", "backend/server.py", "ui/dist/index.mjs")
MAX_REPLY = 262144
# These route shapes were inspected in September 12 and 13 Nightly runtimes.
# A different runtime must have its contract reviewed before this bridge runs.
CONTRACT_HASHES = {
    "apps/routes.py": "9aa68670c418be3682c600016337f2abe8f7cb9e70fbba4a7fff1b90750a760a",
    "apps/manager.py": "dd75af1d7c8eed3805145d4d6843b22259ff3ec11503121fef2634a8961b0715",
    "dashboard/handlers/auth_refresh.py": "bb1716c9eb94d14fec8833d5d6c94df6f28eb6517c21ee4c2da66cc160cd8ce6",
    "dashboard/handlers/security.py": "f6350b8e00bc948c4f5e2179a05cc392f7cc71e343f3aa6193957c1c5d03e109",
    "apps/backend.py": "e379f15db886c4a754bb12aca28122de6f26d08010596a0021946d031b97d326",
    "apps/interpreter.py": "70d30e3bf4bca99c991f285358fc288f4831b79873e6ecf3764446ebaa169260",
    "dashboard/token_auth.py": "2ce2dd02498a6494edfc604b51436e016c62ada2f2be944499579ce09e822cda",
}
# September 13 changes the dependency-lock creator election and adds a backend
# PID helper. Its auth change binds peer pins to signed payload bytes instead
# of token spelling. The bridge's normal cookie exchange, route shapes and
# local app install/trust/enable semantics remain unchanged. Compare complete
# inventories: individual files from different releases are never allowlisted.
CONTRACT_SETS = {
    "0.7.0-nightly.20260912t060850": CONTRACT_HASHES,
    "0.7.0-nightly.20260913t061222": {
        **CONTRACT_HASHES,
        "apps/manager.py": "762fbc3f2e49112f7a2534c1f10df51e72eca5940bb193a5a41fe2f1d300319c",
        "apps/backend.py": "bc65d8bee734a402feb6dff88ba260869dc2502222130563747f67379902ef4b",
        "dashboard/token_auth.py": "fb138ce7c985572de942586f94d6ef723192a387165cf6ca42073b4560867ce3",
    },
}

REMOTE_FILE_AUDIT = '''import hashlib,json,os,stat,sys
from pathlib import Path
request=json.loads(sys.stdin.readline())
root=Path(request["root"])
if root.is_symlink(): raise RuntimeError("symlink")
if not root.exists() and request["installed"]:
 print("null")
 sys.exit(0)
if request["inventory"]:
 allowed_files=set(request["files"])
 allowed_dirs={"backend","ui","ui/dist"}
 if request["installed"]:
  allowed_files.update({"installed.json",".app_secret","data/logs/backend.log"})
  allowed_dirs.update({"data","data/logs"})
 count=0
 for here, dirs, files in os.walk(root,followlinks=False):
  for name in dirs+files:
   count+=1
   if count>64: raise RuntimeError("inventory_size")
   item=Path(here)/name
   kind=item.lstat().st_mode
   rel=item.relative_to(root).as_posix()
   if stat.S_ISLNK(kind): raise RuntimeError("symlink")
   if name in dirs:
    if not stat.S_ISDIR(kind) or rel not in allowed_dirs: raise RuntimeError("extra_directory")
   elif not stat.S_ISREG(kind) or rel not in allowed_files: raise RuntimeError("extra_file")
result={}
for name in request["files"]:
 path=root/name
 for parent in (path,*path.parents):
  info=parent.lstat()
  if stat.S_ISLNK(info.st_mode): raise RuntimeError("symlink")
  if request["protected"] and (info.st_uid != 0 or info.st_mode & 0o022):
   raise RuntimeError("unprotected")
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  info=os.fstat(fd)
  if not stat.S_ISREG(info.st_mode) or info.st_size>8000000: raise RuntimeError("file")
  chunks=[]
  size=0
  while True:
   data=os.read(fd,65536)
   if not data: break
   chunks.append(data)
   size+=len(data)
   if size>8000000: raise RuntimeError("size")
  result[name]=hashlib.sha256(b"".join(chunks)).hexdigest()
 finally: os.close(fd)
print(json.dumps(result,sort_keys=True))
'''


class AppSetupError(RuntimeError):
    """A fixed, nonsecret diagnostic code; do not attach raw child exceptions."""


def require(condition, code):
    if not condition:
        raise AppSetupError(code)


def runtime_contract(hashes):
    """Recognize one whole reviewed source set, including its exact file set."""
    for version, expected in CONTRACT_SETS.items():
        if hashes == expected:
            return version
    raise AppSetupError("app_runtime_contract_changed")


def reviewed_app():
    root = ROOT / "infrastructure/observability/app"
    hashes = {}
    for name in FILES:
        path = root / name
        require(path.is_file() and not path.is_symlink(), "reviewed_app_file_missing")
        raw = path.read_bytes()
        require(len(raw) < MAX_REPLY, "reviewed_app_file_too_large")
        hashes[name] = hashlib.sha256(raw).hexdigest()
    manifest = json.loads((root / "app.json").read_text())
    require(manifest.get("name") == APP and manifest.get("defaultEnabled") is False,
            "reviewed_app_manifest_changed")
    require(manifest.get("backend") == {"entryPoint": "backend/server.py", "type": "python",
                                        "port": "9102", "healthCheck": "/health"},
            "reviewed_app_backend_changed")
    return manifest["version"], hashes


def _ssh(config, argv, *, stdin=None):
    try:
        reply = subprocess.run(
            ["ssh", *ssh_options(config), "-o", "ConnectTimeout=10", config["ssh"]["admin_alias"],
             shlex.join(argv)], input=stdin, capture_output=True, timeout=45,
        )
        require(reply.returncode == 0, "app_management_ssh_failed")
        require(len(reply.stdout) <= MAX_REPLY, "app_management_reply_too_large")
        return reply.stdout
    except AppSetupError:
        raise
    except Exception:
        raise AppSetupError("app_management_ssh_unavailable") from None


def owner_token(config):
    raw = _ssh(config, ["/usr/local/bin/kirocrew-owner-token", "token", "--ttl", "5m"])
    try:
        text = raw.decode("utf-8")
        found = []
        for url in re.findall(r"https?://[^\s<>\"']+", text):
            found.extend(parse_qs(urlsplit(url).query).get("token", []))
        if not found:
            found = re.findall(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", text)
        require(len(set(found)) == 1 and len(found[0]) <= 16384,
                "app_owner_token_not_unambiguous")
        return found[0]
    except AppSetupError:
        raise
    except Exception:
        raise AppSetupError("app_owner_token_unavailable") from None


def remote_files(config, location):
    """Read only fixed paths and return digests; never read generated app secrets."""
    require(location in (STAGED, INSTALLED, PACKAGE), "app_digest_location_invalid")
    files = tuple(CONTRACT_HASHES) if location == PACKAGE else FILES
    # Entirely static code; reviewed file names travel as JSON on stdin. Running
    # as root lets this verify ancestors without borrowing the Gateway cookie.
    # -c holds static code, stdin carries only bounded public path names.
    raw = _ssh(config, ["sudo", "-n", "/usr/bin/python3", "-I", "-c", REMOTE_FILE_AUDIT],
               stdin=(json.dumps({"root": location, "files": files,
                                  "inventory": location != PACKAGE, "installed": location == INSTALLED,
                                  "protected": location != INSTALLED}) + "\n").encode())
    try:
        result = json.loads(raw)
        if result is None and location == INSTALLED:
            return None
        require(isinstance(result, dict) and set(result) == set(files)
                and all(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value)
                        for value in result.values()), "app_file_digest_reply_invalid")
        return result
    except AppSetupError:
        raise
    except Exception:
        raise AppSetupError("app_file_digest_reply_invalid") from None


@asynccontextmanager
async def owned_tunnel(config):
    """A private Unix socket owned by this SSH child, never an ambient listener."""
    process = None
    # Short path stays below macOS's Unix socket path length. mkdtemp is 0700.
    with tempfile.TemporaryDirectory(prefix="kc-app-", dir="/tmp") as directory:
        socket_path = str(Path(directory).resolve() / "gateway.sock")
        try:
            process = subprocess.Popen(
                ["ssh", *ssh_options(config), "-o", "ConnectTimeout=10", "-o", "ExitOnForwardFailure=yes",
                 "-o", "StreamLocalBindUnlink=no", "-o", "ControlMaster=no", "-o", "ControlPath=none",
                 "-N", "-L", f"{socket_path}:127.0.0.1:{config['ssh']['remote_port']}",
                 config["ssh"]["gateway_alias"]],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            for _ in range(30):
                require(process.poll() is None, "app_private_tunnel_failed")
                try:
                    info = Path(socket_path).lstat()
                    require(stat.S_ISSOCK(info.st_mode) and info.st_uid == os.getuid(),
                            "app_private_socket_invalid")
                    break
                except FileNotFoundError:
                    await asyncio.sleep(0.5)
            else:
                raise AppSetupError("app_private_tunnel_timeout")
            yield socket_path
        except AppSetupError:
            raise
        except Exception:
            raise AppSetupError("app_private_tunnel_unavailable") from None
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    await asyncio.to_thread(process.wait, timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    await asyncio.to_thread(process.wait, timeout=5)


async def _body(response):
    chunks = []
    size = 0
    while True:
        chunk = await response.content.read(65536)
        if not chunk:
            break
        size += len(chunk)
        require(size <= MAX_REPLY, "app_http_reply_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


async def _request(http, base, method, route, body=None, *, accepted=(200,)):
    try:
        async with http.request(method, base + route, json=body, allow_redirects=False) as reply:
            raw = await _body(reply)
            require(reply.status in accepted, "app_http_request_refused")
            return reply.status, json.loads(raw)
    except AppSetupError:
        raise
    except Exception:
        raise AppSetupError("app_http_request_unavailable") from None


def _installed_identity(info, version):
    # Frozen install_app leaves InstalledApp.origin at its legacy "registry"
    # default even for an absolute local source. Only this fixed local source
    # plus empty remote provenance and separately checked bytes qualify.
    require(isinstance(info, dict) and info.get("name") == APP
            and info.get("version") == version and info.get("origin") in ("local", "registry")
            and info.get("source") == STAGED
            and info.get("resources") == "gateway" and info.get("lifecycle") == "gateway"
            and not info.get("sourceUrl") and not info.get("sourceRegistry")
            and not info.get("sourceCommit") and not info.get("sourceSigner")
            and not info.get("dev"), "app_existing_install_differs")


def _snapshot_status(data):
    require(isinstance(data, dict) and data.get("schema_version") == 1
            and data.get("mode") == "custom_demo_collectors"
            and isinstance(data.get("sources"), dict), "app_snapshot_schema_invalid")
    sources = {}
    for name in ("client", "server"):
        sample = data["sources"].get(name)
        require(isinstance(sample, dict), "app_snapshot_source_missing")
        age = sample.get("age_seconds")
        freshness = sample.get("freshness")
        require(freshness in ("current", "stale", "clock_skew", "unavailable"),
                "app_snapshot_freshness_invalid")
        sources[name] = {"freshness": freshness,
                         "age_seconds": age if type(age) in (int, float) and -60 <= age <= 86400 else None}
    current = all(row["freshness"] == "current" and row["age_seconds"] is not None
                  and 0 <= row["age_seconds"] <= 180 for row in sources.values())
    return {"sources": sources, "fresh_client_and_server": current,
            "collection_events_available": data.get("events_available") is True}


async def configure_session(http, base, token, version, hashes, digest_reader):
    """Finite App Kit workflow, separately injectable for offline contract tests."""
    try:
        async with http.get(base + "/", params={"token": token}, allow_redirects=False) as reply:
            require(reply.status in (200, 302, 303), "app_owner_cookie_exchange_failed")
            await _body(reply)
    except AppSetupError:
        raise
    except Exception:
        raise AppSetupError("app_owner_cookie_exchange_unavailable") from None
    _, identity = await _request(http, base, "GET", "/api/auth/me")
    # Frozen auth/me returns user_id and expiries, not a role field. The pinned
    # root owner helper is the credential authority; never invent an RBAC role.
    require(isinstance(identity, dict) and isinstance(identity.get("user_id"), str)
            and bool(identity["user_id"]), "app_owner_identity_unavailable")
    status, info = await _request(http, base, "GET", f"/api/apps/{APP}", accepted=(200, 404))
    installed_now = status == 404
    if not installed_now:
        _installed_identity(info, version)
        require(await digest_reader(INSTALLED) == hashes, "app_existing_files_differ")
    else:
        require(await digest_reader(INSTALLED) is None, "app_orphaned_install_refused")
        _, installed = await _request(http, base, "POST", "/api/apps/install", {"source": STAGED},
                                      accepted=(201,))
        require(isinstance(installed, dict) and installed.get("ok") is True
                and installed.get("name") == APP, "app_install_unconfirmed")
        _, info = await _request(http, base, "GET", f"/api/apps/{APP}")
        _installed_identity(info, version)
        require(await digest_reader(INSTALLED) == hashes, "app_installed_files_differ")
    _, before = await _request(http, base, "GET", "/api/security/trusted-apps")
    require(isinstance(before, dict) and isinstance(before.get("apps"), list)
            and type(before.get("allowAll")) is bool, "app_trust_state_invalid")
    _, trusted = await _request(http, base, "POST", f"/api/security/trusted-apps/{APP}", {})
    require(isinstance(trusted, dict) and isinstance(trusted.get("apps"), list)
            and APP in trusted["apps"]
            and trusted.get("allowAll") is before["allowAll"], "app_trust_unconfirmed")
    # Recheck the exact bytes immediately before enabling executable app code.
    require(await digest_reader(INSTALLED) == hashes, "app_files_changed_before_enable")
    _, enabled = await _request(http, base, "POST", f"/api/apps/{APP}/enable", {})
    require(isinstance(enabled, dict) and enabled.get("ok") is True
            and enabled.get("name") == APP, "app_enable_unconfirmed")
    backend_ready = False
    for attempt in range(6):
        _, apps = await _request(http, base, "GET", "/api/apps")
        require(isinstance(apps, list), "app_list_schema_invalid")
        rows = [row for row in apps if isinstance(row, dict) and row.get("name") == APP]
        require(len(rows) == 1, "app_list_identity_ambiguous")
        _installed_identity(rows[0], version)
        state = rows[0].get("backend_status", {})
        backend_ready = (rows[0].get("enabled") is True and isinstance(state, dict)
                         and state.get("running") is True and state.get("healthy") is True
                         and state.get("port") == 9102)
        if backend_ready:
            break
        if attempt < 5:
            await asyncio.sleep(2)
    result = {"app": APP, "version": version, "installed_now": installed_now,
              "exact_app_files_verified": True, "app_execution_trust": True,
              "blanket_trust_changed": False, "blanket_trust_enabled": before["allowAll"],
              "backend_healthy": backend_ready,
              "native_ui_acceptance": False, "credential_source": "same_product_host_owner_helper"}
    if backend_ready:
        _, snapshot = await _request(http, base, "GET", f"/apps/{APP}/api/snapshot")
        result.update(_snapshot_status(snapshot))
    else:
        result.update({"fresh_client_and_server": False,
                       "next_step": "Inspect the App Kit backend health before presenting."})
    return result


async def install_app(config, apply=False):
    """Plan without network, or install/trust/enable the one reviewed local app.

    The caller stages the app and installs the owner helper first. The Gateway
    must be reachable through a private SSH socket created by this call from
    the configuration's pinned host. This function never changes the global
    third-party trust switch or updates an
    existing app whose provenance or bytes differ from this checkout.
    """
    version, hashes = reviewed_app()
    if not apply:
        return {"app": APP, "version": version, "status": "planned", "network_access": False,
                "source": STAGED, "accepted_runtime_contracts": CONTRACT_SETS,
                "transport": "owned_private_unix_socket_ssh_forward",
                "reviewed_files": hashes, "operations": ["verify staged root-owned bytes",
                    "exchange same-product owner token", "install if absent", "trust this app",
                    "enable this app", "check backend health and client/server sample freshness"],
                "existing_different_install": "refused", "native_ui_acceptance": False}
    try:
        contract = runtime_contract(await asyncio.to_thread(remote_files, config, PACKAGE))
        require(await asyncio.to_thread(remote_files, config, STAGED) == hashes,
                "app_staged_files_differ")
        import aiohttp
        base = f"http://localhost:{config['ssh']['local_port']}"
        async with owned_tunnel(config) as socket_path:
            token = await asyncio.to_thread(owner_token, config)
            async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(), trust_env=False,
                                             connector=aiohttp.UnixConnector(path=socket_path),
                                             timeout=aiohttp.ClientTimeout(total=40),
                                             headers={"Origin": base}) as http:
                async def reader(location):
                    return await asyncio.to_thread(remote_files, config, location)
                result = await configure_session(http, base, token, version, hashes, reader)
                result["transport"] = "owned_private_unix_socket_ssh_forward"
                result["runtime_contract"] = contract
                return result
    except AppSetupError:
        raise
    except Exception:
        raise AppSetupError("app_setup_unavailable") from None
