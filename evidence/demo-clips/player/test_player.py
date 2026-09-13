"""Synthetic-only integration checks; no KiroCrew or AWS connection is made."""
import copy
import hashlib
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[3]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


builder = module("demo_builder", "build-recorded-demo-presentation.py")
server_module = module("demo_server", "serve-recorded-demos.py")


class PlayerTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="test-", dir=Path(__file__).parent))
        self.assets = self.folder / "processed"
        self.assets.mkdir()
        self.media = self.assets / "fixture.mp4"
        self.media.write_bytes(b"synthetic video byte-range fixture")
        (self.assets / "poster.jpg").write_bytes(b"synthetic poster")
        (self.assets / "receipt.json").write_text('{"scope":"synthetic player fixture"}')
        self.manifest = {"schemaVersion": 1, "synthetic": True, "title": "Synthetic player test", "scenes": [{
            "id": "test-scene", "title": "Synthetic player test", "description": "No product behavior is represented.",
            "evidenceScope": "Synthetic fixture only", "recordedAt": "2026-09-13T20:00:00Z", "duration": 4,
            "source": {"raw": "/private/do-not-serve.mov", "kind": "synthetic"},
            "provenance": {"sourceSha256": "a" * 64, "sourceDuration": 4, "cut": {"start": 0, "end": 4}},
            "poster": {"url": "poster.jpg"}, "media": [{"url": "fixture.mp4", "type": "video/mp4", "bytes": self.media.stat().st_size, "sha256": hashlib.sha256(self.media.read_bytes()).hexdigest()}],
            "cues": [{"time": 0, "label": "Beginning", "detail": "Fixture start"}, {"time": 2, "label": "Checkpoint", "detail": "Fixture cue", "evidence": "receipt.json"}]
        }]}
        self.manifest_path = self.assets / "manifest.json"
        self.output = self.folder / "edition.html"

    def tearDown(self):
        shutil.rmtree(self.folder)

    def build(self):
        self.manifest_path.write_text(json.dumps(self.manifest))
        return builder.build(self.manifest_path, self.output, fixture=True)

    def test_original_slide_bytes_and_private_source(self):
        _, receipt = self.build()
        self.assertEqual(receipt["slideCount"], 15)
        self.assertEqual(receipt["source"]["preservedSlides"], 14)
        document = self.output.read_text()
        self.assertIn("SYNTHETIC PLAYER TEST", document)
        self.assertIn("media-src 'self' blob:", document)
        self.assertNotIn("/private/do-not-serve.mov", document)
        public = self.output.with_name("edition-manifest.json").read_text()
        self.assertNotIn("/private", public)
        self.assertNotIn('"raw"', public)

    def test_synthetic_rejected_for_final(self):
        self.manifest_path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "Synthetic"):
            builder.build(self.manifest_path, self.output, fixture=False)

    def test_hash_tamper_rejected(self):
        self.media.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash or size mismatch"):
            self.build()

    def test_cue_outside_clip_rejected(self):
        self.manifest["scenes"][0]["cues"][1]["time"] = 5
        with self.assertRaisesRegex(ValueError, "within the clip"):
            self.build()

    def test_script_in_title_escaped(self):
        self.manifest["scenes"][0]["title"] = '<script>alert("x")</script>'
        self.build()
        self.assertIn("&lt;script&gt;", self.output.read_text())
        self.assertNotIn('<script>alert("x")', self.output.read_text())

    def test_traversal_media_rejected(self):
        self.manifest["scenes"][0]["media"][0]["url"] = "../private.mp4"
        with self.assertRaisesRegex(ValueError, "traversing"):
            self.build()

    def test_javascript_evidence_rejected(self):
        self.manifest["scenes"][0]["cues"][1]["evidence"] = "javascript:alert(1)"
        with self.assertRaises(ValueError):
            self.build()

    def test_symlink_media_rejected(self):
        link = self.assets / "link.mp4"
        link.symlink_to(self.media)
        self.manifest["scenes"][0]["media"][0]["url"] = "link.mp4"
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.build()

    def test_derived_destination_symlink_rejected_before_any_write(self):
        victim = self.folder / "do-not-modify.md"
        victim.write_text("preserved")
        for suffix in ["-notes.md", "-manifest.json", "-build.json"]:
            link = self.folder / ("edition" + suffix)
            link.symlink_to(victim)
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.build()
            self.assertEqual(victim.read_text(), "preserved")
            self.assertFalse(self.output.exists())
            link.unlink()

    def test_protected_destination_collision_rejected(self):
        self.manifest["synthetic"] = False
        self.manifest["title"] = "Player destination protection test"
        self.manifest_path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "protected source"):
            builder.build(self.manifest_path, builder.SOURCE, fixture=False)
        for destination in [builder.SOURCE_NOTES, builder.SOURCE.with_suffix(".txt")]:
            with self.assertRaises(ValueError):
                builder.build(self.manifest_path, destination, fixture=False)

    def test_raw_evidence_rejected(self):
        raw = self.assets / "raw"
        raw.mkdir()
        (raw / "receipt.json").write_text("{}")
        self.manifest["scenes"][0]["cues"][1]["evidence"] = "raw/receipt.json"
        with self.assertRaisesRegex(ValueError, "Raw capture"):
            self.build()

    def test_http_scope_ranges_and_replacement(self):
        path, receipt = self.build()
        allowed = server_module.load_allowlist(path)
        server = ThreadingHTTPServer(("127.0.0.1", 0), server_module.make_handler(allowed))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        media_route = next(route for route, item in allowed.items() if item["path"].endswith("fixture.mp4"))
        port = server.server_address[1]

        def request(path, method="GET", headers=None):
            connection = HTTPConnection("127.0.0.1", port)
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            result = response.status, dict(response.getheaders()), response.read()
            connection.close()
            return result

        try:
            code, headers, body = request("/", "HEAD")
            self.assertEqual(code, 200)
            self.assertEqual(body, b"")
            self.assertEqual(int(headers["Content-Length"]), self.output.stat().st_size)
            code, headers, body = request(media_route, headers={"Range": "bytes=3-8"})
            self.assertEqual(code, 206)
            self.assertEqual(body, self.media.read_bytes()[3:9])
            self.assertEqual(headers["Content-Range"], f"bytes 3-8/{self.media.stat().st_size}")
            self.assertEqual(request(media_route, headers={"Range": "bytes=-4"})[2], self.media.read_bytes()[-4:])
            self.assertEqual(request(media_route, headers={"Range": "bytes=3-"})[2], self.media.read_bytes()[3:])
            for byte_range in ["bytes=999-", "bytes=5-2", "bytes=1-2,4-5", "bytes=-0", "invalid"]:
                self.assertEqual(request(media_route, headers={"Range": byte_range})[0], 416)
            for route in ["/HANDOFF.md", "/../HANDOFF.md", "/%2e%2e/HANDOFF.md", "/processed/manifest.json", "/raw/source.mov", "/?file=HANDOFF.md"]:
                self.assertEqual(request(route)[0], 404)
            self.assertEqual(request("/", headers={"Host": "attacker.example"})[0], 403)
            self.assertEqual(request("/", method="POST")[0], 501)
            self.media.unlink()
            self.media.symlink_to(self.assets / "receipt.json")
            self.assertEqual(request(media_route)[0], 409)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main(verbosity=2)
