"""Security and data-boundary checks against the frozen KiroCrew proxy SDK.

Run with the installed Nightly Python interpreter from repository root:
python -m unittest discover -s infrastructure/observability/tests -p test_app.py -v
"""
import hashlib
import hmac
import http.client
import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app"
spec = importlib.util.spec_from_file_location("observability_server", APP / "backend/server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
FIXTURE_SECRET = "test-only-proxy-secret-not-a-credential"
NOW = 1789308000.0


def sample(source="client"):
    return {
        "schema_version": 1, "source": source, "collector": server.COLLECTOR,
        "collected_at": "2026-09-13T14:00:00Z", "status": "ok",
        "metrics": {key: 2 for key in server.METRICS[source]},
        "checks": {key: True for key in server.CHECKS[source]}, "errors": [],
    }


def signature(method, target, timestamp=None, secret=FIXTURE_SECRET, body=b""):
    stamp = str(int(time.time()) if timestamp is None else timestamp)
    value = f"{stamp}:{method}:{target}:{hashlib.sha256(body).hexdigest()}"
    return stamp + ":" + hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


class SchemaTests(unittest.TestCase):
    def test_sensitive_fields_and_arbitrary_strings_never_leave_boundary(self):
        raw = sample()
        raw.update(token="TOKEN_CANARY", prompt="PROMPT_CANARY", path="PATH_CANARY")
        raw["metrics"]["api_key"] = "KEY_CANARY"
        raw["checks"]["session"] = "SESSION_CANARY"
        raw["errors"] = ["process_probe_failed", "RAW_LOG_CANARY", {"token": "NESTED_CANARY"}]
        clean = server.clean_sample(raw, "client", NOW)
        self.assertEqual(clean["errors"], ["process_probe_failed"])
        self.assertNotIn("CANARY", json.dumps(clean))
        self.assertEqual(clean["status"], "partial")

    def test_unknown_is_not_zero_and_optimistic_status_is_recomputed(self):
        raw = sample()
        raw["metrics"] = {"cpu_percent": "unknown", "rss_mib": False, "process_count": 2.5}
        raw["checks"] = {"client_running": "true"}
        clean = server.clean_sample(raw, "client", NOW)
        self.assertEqual(set(clean["metrics"].values()), {None})
        self.assertEqual(set(clean["checks"].values()), {None})
        self.assertEqual(clean["status"], "unknown")

    def test_nonfinite_negative_out_of_range_and_huge_metrics_are_removed(self):
        for value in (-1, float("nan"), float("inf"), 2 ** 4096):
            raw = sample("server")
            raw["metrics"]["cpu_percent"] = value
            self.assertIsNone(server.clean_sample(raw, "server", NOW)["metrics"]["cpu_percent"])

    def test_client_cpu_can_exceed_one_core(self):
        raw = sample()
        raw["metrics"]["cpu_percent"] = 230.5
        self.assertEqual(server.clean_sample(raw, "client", NOW)["metrics"]["cpu_percent"], 230.5)

    def test_stale_and_future_clocks_are_distinct_from_current(self):
        stamp = server.timestamp(sample()["collected_at"])[1]
        self.assertEqual(server.clean_sample(sample(), "client", stamp + 180)["freshness"], "current")
        self.assertEqual(server.clean_sample(sample(), "client", stamp + 181)["freshness"], "stale")
        self.assertEqual(server.clean_sample(sample(), "client", stamp - 61)["freshness"], "clock_skew")

    def test_wrong_source_schema_or_collector_fails_closed(self):
        for changes in ({"source": "server"}, {"collector": "forged"}, {"schema_version": True}, {"collected_at": "2026-09-13T14:00:00"}):
            self.assertEqual(server.clean_sample(sample() | changes, "client", NOW)["freshness"], "unavailable")

    def test_event_labels_are_synthesized_and_history_bounded(self):
        event = {"schema_version": 1, "source": "client", "at": "2026-09-13T14:00:00Z", "kind": "collected", "level": "info", "code": "first_sample", "message": "SECRET_CANARY"}
        data = b"\n".join(json.dumps(event).encode() for _ in range(300))
        result = server.clean_events(data)
        self.assertEqual(len(result), 200)
        self.assertEqual(result[0]["message"], "First sample collected")
        self.assertNotIn("CANARY", json.dumps(result))
        for changes in ({"code": "unknown"}, {"source": "arbitrary"}, {"level": []}, {"at": "bad"}):
            self.assertEqual(server.clean_events(json.dumps(event | changes).encode()), [])

    def test_missing_malformed_oversize_and_symlink_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            self.assertEqual(server.snapshot(base, NOW)["sources"]["client"]["status"], "unknown")
            target = base / "other"
            target.write_text(json.dumps(sample()))
            (base / "client.json").symlink_to(target)
            self.assertEqual(server.snapshot(base, NOW)["sources"]["client"]["status"], "unknown")
            (base / "client.json").unlink()
            (base / "client.json").write_bytes(b"x" * (server.MAX_FILE_BYTES + 1))
            self.assertEqual(server.snapshot(base, NOW)["sources"]["client"]["status"], "unknown")
            (base / "client.json").write_text("not json")
            self.assertEqual(server.snapshot(base, NOW)["sources"]["client"]["status"], "unknown")
            (base / "client.json").write_text("[" * 2000 + "0" + "]" * 2000)
            self.assertEqual(server.snapshot(base, NOW)["sources"]["client"]["status"], "unknown")


class SpawnContractTests(unittest.TestCase):
    def test_manifest_matches_actual_gateway_port_range_and_entry_contract(self):
        from kiro_crew.apps import backend as platform_backend
        from kiro_crew.apps.manifest import AppManifest
        manifest = AppManifest.from_dict(json.loads((APP / "app.json").read_text()))
        self.assertEqual(manifest.validate(APP), [])
        port = int(manifest.backend.port)
        self.assertGreaterEqual(port, platform_backend._MIN_PORT)
        self.assertLessEqual(port, platform_backend._MAX_PORT)
        self.assertEqual(port, server.APP_PORT)
        self.assertEqual(manifest.backend.type, "python")
        entry = APP / manifest.backend.entryPoint
        self.assertTrue(entry.is_file())
        self.assertTrue(entry.resolve().is_relative_to(APP.resolve()))
        self.assertTrue((APP / "ui" / manifest.ui.entry).is_file())

    def test_entrypoint_requires_secret_and_binds_only_the_declared_loopback_port(self):
        with patch.dict(os.environ, {"KIROCREW_PROXY_SECRET": ""}):
            with self.assertRaises(SystemExit):
                server.main()
        with patch.dict(os.environ, {"KIROCREW_PROXY_SECRET": FIXTURE_SECRET, "PORT": "9000"}):
            with self.assertRaises(SystemExit):
                server.main()
        with patch.dict(os.environ, {"KIROCREW_PROXY_SECRET": FIXTURE_SECRET, "PORT": "9102"}), patch.object(server, "Server") as listener:
            server.main()
            listener.assert_called_once_with(("127.0.0.1", 9102), server.Handler)
            listener.return_value.serve_forever.assert_called_once_with()


class HttpBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.httpd = server.Server(("127.0.0.1", 0), server.Handler)
        cls.httpd.data_dir = Path(cls.temp.name)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, method="GET", path="/api/snapshot", header=None, body=None):
        headers = {"X-KiroCrew-Proxy": header} if header else {}
        with patch.dict(os.environ, {"KIROCREW_PROXY_SECRET": FIXTURE_SECRET}):
            conn = http.client.HTTPConnection(*self.httpd.server_address, timeout=5)
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            result = response.status, json.loads(response.read())
            conn.close()
            return result

    def test_health_is_only_unsigned_public_data(self):
        self.assertEqual(self.request(path="/health"), (200, {"status": "ok"}))
        self.assertEqual(self.request()[0], 401)
        self.assertEqual(self.request(path="/health?source=client")[0], 401)

    def test_valid_proxy_request_returns_allowlisted_snapshot(self):
        code, data = self.request(header=signature("GET", "/api/snapshot"))
        self.assertEqual(code, 200)
        self.assertEqual(data["mode"], "custom_demo_collectors")

    def test_wrong_secret_stale_future_method_path_and_body_signatures_fail(self):
        invalid = [
            signature("GET", "/api/snapshot", secret="wrong"),
            signature("GET", "/api/snapshot", timestamp=int(time.time()) - 61),
            signature("GET", "/api/snapshot", timestamp=int(time.time()) + 61),
            signature("POST", "/api/snapshot"), signature("GET", "/api/other"),
            signature("GET", "/api/snapshot", body=b"tampered"), "broken",
        ]
        for header in invalid:
            self.assertEqual(self.request(header=header)[0], 401)

    def test_raw_query_target_is_bound_and_unknown_routes_never_read_files(self):
        self.assertEqual(self.request(path="/api/snapshot?file=secret", header=signature("GET", "/api/snapshot"))[0], 401)
        self.assertEqual(self.request(path="/api/snapshot?file=secret", header=signature("GET", "/api/snapshot?file=secret"))[0], 404)

    def test_mutations_and_bodies_are_refused(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            self.assertEqual(self.request(method=method, header=signature(method, "/api/snapshot"))[0], 405)
        self.assertEqual(self.request(header=signature("GET", "/api/snapshot"), body=b"{}")[0], 400)

    def test_missing_secret_is_fail_closed_and_recent_reads_can_repeat(self):
        self.assertFalse(server.verify_proxy_request(signature("GET", "/api/snapshot"), method="GET", target="/api/snapshot", body=b"", secret=""))
        header = signature("GET", "/api/snapshot")
        self.assertEqual(self.request(header=header)[0], 200)
        self.assertEqual(self.request(header=header)[0], 200)


if __name__ == "__main__":
    unittest.main()
