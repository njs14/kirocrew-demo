"""Synthetic-only processor checks. These fixtures are never application demo evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "demo-clips.py"
spec = importlib.util.spec_from_file_location("demo_clips", SCRIPT)
clips = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clips)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
class DemoClipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="synthetic-demo-clips-test-")
        cls.root = Path(cls.temp.name)
        cls.raw = cls.root / "synthetic-source.mp4"
        # Changes every frame; audio lets us verify that silent-by-default is observable.
        subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "lavfi", "-i",
                        "testsrc2=size=640x360:rate=20:duration=4", "-f", "lavfi", "-i",
                        "sine=frequency=440:sample_rate=48000:duration=4", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.raw)], check=True)
        cls.raw_hash = clips.sha256(cls.raw)
        (cls.root / "receipts").mkdir()
        (cls.root / "receipts/test.json").write_text('{"scope":"Synthetic tooling test only"}\n')
        cls.template = {"schemaVersion": 1, "title": "Synthetic tooling validation only", "scenes": [{
            "id": "synthetic-timing-test", "title": "Synthetic tooling fixture",
            "description": "FFmpeg-generated moving test pattern, not KiroCrew behavior.",
            "evidenceScope": "Synthetic tooling test; not application evidence",
            "recordedAt": "2026-09-13T00:00:00+00:00", "source": {
                "raw": cls.raw.name, "kind": "synthetic-tooling-test"},
            "start": 0.75, "end": 2.75, "cues": [
                {"time": 1.4, "label": "Second cue", "detail": "Synthetic checkpoint"},
                {"time": 0.2, "label": "First cue", "detail": "Synthetic checkpoint", "evidence": "receipts/test.json"}]}]}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def manifest(self, data=None):
        path = self.root / f"{self.id().split('.')[-1]}.json"
        path.write_text(json.dumps(data if data is not None else self.template))
        return path

    def test_build_mp4_webm_and_provenance(self):
        manifest = self.manifest()
        output = self.root / "processed"
        result = clips.compile_clips(manifest, output, width=480, webm=True)
        scene = result["scenes"][0]
        self.assertEqual([m["type"] for m in scene["media"]], ["video/mp4", "video/webm"])
        self.assertEqual(scene["provenance"]["sourceSha256"], self.raw_hash)
        self.assertNotIn("raw", scene["source"])
        self.assertEqual(clips.sha256(self.raw), self.raw_hash)
        self.assertFalse(scene["provenance"]["padded"])
        self.assertEqual([cue["time"] for cue in scene["cues"]], [0.2, 1.4])
        for media in scene["media"]:
            self.assertFalse(media["audio"])
            self.assertEqual(media["width"], 480)
            self.assertAlmostEqual(media["duration"], 2, delta=0.1)
            self.assertTrue(media["decodeValidated"])
            self.assertEqual(clips.sha256(output / media["url"]), media["sha256"])
        for asset in [scene["poster"], scene["contactSheet"], *scene["frames"]]:
            self.assertTrue((output / asset["url"]).is_file())
            self.assertGreater(asset["bytes"], 100)
        receipt = json.loads((output / "receipt.json").read_text())
        self.assertEqual(receipt["manifestSha256"], clips.sha256(output / "manifest.json"))
        self.assertTrue(all(command["exitCode"] == 0 for command in receipt["commands"]))
        self.assertTrue(clips.faststart(output / scene["media"][0]["url"]))
        self.assertEqual((output / "receipts/test.json").read_bytes(), (self.root / "receipts/test.json").read_bytes())
        self.assertEqual(result["evidence"][0]["sha256"], clips.sha256(output / "receipts/test.json"))

    def test_audio_opt_in(self):
        result = clips.compile_clips(self.manifest(), self.root / "with-audio", width=320, audio=True)
        self.assertTrue(result["scenes"][0]["media"][0]["audio"])
        self.assertTrue(result["scenes"][0]["provenance"]["audioIncluded"])

    def test_cuts_and_cues_outside_source_are_rejected_before_output(self):
        variants = [("start", -0.1), ("end", 4.001), ("end", 0.7), ("end", float("nan"))]
        for key, value in variants:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(self.template)
                data["scenes"][0][key] = value
                target = self.root / "invalid-cut-must-not-exist"
                with self.assertRaises(clips.ClipError):
                    clips.compile_clips(self.manifest(data), target)
                self.assertFalse(target.exists())
        for value in (-0.1, 2, float("inf"), True):
            data = copy.deepcopy(self.template)
            data["scenes"][0]["cues"][0]["time"] = value
            with self.assertRaises(clips.ClipError):
                clips.read_manifest(self.manifest(data), "ffprobe")

    def test_local_path_boundaries(self):
        for raw in (str(self.raw), "../synthetic-source.mp4", "https://example.org/a.mp4", "raw\\bad.mp4"):
            with self.subTest(raw=raw):
                data = copy.deepcopy(self.template)
                data["scenes"][0]["source"]["raw"] = raw
                with self.assertRaises(clips.ClipError):
                    clips.read_manifest(self.manifest(data), "ffprobe")
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "source.mp4"
            shutil.copyfile(self.raw, outside)
            (self.root / "escape.mp4").symlink_to(outside)
            data = copy.deepcopy(self.template)
            data["scenes"][0]["source"]["raw"] = "escape.mp4"
            with self.assertRaises(clips.ClipError):
                clips.read_manifest(self.manifest(data), "ffprobe")

    def test_unsafe_evidence_urls(self):
        for url in ("javascript:alert(1)", "file:///tmp/secret", "//example.org/x", "../secret", "%2e%2e/secret", "https://user:pass@example.org/a"):
            with self.subTest(url=url), self.assertRaises(clips.ClipError):
                clips.evidence_url(url)
        self.assertEqual(clips.evidence_url("https://example.org/receipt#one"), "https://example.org/receipt#one")

    def test_renamed_playlist_cannot_read_external_source(self):
        playlist = self.root / "disguised-playlist.mp4"
        playlist.write_text("ffconcat version 1.0\nfile 'synthetic-source.mp4'\n")
        data = copy.deepcopy(self.template)
        data["scenes"][0]["source"]["raw"] = playlist.name
        with self.assertRaises(clips.ClipError):
            clips.read_manifest(self.manifest(data), "ffprobe")

    def test_missing_and_active_evidence_files_rejected(self):
        for url in ("receipts/missing.json", "receipts/active.html", "synthetic-source.mp4"):
            data = copy.deepcopy(self.template)
            data["scenes"][0]["cues"][0]["evidence"] = url
            _, scenes = clips.read_manifest(self.manifest(data), "ffprobe")
            with self.subTest(url=url), self.assertRaises(clips.ClipError):
                clips.collect_evidence(scenes, self.root)

    def test_existing_output_and_raw_are_never_overwritten(self):
        target = self.root / "existing-output"
        target.mkdir()
        protected = target / "keep.txt"
        protected.write_text("Keep existing result")
        with self.assertRaises(clips.ClipError):
            clips.compile_clips(self.manifest(), target)
        self.assertEqual(protected.read_text(), "Keep existing result")
        with self.assertRaises(clips.ClipError):
            clips.compile_clips(self.manifest(), self.raw)
        self.assertEqual(clips.sha256(self.raw), self.raw_hash)

    def test_script_change_during_build_rejects_receipt(self):
        script_copy = self.root / "processor-copy.py"
        shutil.copyfile(SCRIPT, script_copy)
        original_run = clips.run
        changed = False

        def changing_run(argv, commands=None):
            nonlocal changed
            result = original_run(argv, commands)
            if not changed and Path(argv[0]).name == "ffmpeg":
                script_copy.write_text(script_copy.read_text() + "\n# Changed during processing\n")
                changed = True
            return result

        target = self.root / "script-change-output"
        with patch.object(clips, "__file__", str(script_copy)), patch.object(clips, "run", changing_run):
            with self.assertRaisesRegex(clips.ClipError, "script changed"):
                clips.compile_clips(self.manifest(), target, width=320)
        self.assertFalse(target.exists())

    def test_duplicate_ids_synthetic_scope_and_untimed_capture_rejected(self):
        for modification in ("duplicate", "scope", "timezone"):
            data = copy.deepcopy(self.template)
            if modification == "duplicate":
                data["scenes"].append(copy.deepcopy(data["scenes"][0]))
            elif modification == "scope":
                data["scenes"][0]["evidenceScope"] = "Actual product success"
            else:
                data["scenes"][0]["recordedAt"] = "2026-09-13T12:00:00"
            with self.subTest(modification=modification), self.assertRaises(clips.ClipError):
                clips.read_manifest(self.manifest(data), "ffprobe")


if __name__ == "__main__":
    unittest.main()
