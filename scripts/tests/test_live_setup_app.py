"""Offline App Kit lifecycle contract tests; no SSH, AWS or native UI calls."""
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import live_setup_app as app
from demo_config import defaults


class Response:
    def __init__(self, status=200, data=None, raw=None):
        self.status = status
        self._bytes = io.BytesIO(raw if raw is not None else json.dumps(data).encode())
        self.content = self

    async def read(self, size):
        return self._bytes.read(size)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected request")
        expected_method, expected_route, response = self.responses.pop(0)
        if method != expected_method or url != "http://localhost:5599" + expected_route:
            raise AssertionError("Unexpected route")
        if kwargs.get("allow_redirects") is not False:
            raise AssertionError("Redirects allowed")
        return response

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)


def installed(**changes):
    # The frozen manager's local install keeps the dataclass origin default.
    row = {"name": app.APP, "version": "1.0.1", "origin": "registry", "source": app.STAGED,
           "resources": "gateway", "lifecycle": "gateway", "enabled": True,
           "backend_status": {"running": True, "healthy": True, "port": 9102}}
    row.update(changes)
    return row


def snapshot(client="current", server="current"):
    return {"schema_version": 1, "mode": "custom_demo_collectors", "sources": {
        "client": {"freshness": client, "age_seconds": 10},
        "server": {"freshness": server, "age_seconds": 20}}, "events_available": True,
        "raw_private_data": "NEVER-PERSIST-THIS"}


def flow(*, absent=False, existing=None, samples=None):
    sequence = [("GET", "/", Response(302, raw=b"")),
                ("GET", "/api/auth/me", Response(data={"user_id": "PRIVATE-IDENTITY"})),
                ("GET", f"/api/apps/{app.APP}", Response(404 if absent else 200,
                                                          existing or installed()))]
    if absent:
        sequence.extend([("POST", "/api/apps/install", Response(201, {"ok": True, "name": app.APP})),
                         ("GET", f"/api/apps/{app.APP}", Response(data=installed()))])
    sequence.extend([
        ("GET", "/api/security/trusted-apps", Response(data={"apps": [], "allowAll": False})),
        ("POST", f"/api/security/trusted-apps/{app.APP}",
         Response(data={"apps": [app.APP], "allowAll": False})),
        ("POST", f"/api/apps/{app.APP}/enable", Response(data={"ok": True, "name": app.APP})),
        ("GET", "/api/apps", Response(data=[installed()])),
        ("GET", f"/apps/{app.APP}/api/snapshot", Response(data=samples or snapshot())),
    ])
    return sequence


class AppSetupTests(unittest.IsolatedAsyncioTestCase):
    async def run_flow(self, http, *, digest=None):
        fresh_install = http.responses[2][2].status == 404
        read_count = 0
        async def reader(location):
            nonlocal read_count
            self.assertEqual(location, app.INSTALLED)
            read_count += 1
            if fresh_install and read_count == 1 and digest is None:
                return None
            return {"exact": "hash"} if digest is None else digest
        return await app.configure_session(http, "http://localhost:5599", "TOKEN-ONLY-IN-MEMORY",
                                           "1.0.1", {"exact": "hash"}, reader)

    async def test_plan_never_uses_network_or_credentials(self):
        with patch.object(app, "remote_files", side_effect=AssertionError("Network")), \
             patch.object(app, "owner_token", side_effect=AssertionError("Credentials")):
            result = await app.install_app(defaults())
        self.assertFalse(result["network_access"])
        self.assertEqual(set(result["reviewed_files"]), set(app.FILES))
        self.assertFalse(result["native_ui_acceptance"])

    async def test_existing_exact_install_is_enabled_without_update(self):
        http = Session(flow())
        result = await self.run_flow(http)
        self.assertFalse(result["installed_now"])
        self.assertTrue(result["backend_healthy"])
        self.assertTrue(result["fresh_client_and_server"])
        self.assertFalse(result["native_ui_acceptance"])
        self.assertEqual(http.responses, [])
        published = json.dumps(result)
        for secret in ("PRIVATE-IDENTITY", "TOKEN-ONLY-IN-MEMORY", "NEVER-PERSIST-THIS"):
            self.assertNotIn(secret, published)
        self.assertFalse(any("update" in url or "uninstall" in url or "allow-all" in url
                             for _, url, _ in http.calls))

    async def test_absent_app_install_accepts_actual_201(self):
        http = Session(flow(absent=True))
        result = await self.run_flow(http)
        self.assertTrue(result["installed_now"])
        writes = [(url, data.get("json")) for method, url, data in http.calls if method == "POST"]
        self.assertEqual(writes[0], ("http://localhost:5599/api/apps/install", {"source": app.STAGED}))
        self.assertEqual(len(writes), 3)

    async def test_different_provenance_or_version_refused_before_mutation(self):
        for changes in ({"version": "9.9.9"}, {"origin": "external"}, {"source": "/other"},
                        {"dev": True}, {"sourceUrl": "https://example.invalid/repo"}):
            with self.subTest(changes=changes):
                http = Session(flow(existing=installed(**changes)))
                with self.assertRaisesRegex(app.AppSetupError, "app_existing_install_differs"):
                    await self.run_flow(http)
                self.assertFalse(any(method == "POST" for method, _, _ in http.calls))

    async def test_same_version_changed_bytes_refused_before_trust(self):
        http = Session(flow())
        with self.assertRaisesRegex(app.AppSetupError, "app_existing_files_differ"):
            await self.run_flow(http, digest={"exact": "different"})
        self.assertFalse(any(method == "POST" for method, _, _ in http.calls))

    async def test_orphan_files_are_not_overwritten_after_api_404(self):
        http = Session(flow(absent=True))
        with self.assertRaisesRegex(app.AppSetupError, "app_orphaned_install_refused"):
            await self.run_flow(http, digest={"exact": "hash"})
        self.assertFalse(any(method == "POST" for method, _, _ in http.calls))

    async def test_stale_source_cannot_be_claimed_as_fresh(self):
        result = await self.run_flow(Session(flow(samples=snapshot(server="stale"))))
        self.assertTrue(result["backend_healthy"])
        self.assertFalse(result["fresh_client_and_server"])
        self.assertEqual(result["sources"]["server"]["freshness"], "stale")

    async def test_change_after_trust_refused_before_enable(self):
        http = Session(flow())
        reads = iter(({"exact": "hash"}, {"exact": "changed"}))
        async def reader(location):
            return next(reads)
        with self.assertRaisesRegex(app.AppSetupError, "app_files_changed_before_enable"):
            await app.configure_session(http, "http://localhost:5599", "TOKEN",
                                         "1.0.1", {"exact": "hash"}, reader)
        self.assertFalse(any(url.endswith("/enable") for _, url, _ in http.calls))

    async def test_backend_failure_does_not_claim_snapshot_or_native_acceptance(self):
        responses = flow()[:-2]
        responses.extend([("GET", "/api/apps", Response(data=[installed(backend_status={
            "running": True, "healthy": False, "port": 9102})])) for _ in range(6)])
        with patch.object(app.asyncio, "sleep"):
            result = await self.run_flow(Session(responses))
        self.assertFalse(result["backend_healthy"])
        self.assertFalse(result["fresh_client_and_server"])
        self.assertFalse(result["native_ui_acceptance"])

    async def test_blanket_trust_change_refused_before_enable(self):
        responses = flow()
        responses[4] = ("POST", f"/api/security/trusted-apps/{app.APP}",
                        Response(data={"apps": [app.APP], "allowAll": True}))
        http = Session(responses)
        with self.assertRaisesRegex(app.AppSetupError, "app_trust_unconfirmed"):
            await self.run_flow(http)
        self.assertFalse(any(url.endswith("/enable") for _, url, _ in http.calls))

    async def test_api_errors_never_include_response_body(self):
        http = Session([("GET", "/api/auth/me", Response(403, {"error": "SECRET-RESPONSE"}))])
        with self.assertRaises(app.AppSetupError) as caught:
            await app._request(http, "http://localhost:5599", "GET", "/api/auth/me")
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertEqual(str(caught.exception), "app_http_request_refused")

    async def test_oversized_reply_is_bounded(self):
        with self.assertRaisesRegex(app.AppSetupError, "app_http_reply_too_large"):
            await app._body(Response(raw=b"x" * (app.MAX_REPLY + 1)))

    async def test_runtime_contract_checked_before_token_mint(self):
        with patch.object(app, "remote_files", return_value={}), \
             patch.object(app, "owner_token", side_effect=AssertionError("Should not mint")):
            with self.assertRaisesRegex(app.AppSetupError, "app_runtime_contract_changed"):
                await app.install_app(defaults(), apply=True)

    def test_both_reviewed_runtime_sets_are_accepted(self):
        for version, hashes in app.CONTRACT_SETS.items():
            with self.subTest(version=version):
                self.assertEqual(app.runtime_contract(dict(hashes)), version)

    def test_mixed_or_unknown_runtime_files_are_refused(self):
        old, new = app.CONTRACT_SETS.values()
        mixed = {**old, "apps/manager.py": new["apps/manager.py"]}
        unknown = {**new, "apps/routes.py": "0" * 64}
        extra = {**new, "other.py": "0" * 64}
        for hashes in (mixed, unknown, extra):
            with self.subTest(hashes=hashes):
                with self.assertRaisesRegex(app.AppSetupError, "app_runtime_contract_changed"):
                    app.runtime_contract(hashes)

    async def test_staged_bytes_checked_before_token_mint(self):
        with patch.object(app, "remote_files", side_effect=[app.CONTRACT_HASHES, {}]), \
             patch.object(app, "owner_token", side_effect=AssertionError("Should not mint")):
            with self.assertRaisesRegex(app.AppSetupError, "app_staged_files_differ"):
                await app.install_app(defaults(), apply=True)

    def test_owner_token_never_propagates_child_diagnostics(self):
        with patch.object(app, "_ssh", return_value=b"SECRET-UNUSABLE-OUTPUT"):
            with self.assertRaisesRegex(app.AppSetupError, "app_owner_token_not_unambiguous"):
                app.owner_token(defaults())

    def test_remote_inventory_refuses_executable_extras(self):
        for extra in ("requirements.txt", ".venv/bin/python3", "backend/json.py",
                      "data/.kirocrew-deps/module.py"):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                for name in (*app.FILES, extra):
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("fixture")
                result = subprocess.run([sys.executable, "-I", "-c", app.REMOTE_FILE_AUDIT],
                    input=json.dumps({"root": str(root), "files": app.FILES, "inventory": True,
                                      "installed": True, "protected": False}).encode(),
                    capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")

    def test_remote_inventory_allows_generated_files_without_reading_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in (*app.FILES, "installed.json", ".app_secret", "data/logs/backend.log"):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("SECRET" if name == ".app_secret" else "fixture")
            result = subprocess.run([sys.executable, "-I", "-c", app.REMOTE_FILE_AUDIT],
                input=json.dumps({"root": str(root), "files": app.FILES, "inventory": True,
                                  "installed": True, "protected": False}).encode(),
                capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(set(json.loads(result.stdout)), set(app.FILES))
            self.assertNotIn(b"SECRET", result.stdout)

    async def test_owned_tunnel_uses_private_socket_and_terminates_only_own_child(self):
        process = MagicMock()
        process.poll.return_value = None
        with patch.object(app, "ssh_options", return_value=[]), \
             patch.object(app.subprocess, "Popen", return_value=process) as spawn, \
             patch.object(app.Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFSOCK,
                                                                         st_uid=os.getuid())):
            async with app.owned_tunnel(defaults()) as socket_path:
                self.assertTrue(socket_path.endswith("/gateway.sock"))
                self.assertIn("kc-app-", socket_path)
                args = spawn.call_args.args[0]
                self.assertIn("ExitOnForwardFailure=yes", args)
                self.assertIn("ControlPath=none", args)
                self.assertIn(socket_path + ":127.0.0.1:5476", args)
                self.assertNotIn("5599:127.0.0.1:5476", args)
        process.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
