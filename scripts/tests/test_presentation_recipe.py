"""Portable recipe tests using only declared public project inputs."""
import hashlib
from html.parser import HTMLParser
import http.client
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("presentation_recipe", ROOT / "scripts/build-demo-presentation.py")
recipe_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recipe_module)


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        self.references.extend(value for key, value in attrs if key in {"src", "poster", "href"} and value)


def declared_sources(recipe):
    paths = set(recipe["input_sha256"])
    for relative in recipe["manifests"]:
        path = ROOT / relative
        manifest = json.loads(path.read_bytes())
        for scene in manifest["scenes"]:
            for item in scene.get("media", []) + [scene.get("poster"), scene.get("contactSheet")]:
                if item:
                    paths.add((path.parent / item["url"]).relative_to(ROOT).as_posix())
        for item in manifest.get("evidence", []):
            paths.add((path.parent / item["url"]).relative_to(ROOT).as_posix())
    if recipe["admin_build"]:
        admin = json.loads((ROOT / recipe["admin_build"]).read_bytes())
        paths.update(item["path"] for item in admin.get("outputs", []) + admin.get("sources", []) + admin.get("screenshots", []))
    if recipe["diagram_build"]:
        paths.add(json.loads((ROOT / recipe["diagram_build"]).read_bytes())["artifact"]["path"])
    for relative in recipe["receipts"]:
        if relative.endswith(".json"):
            receipt = json.loads((ROOT / relative).read_bytes())
            if isinstance(receipt, dict) and receipt.get("kind") == "managed_native_presentation":
                paths.update(item["path"] for item in receipt.get("receipts", []) + receipt.get("screenshots", []))
    paths.update({"config/presentation-native.json", "scripts/build-demo-presentation.py",
                  "scripts/build-native-control-presentation.py", "scripts/build-recorded-demo-presentation.py",
                  "scripts/serve-recorded-demos.py", "presentation/slides.css", "presentation/demo-player.css",
                  "presentation/slide-runtime.js", "presentation/demo-player.js"})
    return paths


def skill_link_sources(root):
    """Follow local Markdown links in the full checkout, never in playback."""
    skill = root / ".agents/skills/kirocrew-demo"
    pending = list(skill.rglob("*.md"))
    sources = set()
    while pending:
        document = pending.pop()
        relative = document.relative_to(root).as_posix()
        if relative in sources:
            continue
        sources.add(relative)
        if len(sources) > 500:
            raise ValueError("Skill documentation link graph exceeded its bound")
        for value in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text()):
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (document.parent / parsed.path).resolve()
            target_relative = target.relative_to(root).as_posix()
            if not target.is_file():
                raise ValueError(f"Missing skill documentation link: {relative} -> {value}")
            if any(part in {".build", "raw"} for part in Path(target_relative).parts) or target.name == "demo.local.json":
                raise ValueError("Skill documentation links to private state")
            # Historical output artifacts retain their original evidence links;
            # they are linked files, not part of the executable skill's guides.
            recurse = target_relative.startswith(("docs/", ".agents/skills/kirocrew-demo/"))
            if target.suffix == ".md" and recurse and target_relative not in sources:
                pending.append(target)
            else:
                sources.add(target_relative)
    return sources


class RecipeValidationTests(unittest.TestCase):
    def test_playback_readme_collision_preserves_existing_bytes(self):
        recipe = recipe_module.load_recipe()
        with tempfile.TemporaryDirectory() as temporary:
            export = Path(temporary).resolve()
            readme = export / "README.txt"
            readme.write_bytes(b"Existing input receipt")
            for files in ({}, {"/README.txt": {"path": "assets/README.txt"}}):
                with patch.object(recipe_module.builder, "build", return_value={"serveFiles": files}):
                    with self.assertRaisesRegex(ValueError, "README route collides"):
                        recipe_module.rebuild(recipe, export)
                self.assertEqual(readme.read_bytes(), b"Existing input receipt")

    def test_declared_recipe_and_processed_assets_validate(self):
        recipe = recipe_module.load_recipe()
        checked = recipe_module.check_assets(recipe)
        self.assertEqual(checked["sceneCount"], recipe["accepted_reference"]["scene_count"])
        self.assertGreater(checked["boundAssetCount"], checked["sceneCount"])

    def test_missing_and_traversing_inputs_fail_clearly(self):
        with self.assertRaisesRegex(ValueError, "Missing artifact"):
            recipe_module.project_file("config/missing-presentation-input.json")
        for value in ("../config/demo.local.json", "/tmp/source.json", "output//media.mp4", "output/../media.mp4"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "project-relative"):
                recipe_module.project_file(value)

    def test_existing_or_symlinked_destinations_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            with self.assertRaisesRegex(ValueError, "already exists"):
                recipe_module.builder.export_destination(root)
            link = root / "linked"
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinks"):
                recipe_module.builder.export_destination(link / "new-export")


class PortablePresentationTests(unittest.TestCase):
    def test_clean_project_build_and_independent_loopback_export(self):
        recipe = recipe_module.load_recipe()
        protected = {path: hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in recipe_module.builder.DESTINATIONS if path.exists()}
        with tempfile.TemporaryDirectory(prefix="presentation portability ") as temporary:
            base = Path(temporary).resolve()
            project = base / "fresh project with spaces"
            skill_sources = skill_link_sources(ROOT)
            for relative in declared_sources(recipe) | skill_sources:
                self.assertNotIn(".build", Path(relative).parts)
                self.assertNotIn("raw", Path(relative).parts)
                source, target = ROOT / relative, project / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            self.assertFalse((project / "config/demo.local.json").exists())
            self.assertEqual(skill_link_sources(project), skill_sources)
            command = [sys.executable, str(project / "scripts/build-demo-presentation.py"), "--recipe", "config/presentation-native.json"]
            check = subprocess.run(command + ["--check"], cwd=base, text=True, capture_output=True, timeout=30)
            self.assertEqual(check.returncode, 0, check.stderr)
            required = project / recipe["manifests"][0]
            original = required.read_bytes()
            required.unlink()
            missing = subprocess.run(command + ["--check"], cwd=base, text=True, capture_output=True, timeout=30)
            self.assertEqual(missing.returncode, 2)
            self.assertIn("Missing artifact", missing.stderr)
            self.assertNotIn("Traceback", missing.stderr)
            required.write_bytes(original)
            collision_name = "kirocrew-native-controls-notes.md"
            collision_data = b"Public receipt with a reserved route name.\n"
            (project / collision_name).write_bytes(collision_data)
            collision_recipe = json.loads(json.dumps(recipe))
            collision_recipe["receipts"].append(collision_name)
            collision_recipe["input_sha256"][collision_name] = hashlib.sha256(collision_data).hexdigest()
            (project / "config/collision.json").write_text(json.dumps(collision_recipe))
            collision_export = base / "must not publish collision"
            collision = subprocess.run([*command[:2], "--recipe", "config/collision.json", "--output-dir", str(collision_export)],
                                       cwd=base, text=True, capture_output=True, timeout=30)
            self.assertEqual(collision.returncode, 2)
            self.assertIn("route collides", collision.stderr)
            self.assertFalse(collision_export.exists())
            export = base / "portable presentation with spaces"
            build = subprocess.run(command + ["--output-dir", str(export)], cwd=base, text=True, capture_output=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = json.loads(build.stdout)
            self.assertEqual(result["slideCount"], recipe["accepted_reference"]["slide_count"])
            self.assertEqual(result["editionSha256"], recipe["accepted_reference"]["edition_sha256"])
            # Export must stand alone after its source checkout moves away.
            project.rename(base / "source checkout moved away")
            build_path = export / "kirocrew-native-controls-build.json"
            metadata = json.loads(build_path.read_bytes())
            self.assertIn("requires its own editorial review", metadata["editorialReview"])
            self.assertFalse(metadata["portableExport"]["transitiveLiveSetupLinksIncluded"])
            self.assertIn("Run the complete project skill", (export / "README.txt").read_text())
            server_spec = importlib.util.spec_from_file_location("portable_preview", export / "scripts/serve-recorded-demos.py")
            preview = importlib.util.module_from_spec(server_spec)
            server_spec.loader.exec_module(preview)
            self.assertEqual(preview.ROOT, export)
            allowed = preview.load_allowlist(build_path)
            server = preview.ThreadingHTTPServer(("127.0.0.1", 0), preview.make_handler(allowed))
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
            thread.start()

            def request(route, method="GET", headers=None):
                connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=3)
                try:
                    connection.request(method, route, headers=headers or {})
                    response = connection.getresponse()
                    return response.status, dict(response.getheaders()), response.read()
                finally:
                    connection.close()

            try:
                for route, item in allowed.items():
                    with self.subTest(route=route):
                        status, headers, _ = request(route, "HEAD")
                        self.assertEqual(status, 200)
                        self.assertEqual(int(headers["Content-Length"]), item["bytes"])
                checked_html = set()
                for route, item in allowed.items():
                    if not item["path"].endswith(".html") or item["path"] in checked_html:
                        continue
                    checked_html.add(item["path"])
                    parser = References()
                    parser.feed((export / item["path"]).read_text())
                    for reference in parser.references:
                        parsed = urlsplit(reference)
                        if parsed.scheme or parsed.netloc or reference.startswith("#"):
                            continue
                        target = urlsplit(urljoin("http://localhost" + route, reference))
                        with self.subTest(html=route, reference=reference):
                            self.assertIn(target.path, allowed)
                media_route, media = next((route, item) for route, item in allowed.items() if item["path"].endswith(".mp4"))
                expected_bytes = (export / media["path"]).read_bytes()
                for byte_range, expected in (("bytes=2-11", expected_bytes[2:12]), ("bytes=-8", expected_bytes[-8:])):
                    status, _, data = request(media_route, headers={"Range": byte_range})
                    self.assertEqual((status, data), (206, expected))
                self.assertEqual(request(media_route, headers={"Range": "bytes=999999999999-"})[0], 416)
                for route in ("/config/demo.local.json", "/.build/private.json", "/raw/capture.mov", "/scripts/serve-recorded-demos.py", "/../config/demo.local.json"):
                    self.assertEqual(request(route)[0], 404)
                self.assertEqual(request("/", headers={"Host": "example.invalid"})[0], 403)
                (export / media["path"]).write_bytes(b"changed exported asset")
                self.assertEqual(request(media_route)[0], 409)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
            self.assertTrue(all(not Path(item["path"]).is_absolute() and ".." not in Path(item["path"]).parts
                                for item in metadata["serveFiles"].values()))
        self.assertEqual(protected, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected})


if __name__ == "__main__":
    unittest.main()
