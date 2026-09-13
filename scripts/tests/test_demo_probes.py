"""Reusable operator boundary checks with generated receipts and local subprocess stubs.
No original deployment fixture, account, credential, AWS service or login is used.
"""
import copy
import http.client
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from demo_config import load_config
spec = importlib.util.spec_from_file_location("probe_presenter", ROOT / "scripts/serve-demo-probes.py")
presenter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(presenter)
def direct_fixture():
    prefix = "probe-" + "a" * 32
    receipt = {"kind": "direct_mcp_service_probe", "native_crew_backend_verified": False, "passed": True,
               "time": "2026-01-01T00:00:00Z", "trace_prefix": prefix, "schema": 1,
               "expected_allowed_sha256": presenter.EXPECTED_SHA, "server_file_sha256": "b" * 64,
               "url": "http://127.0.0.1:8001/mcp", "dependencies": {key: "1.0" for key in ("boto3", "httpx", "mcp")},
               "checks": [{"name": "authentication_required", "passed": True, "http_status": 401},
                          {"name": "catalog", "passed": True, "tools": presenter.TOOLS}]}
    for name in ("read_allowed", "mcp_denied", "iam_denied"):
        result = {"tool": name, "ok": name == "read_allowed", "layer": "mcp" if name == "mcp_denied" else "aws",
                  "principal": "kirocrew-demo-client", "trace_id": prefix + "-" + name,
                  "invocation_id": "11111111-1111-1111-1111-111111111111"}
        if name != "mcp_denied": result["aws_request_id"] = "TEST_REQUEST_ID"
        if name == "read_allowed": result.update(object_sha256=presenter.EXPECTED_SHA, object_bytes=12)
        else: result["error_code"] = "AccessDenied" if name == "iam_denied" else "tool_grant_denied"
        if name == "iam_denied": result["http_status"] = 403
        receipt["checks"].append({"name": name, "passed": True, "result": result})
    return receipt


def synthetic_fixture():
    steps = [{"step": name} for name in presenter.STEP_NAMES]
    steps[6].update(decisions={name: {"permitted": name == "ReadDemo", "limiting_layer": "profile"}
                               for name in ("ReadDemo", "WriteDemo", "DenyDemo")}, signature_state="unsigned fixture")
    steps[7]["output"] = "[REDACTED: credential]"
    steps[8]["correlated_request"] = "demo-deny"
    return {"steps": steps, "baseline": {"installed_version": "fixture-only", "snapshot_digest": "b" * 64}}


FIXTURE = direct_fixture()
TEST_CONFIG_DIR = None


def setUpModule():
    global TEST_CONFIG_DIR
    TEST_CONFIG_DIR = tempfile.TemporaryDirectory()
    folder = Path(TEST_CONFIG_DIR.name)
    (folder / "known_hosts").write_text("fixture-host ssh-ed25519 TEST_PUBLIC_KEY\n")
    config = folder / "config.json"
    config.write_text(json.dumps({"schema_version": 1, "ssh": {"host_key_alias": "fixture-host", "known_hosts_path": "known_hosts"}}))
    presenter.configure_runtime(load_config(config))


def tearDownModule():
    TEST_CONFIG_DIR.cleanup()


class ParserTests(unittest.TestCase):
    def test_known_receipt_and_unknown_secret_removed(self):
        value = copy.deepcopy(FIXTURE)
        value["secret"] = "DO_NOT_RETAIN"
        value["checks"][2]["result"]["raw_headers"] = "DO_NOT_RETAIN"
        result = presenter.parse_direct(json.dumps(value))
        self.assertTrue(result["passed"])
        self.assertFalse(result["native_backend_verified"])
        self.assertNotIn("DO_NOT_RETAIN", json.dumps(result))

    def test_native_boundary_rejected(self):
        value = copy.deepcopy(FIXTURE)
        value["native_crew_backend_verified"] = True
        with self.assertRaises(ValueError):
            presenter.parse_direct(json.dumps(value))

    def test_wrong_digest_cannot_pass(self):
        value = copy.deepcopy(FIXTURE)
        value["checks"][2]["result"]["object_sha256"] = "0" * 64
        self.assertFalse(presenter.parse_direct(json.dumps(value))["passed"])

    def test_html_and_mismatched_trace_rejected(self):
        value = copy.deepcopy(FIXTURE)
        value["checks"][3]["result"]["trace_id"] = "<script>bad</script>"
        with self.assertRaises(ValueError):
            presenter.parse_direct(json.dumps(value))

    def test_incomplete_checks_rejected(self):
        value = copy.deepcopy(FIXTURE)
        value["checks"].pop()
        with self.assertRaises(ValueError):
            presenter.parse_direct(json.dumps(value))

    def test_synthetic_accepted_steps(self):
        value = synthetic_fixture()
        value["steps"][2]["approval_mode"] = "scripted rehearsal"
        raw = ("Baseline: " + json.dumps(value["baseline"]) + "\n" +
               "\n".join(json.dumps(step) for step in value["steps"]) + "\nPASS. Evidence: ignored\n").encode()
        receipt = presenter.parse_synthetic(raw)
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["network_calls"], 0)
        self.assertEqual(receipt["steps"][7]["output"], "[REDACTED: credential]")
        self.assertFalse(receipt["backend_session_executed"])


class SubprocessTests(unittest.TestCase):
    def test_fixed_command_is_exact(self):
        self.assertEqual(presenter.COMMANDS["direct"][:2], ["/usr/bin/ssh", "-T"])
        self.assertEqual(presenter.COMMANDS["direct"][-2], "kirocrew-demo-admin")
        self.assertIn("StrictHostKeyChecking=yes", presenter.COMMANDS["direct"])
        self.assertEqual(presenter.COMMANDS["direct"][-1], "sudo -u mcp-demo env DEMO_MCP_TOKEN_FILE=/etc/kirocrew-demo/mcp-token /opt/kirocrew-demo/mcp-venv/bin/python /opt/kirocrew-demo/mcp-enforcement/probe.py --expected-allowed-sha256 " + presenter.EXPECTED_SHA)

    def test_bounded_stdout_and_stderr(self):
        with patch.dict(presenter.COMMANDS, {"direct": [sys.executable, "-c", "import sys; print('ok'); print('diagnostic',file=sys.stderr)"]}):
            result = presenter.bounded_command("direct", lambda _: None)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], b"ok\n")
        self.assertEqual(result["stderr"], b"diagnostic\n")

    def test_output_limit_kills_process(self):
        with patch.dict(presenter.COMMANDS, {"direct": [sys.executable, "-c", "print('x'*200000)"]}), patch.object(presenter, "OUTPUT_LIMIT", 4096):
            result = presenter.bounded_command("direct", lambda _: None)
        self.assertEqual(result["termination"], "output_limit")
        self.assertLessEqual(len(result["stdout"]), 8192)

    def test_timeout_kills_process(self):
        with patch.dict(presenter.COMMANDS, {"direct": [sys.executable, "-c", "import time; time.sleep(30)"]}), patch.object(presenter, "TIMEOUT", 0.15):
            result = presenter.bounded_command("direct", lambda _: None)
        self.assertEqual(result["termination"], "timeout")
        self.assertNotEqual(result["exit_code"], 0)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.release = threading.Event()
        def stub(mode, progress):
            progress(123)
            self.release.wait(3)
            return {"stdout": json.dumps(FIXTURE).encode(), "stderr": b"DO_NOT_RETAIN", "exit_code": 0, "termination": None}
        self.state = presenter.OperatorState(Path(self.temp.name), stub)
        self.server = presenter.ThreadingHTTPServer(("127.0.0.1", 0), presenter.handler_for(self.state))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        deadline = time.monotonic() + 3
        while self.state.snapshot()["active"] and time.monotonic() < deadline:
            time.sleep(0.01)
        self.temp.cleanup()

    def request(self, method="GET", path="/", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        merged = {"Host": presenter.HOST}
        if headers:
            merged.update(headers)
        connection.request(method, path, body=body, headers=merged)
        response = connection.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        connection.close()
        return result

    def post(self, data={"mode": "direct"}, headers=None):
        required = {"Origin": presenter.ORIGIN, "Content-Type": "application/json", "X-Demo-Nonce": self.state.nonce}
        if headers:
            required.update(headers)
        return self.request("POST", "/api/run", json.dumps(data), required)

    def test_initial_get_does_not_run(self):
        status, body, headers = self.request()
        self.assertEqual(status, 200)
        self.assertIn(b"Standalone operator screen", body)
        self.assertIn(b"Native backend proof remains pending", body)
        self.assertIn(b"native_backend_verified = false", body)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIsNone(self.state.active)

    def test_remote_host_and_cross_origin_rejected(self):
        self.assertEqual(self.request(headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request(headers={"Origin": "https://evil.example"})[0], 403)

    def test_post_requires_origin_and_nonce(self):
        self.assertEqual(self.post(headers={"Origin": "null"})[0], 403)
        self.assertEqual(self.post(headers={"X-Demo-Nonce": "wrong"})[0], 403)
        self.assertEqual(self.post(headers={"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertIsNone(self.state.active)

    def test_no_arbitrary_command_or_path(self):
        self.assertEqual(self.post({"mode": "direct", "command": "id"})[0], 400)
        self.assertEqual(self.post({"mode": "../../etc/passwd"})[0], 400)
        self.assertEqual(self.post({"mode": []})[0], 400)
        self.assertEqual(self.request(path="/artifacts/../../HANDOFF.md")[0], 404)
        self.assertEqual(self.request(path="/HANDOFF.md")[0], 404)

    def test_concurrent_run_rejected_and_artifact_allowlisted(self):
        self.assertEqual(self.post()[0], 202)
        self.assertEqual(self.post()[0], 409)
        self.release.set()
        deadline = time.monotonic() + 3
        while self.state.snapshot()["active"] and time.monotonic() < deadline:
            time.sleep(0.01)
        run = self.state.snapshot()["runs"]["direct"]
        self.assertEqual(run["status"], "passed")
        self.assertEqual(len(list(Path(self.temp.name).glob("*.json"))), 1)
        status, body, _ = self.request(path=run["artifact_url"])
        self.assertEqual(status, 200)
        self.assertNotIn(b"DO_NOT_RETAIN", body)
        self.assertFalse(json.loads(body)["native_backend_verified"])
        self.assertEqual(self.request(path=run["artifact_url"]+"?path=elsewhere")[0], 404)

    def test_bad_output_is_sanitized_and_failure_retained(self):
        self.state.runner = lambda *_: {"stdout": b"SECRET_CREDENTIAL", "stderr": b"SECRET_CREDENTIAL", "exit_code": 1, "termination": None}
        self.assertEqual(self.post()[0], 202)
        deadline = time.monotonic()+3
        while self.state.snapshot()["active"] and time.monotonic() < deadline:
            time.sleep(0.01)
        run = self.state.snapshot()["runs"]["direct"]
        self.assertEqual(run["status"], "failed")
        body = self.request(path=run["artifact_url"])[1]
        self.assertNotIn(b"SECRET_CREDENTIAL", body)
        self.assertFalse(json.loads(body)["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
