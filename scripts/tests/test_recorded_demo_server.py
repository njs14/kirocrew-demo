"""HTTP fixtures for the hash-bound, loopback-only recorded-demo preview."""
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("recorded_demo_server", ROOT / "scripts/serve-recorded-demos.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class RecordedDemoQueryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.html = b"<!doctype html><title>Bound diagram</title>"
        self.media = b"test-media-bytes"
        (self.root / "diagram.html").write_bytes(self.html)
        (self.root / "clip.mp4").write_bytes(self.media)
        (self.root / "private.txt").write_bytes(b"PRIVATE-FIXTURE-NOT-SERVED")
        self.root_patch = patch.object(preview, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

        def item(name, content):
            return {"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}

        self.build = {
            "schemaVersion": 1,
            "edition": "diagram.html",
            "editionSha256": hashlib.sha256(self.html).hexdigest(),
            "serveFiles": {
                "/diagram.html": item("diagram.html", self.html),
                "/clip.mp4": item("clip.mp4", self.media),
                # Route spelling cannot turn a media item into eligible HTML.
                "/media-alias.html": item("clip.mp4", self.media),
            },
        }
        self.build_path = self.root / "build.json"
        self.build_path.write_text(json.dumps(self.build))
        allowed = preview.load_allowlist(self.build_path)
        self.server = preview.ThreadingHTTPServer(("127.0.0.1", 0), preview.make_handler(allowed))
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, target, method="GET", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=2)
        try:
            connection.request(method, target, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_exact_presentation_query_serves_bound_html_and_root_alias(self):
        for route in ("/diagram.html", "/"):
            for method in ("GET", "HEAD"):
                with self.subTest(route=route, method=method):
                    status, headers, body = self.request(route + "?present=1", method)
                    self.assertEqual(status, 200)
                    self.assertEqual(headers["Content-Type"], "text/html")
                    self.assertEqual(headers["Content-Length"], str(len(self.html)))
                    self.assertEqual(headers["ETag"], '"' + hashlib.sha256(self.html).hexdigest() + '"')
                    self.assertEqual(body, self.html if method == "GET" else b"")

    def test_other_queries_and_presentation_query_on_non_html_are_rejected(self):
        queries = ("present=0", "present=01", "present=%31", "Present=1", "present=1&", "present=1&x=2", "present=1&present=1", "unknown=1")
        targets = ["/diagram.html?" + query for query in queries]
        targets += ["/clip.mp4?present=1", "/media-alias.html?present=1", "/build.json?present=1"]
        for target in targets:
            with self.subTest(target=target):
                self.assertEqual(self.request(target)[0], 404)

    def test_private_unknown_traversal_and_literal_fragment_stay_rejected(self):
        for target in ("/private.txt", "/private.txt?present=1", "/missing.html?present=1", "/../private.txt", "/%2e%2e/private.txt", "/diagram.html?present=1#focus=native-crew-runtime"):
            with self.subTest(target=target):
                status, _, body = self.request(target)
                self.assertEqual(status, 404)
                self.assertNotIn(b"PRIVATE-FIXTURE-NOT-SERVED", body)

    def test_normal_html_media_and_byte_ranges_are_unchanged(self):
        self.assertEqual(self.request("/diagram.html")[2], self.html)
        self.assertEqual(self.request("/clip.mp4")[2], self.media)
        status, headers, body = self.request("/clip.mp4", headers={"Range": "bytes=2-5"})
        self.assertEqual((status, body), (206, self.media[2:6]))
        self.assertEqual(headers["Content-Range"], f"bytes 2-5/{len(self.media)}")

    def test_presentation_query_does_not_bypass_changed_file_or_symlink_guard(self):
        (self.root / "diagram.html").write_bytes(b"changed")
        self.assertEqual(self.request("/diagram.html?present=1")[0], 409)
        (self.root / "diagram.html").unlink()
        (self.root / "diagram.html").symlink_to(self.root / "private.txt")
        status, _, body = self.request("/diagram.html?present=1")
        self.assertEqual(status, 409)
        self.assertNotIn(b"PRIVATE-FIXTURE-NOT-SERVED", body)

    def test_host_and_initial_hash_guards_remain_enforced(self):
        self.assertEqual(self.request("/diagram.html?present=1", headers={"Host": "example.invalid"})[0], 403)
        self.build["serveFiles"]["/diagram.html"]["sha256"] = "0" * 64
        self.build_path.write_text(json.dumps(self.build))
        with self.assertRaisesRegex(ValueError, "Artifact differs from build receipt"):
            preview.load_allowlist(self.build_path)


if __name__ == "__main__":
    unittest.main()
