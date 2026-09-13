#!/usr/bin/env python3
"""Append recorded scenes to the accepted deck without changing its slide bytes."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "output/kirocrew-system-design.html"
SOURCE_NOTES = ROOT / "output/kirocrew-system-design-notes.md"
DEFAULT_OUTPUT = ROOT / "output/kirocrew-recorded-demos.html"
FIXTURE_ROOT = ROOT / "evidence/demo-clips/player"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_file(path, within=ROOT):
    """Reject symlinks at every path component, including existing parents."""
    path = Path(path).absolute()
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError("Symlink artifacts are not allowed")
    path = path.resolve()
    try:
        path.relative_to(within.resolve())
    except ValueError as exc:
        raise ValueError("Artifact is outside its allowed directory") from exc
    if not path.is_file():
        raise ValueError(f"Missing artifact: {path.name}")
    return path


def local_asset(value, base, within):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Expected a relative artifact URL")
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or value.startswith("/"):
        raise ValueError("Media URLs must be plain relative local paths")
    if any(part in {"", ".", ".."} for part in value.split("/")) or "%" in value:
        raise ValueError("Ambiguous or traversing artifact URL")
    return safe_file(base / value, within)


def text(value, label, max_length=10000):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"Invalid {label}")
    return value


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f"Invalid {label}")
    return value


def write_atomic(path, content):
    """Replace the named file atomically; never follow a destination symlink."""
    fd, temporary = tempfile.mkstemp(prefix=".demo-build-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def build(manifest_path, output=DEFAULT_OUTPUT, fixture=False):
    manifest_path = safe_file(manifest_path)
    output = Path(output).absolute()
    if any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError("Output must be a regular path inside the project")
    output = output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Output must stay inside the project")
    if output.suffix != ".html":
        raise ValueError("Edition output must have the .html extension")
    if fixture and not output.is_relative_to(FIXTURE_ROOT):
        raise ValueError("Synthetic player fixtures must stay under evidence/demo-clips/player")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("schemaVersion") != 1 or not isinstance(manifest.get("scenes"), list) or not manifest["scenes"]:
        raise ValueError("Expected a nonempty schemaVersion 1 processed scene manifest")
    scenes = manifest["scenes"]
    evidence_index = {item["url"]: item for item in manifest.get("evidence", [])}
    if len(scenes) > 24:
        raise ValueError("At most 24 scenes per edition")
    if not fixture and (manifest.get("synthetic") or "synthetic" in manifest.get("title", "").lower()):
        raise ValueError("Synthetic manifests require --test-fixture")
    source_bytes = safe_file(SOURCE).read_bytes()
    source = source_bytes.decode("utf-8")
    old_sections = re.findall(r'<section class="slide\b.*?</section>', source, re.S)
    if len(old_sections) != 14 or source.count("</main>") != 1:
        raise ValueError("Accepted source must contain exactly 14 slides and one main element")
    original_notes = safe_file(SOURCE_NOTES).read_text()
    notes_path = output.with_name(output.stem + "-notes.md")
    public_path = output.with_name(output.stem + "-manifest.json")
    receipt_path = output.with_name(output.stem + "-build.json")
    destinations = [output, notes_path, public_path, receipt_path]
    for destination in destinations:
        if destination in {SOURCE, SOURCE_NOTES, manifest_path}:
            raise ValueError("A protected source cannot be overwritten")
        if any(p.is_symlink() for p in [destination, *destination.parents]):
            raise ValueError("Output destinations must not be symlinks")
        if destination.exists() and not destination.is_file():
            raise ValueError("Output destinations must be regular files")
    files = {}

    def register(path):
        path = safe_file(path)
        relative = path.relative_to(output.parent) if path.is_relative_to(output.parent) else None
        if relative is None:
            # Copy-free fixtures can reference project assets using a fixed virtual route.
            url = "artifacts/" + quote(path.relative_to(ROOT).as_posix(), safe="/")
        else:
            url = quote(relative.as_posix(), safe="/")
        data = path.read_bytes()
        files["/" + url] = {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha(data)}
        return url

    ids = set()
    slides = []
    public_scenes = []
    notes_addendum = ["\n\n# Recorded demo edition", "\nThe first 14 slides preserve the accepted source edition. The recorded scenes follow those slides. Play a scene, select a chapter to seek and pause, or enable guided pauses. Replay restarts the scene. Moving to another slide or opening a dialog pauses playback.", "\nReview scope: the previous model council reviewed its frozen source candidate. It did not review this recorded-demo edition. New recording and player validation receipts have their own scope."]
    for position, scene in enumerate(scenes, 15):
        scene_id = text(scene.get("id"), "scene id", 80)
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", scene_id) or scene_id in ids:
            raise ValueError("Scene IDs must be unique safe identifiers")
        ids.add(scene_id)
        title = text(scene.get("title"), "scene title", 180)
        description = text(scene.get("description"), "scene description", 1500)
        scope = text(scene.get("evidenceScope"), "evidence scope", 1500)
        recorded = text(scene.get("recordedAt"), "recording timestamp", 80)
        if not fixture and "synthetic" in str(scene.get("source", {}).get("kind", "")).lower():
            raise ValueError("Synthetic scenes require --test-fixture")
        try:
            if datetime.fromisoformat(recorded.replace("Z", "+00:00")).tzinfo is None:
                raise ValueError()
        except ValueError as exc:
            raise ValueError("recordedAt must be an ISO timestamp with timezone") from exc
        duration = number(scene.get("duration"), "duration")
        if duration <= 0:
            raise ValueError("Scene duration must be positive")
        provenance = scene.get("provenance", {})
        source_hash = provenance.get("sourceSha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
            raise ValueError("Processed scenes require sourceSha256 provenance")
        sources = []
        media_public = []
        for media in scene.get("media", []):
            if not fixture and media.get("decodeValidated") is not True:
                raise ValueError("Final scenes require decoded media validation")
            if media.get("type") not in {"video/mp4", "video/webm"}:
                raise ValueError("Only processed MP4 and WebM media are supported")
            path = local_asset(media.get("url"), manifest_path.parent, manifest_path.parent)
            if path.suffix.lower() not in {".mp4", ".webm"}:
                raise ValueError("Unsupported media extension")
            data = path.read_bytes()
            if media.get("sha256") != sha(data) or media.get("bytes") != len(data):
                raise ValueError(f"Processed media hash or size mismatch: {path.name}")
            url = register(path)
            sources.append(f'<source src="{html.escape(url, quote=True)}" type="{media["type"]}">')
            media_public.append({key: media[key] for key in ("type", "bytes", "sha256", "duration", "width", "height", "codec", "pixelFormat", "fps", "audio", "decodeValidated") if key in media} | {"url": url})
        if not sources:
            raise ValueError("Scene has no processed video")
        poster = scene.get("poster", {})
        poster_path = local_asset(poster.get("url"), manifest_path.parent, manifest_path.parent)
        if poster_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise ValueError("Unsupported poster extension")
        if not fixture and (poster.get("sha256") != sha(poster_path.read_bytes()) or poster.get("bytes") != poster_path.stat().st_size):
            raise ValueError("Poster hash or size mismatch")
        poster_url = register(poster_path)
        contact_url = None
        if scene.get("contactSheet"):
            contact_path = local_asset(scene["contactSheet"].get("url"), manifest_path.parent, manifest_path.parent)
            if contact_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                raise ValueError("Unsupported contact sheet extension")
            contact = scene["contactSheet"]
            if not fixture and (contact.get("sha256") != sha(contact_path.read_bytes()) or contact.get("bytes") != contact_path.stat().st_size):
                raise ValueError("Contact sheet hash or size mismatch")
            contact_url = register(contact_path)
        cues = []
        cue_buttons = []
        previous_cue = -1
        for cue in scene.get("cues", []):
            at = number(cue.get("time"), "cue time")
            if at < 0 or at > duration or at <= previous_cue:
                raise ValueError("Cues must be strictly increasing and within the clip")
            previous_cue = at
            label = text(cue.get("label"), "cue label", 200)
            detail = text(cue.get("detail"), "cue detail", 2500)
            evidence = cue.get("evidence")
            if evidence:
                parsed = urlsplit(evidence)
                if parsed.scheme == "https" and parsed.netloc and not parsed.username and not parsed.password:
                    if any(ord(c) < 32 for c in evidence):
                        raise ValueError("Invalid evidence URL")
                else:
                    evidence_path = local_asset(evidence, manifest_path.parent, manifest_path.parent)
                    if evidence_path.suffix.lower() not in {".json", ".md", ".txt", ".pdf", ".jpg", ".jpeg", ".png", ".webp"}:
                        raise ValueError("Local cue evidence must be a reviewed receipt or image")
                    if "raw" in evidence_path.relative_to(manifest_path.parent).parts:
                        raise ValueError("Raw capture paths cannot be linked as public evidence")
                    if not fixture:
                        expected = evidence_index.get(evidence, {})
                        if expected.get("sha256") != sha(evidence_path.read_bytes()) or expected.get("bytes") != evidence_path.stat().st_size:
                            raise ValueError("Cue receipt must match explicit processed evidence metadata")
                    evidence = register(evidence_path)
            cue_out = {"time": at, "label": label, "detail": detail}
            if evidence:
                cue_out["evidence"] = evidence
            cues.append(cue_out)
            ev_attr = f' data-cue-evidence="{html.escape(evidence, quote=True)}"' if evidence else ""
            clock = f"{int(at)//60}:{int(at)%60:02d}"
            cue_buttons.append(f'<button type="button" data-cue-time="{at}" data-cue-label="{html.escape(label, quote=True)}" data-cue-detail="{html.escape(detail, quote=True)}"{ev_attr}><time>{clock}</time><span>{html.escape(label)}</span></button>')
        e = html.escape
        fixture_label = '<span class="demo-fixture">SYNTHETIC PLAYER TEST · </span>' if fixture else ""
        note = f"Recorded {recorded}. {scope} Source capture SHA-256: {source_hash}. Original footage remains in the private capture directory. The playback controls seek within this recording; they do not operate KiroCrew."
        slides.append(f'''<section class="slide recorded-demo" id="slide-{position}" data-title="{e(title, quote=True)}" data-section="08 / Recorded demos" aria-label="Slide {position}: {e(title, quote=True)}" data-scene-id="{scene_id}" hidden>
<header class="slide-header"><p class="eyebrow">{fixture_label}Recorded demo {position - 14} / {len(scenes)}</p><h2>{e(title)}</h2><p class="demo-description">{e(description)}</p></header>
<div class="demo-layout"><div class="demo-screen"><video controls muted playsinline preload="metadata" poster="{e(poster_url, quote=True)}" aria-label="Recorded walkthrough: {e(title, quote=True)}">{''.join(sources)}Your browser does not support this video.</video><div class="demo-controls"><button class="demo-replay" type="button">Replay</button><button class="demo-next-cue" type="button">Next chapter</button><label><input class="demo-guided" type="checkbox"> Pause at chapters</label></div><p class="demo-status" role="status" aria-live="polite">Select a chapter to seek and pause.</p></div><aside class="demo-chapters" aria-label="Recording chapters"><h3>Chapters</h3><div class="demo-cues">{''.join(cue_buttons)}</div><div class="demo-cue-detail" aria-live="polite"></div></aside></div>
<footer class="slide-footer"><div class="demo-scope"><strong>Recorded {e(recorded)}</strong><br>{e(scope)}</div><span class="number">{position:02d}</span></footer><aside class="speaker-notes" hidden><p>{e(note)}</p></aside></section>''')
        notes_addendum.extend([f"\n## Slide {position}. {title}", f"\n{description}", f"\n{note}"])
        notes_addendum.extend(f"\n- {cue['time']:g}s: {cue['label']}. {cue['detail']}" + (f" Evidence: {cue['evidence']}" if cue.get("evidence") else "") for cue in cues)
        public_scenes.append({"id": scene_id, "title": title, "description": description, "evidenceScope": scope, "recordedAt": recorded, "duration": duration, "media": media_public, "poster": {"url": poster_url}, "contactSheet": {"url": contact_url} if contact_url else None, "cues": cues, "provenance": {"sourceSha256": source_hash, "cut": provenance.get("cut"), "sourceDuration": provenance.get("sourceDuration")}})
    notes = original_notes + "\n".join(notes_addendum) + "\n"
    input_paths = {ROOT / item["path"] for item in files.values()}
    if any(destination in input_paths for destination in destinations):
        raise ValueError("Output destinations cannot overwrite input artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(notes_path, notes)
    notes_url = register(notes_path)
    document = source.replace("</main>", "\n".join(slides) + "\n</main>", 1)
    document = document.replace("img-src data: blob:;", "img-src 'self' data: blob:; media-src 'self' blob:;", 1)
    document = document.replace("</head>", f'<link rel="icon" href="data:,"><style>{safe_file(ROOT / "presentation/demo-player.css").read_text()}</style></head>', 1)
    document = document.replace("</body>", f'<script>{safe_file(ROOT / "presentation/demo-player.js").read_text()}</script></body>', 1)
    document = document.replace("<title>KiroCrew on ARM — System design presentation</title>", "<title>KiroCrew — Recorded demo presentation</title>", 1)
    document = document.replace("System design / September 2026</span>", "System design + recorded demos</span>", 1)
    document = re.sub(r'<a href="[^"]*" download="kirocrew-system-design-notes.md"', f'<a href="data:text/markdown;base64,{base64.b64encode(notes.encode()).decode()}" download="{notes_path.name}"', document, count=1)
    if re.findall(r'<section class="slide\b.*?</section>', document, re.S)[:14] != old_sections:
        raise ValueError("Accepted slide content changed")
    write_atomic(output, document)
    register(output)
    public = {"schemaVersion": 1, "title": manifest.get("title"), "synthetic": fixture, "scenes": public_scenes, "reviewScope": "Prior model council covers its frozen source candidate only; this derivative has no final council verdict."}
    write_atomic(public_path, json.dumps(public, indent=2) + "\n")
    register(public_path)
    receipt = {"schemaVersion": 1, "builtAt": datetime.now(timezone.utc).isoformat(), "edition": output.relative_to(ROOT).as_posix(), "editionSha256": sha(document.encode()), "notes": notes_path.relative_to(ROOT).as_posix(), "notesSha256": sha(notes.encode()), "processedManifest": manifest_path.relative_to(ROOT).as_posix(), "processedManifestSha256": sha(manifest_bytes), "source": {"path": SOURCE.relative_to(ROOT).as_posix(), "sha256": sha(source_bytes), "slides": [{"index": i + 1, "sha256": sha(section.encode())} for i, section in enumerate(old_sections)], "preservedSlides": 14, "allOriginalSlideBytesPreserved": True}, "slideCount": 14 + len(scenes), "synthetic": fixture, "reviewScope": public["reviewScope"], "publicManifest": public_path.relative_to(ROOT).as_posix(), "serveFiles": files, "buildInputs": {name: sha(safe_file(ROOT / name).read_bytes()) for name in ["scripts/build-recorded-demo-presentation.py", "presentation/demo-player.js", "presentation/demo-player.css", "output/kirocrew-system-design-notes.md"]}}
    write_atomic(receipt_path, json.dumps(receipt, indent=2) + "\n")
    return receipt_path, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--test-fixture", action="store_true")
    args = parser.parse_args()
    path, receipt = build(args.manifest, args.output, args.test_fixture)
    print(json.dumps({"buildReceipt": str(path), "edition": receipt["edition"], "sha256": receipt["editionSha256"], "slideCount": receipt["slideCount"]}, indent=2))


if __name__ == "__main__":
    main()
