#!/usr/bin/env python3
"""Build evidence-preserving HTML demo media from reviewed cuts of local recordings."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit


KINDS = {"browser-recording", "desktop-recording", "terminal-recording", "synthetic-tooling-test"}
MEDIA_SUFFIXES = {".webm", ".mp4", ".mov", ".mkv", ".m4v", ".avi"}
RECEIPT_TYPES = {".json": "application/json", ".md": "text/markdown", ".txt": "text/plain",
                 ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


class ClipError(ValueError):
    """Invalid input or failed media verification."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(argv: list[str], commands: list[dict] | None = None) -> str:
    result = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if commands is not None:
        commands.append({"argv": argv, "exitCode": result.returncode})
    if result.returncode:
        raise ClipError(f"{Path(argv[0]).name} failed: {result.stderr.strip()[-3000:]}")
    return result.stdout


def number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ClipError(f"{field} must be a finite number")
    return float(value)


def text_field(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ClipError(f"{field} must be nonempty text")
    return value


def local_relative(value: object, field: str) -> Path:
    value = text_field(value, field)
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
        raise ClipError(f"{field} must be a local relative path without traversal")
    if any(ord(c) < 32 for c in value):
        raise ClipError(f"{field} contains control characters")
    return path


def evidence_url(value: object) -> str:
    value = text_field(value, "cue.evidence")
    if any(ord(c) < 32 for c in value) or "\\" in value:
        raise ClipError("cue.evidence contains unsafe characters")
    parsed = urlsplit(value)
    if parsed.scheme:
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ClipError("cue.evidence must be HTTPS or a relative local URL")
    elif parsed.netloc or parsed.path.startswith("/"):
        raise ClipError("cue.evidence must be HTTPS or a relative local URL")
    if ".." in Path(unquote(parsed.path)).parts:
        raise ClipError("cue.evidence must not traverse directories")
    return value


def input_options(path: Path) -> list[str]:
    # Do not let a file named *.mp4 auto-detect as a playlist or other dependency-bearing format.
    suffix = path.suffix.lower()
    if suffix not in MEDIA_SUFFIXES:
        raise ClipError(f"Unsupported source extension: {suffix}")
    demuxer = "mov" if suffix in {".mp4", ".mov", ".m4v"} else "avi" if suffix == ".avi" else "matroska"
    options = ["-protocol_whitelist", "file,pipe", "-f", demuxer]
    if demuxer == "mov":
        options += ["-enable_drefs", "0", "-use_absolute_path", "0"]
    return options


def probe(path: Path, ffprobe: str, commands: list[dict] | None = None) -> dict:
    raw = json.loads(run([ffprobe, "-v", "error"] + input_options(path) + ["-show_format",
                          "-show_streams", "-of", "json", str(path)], commands))
    video = next((s for s in raw.get("streams", []) if s.get("codec_type") == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    if not video:
        raise ClipError(f"No video stream in {path.name}")
    try:
        duration = float(video.get("duration", raw.get("format", {}).get("duration", "nan")))
        fps = float(Fraction(video.get("avg_frame_rate", "0/1")))
    except (ValueError, ZeroDivisionError):
        raise ClipError(f"Invalid timing metadata in {path.name}") from None
    if not math.isfinite(duration) or duration <= 0:
        raise ClipError(f"No positive finite duration in {path.name}")
    return {"duration": duration, "width": video["width"], "height": video["height"],
            "codec": video["codec_name"], "pixelFormat": video.get("pix_fmt"), "fps": fps,
            "audio": any(s.get("codec_type") == "audio" for s in raw.get("streams", []))}


def read_manifest(path: Path, ffprobe: str, commands: list[dict] | None = None) -> tuple[dict, list[dict]]:
    if not path.is_file():
        raise ClipError("Manifest is not a regular file")
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        raise ClipError("Manifest schemaVersion must be 1")
    text_field(data.get("title"), "title")
    if not isinstance(data.get("scenes"), list) or not data["scenes"]:
        raise ClipError("Manifest must contain scenes")
    root, ids, scenes, source_cache = path.parent.resolve(), set(), [], {}
    for entry in data["scenes"]:
        if not isinstance(entry, dict):
            raise ClipError("Each scene must be an object")
        scene_id = entry.get("id")
        if not isinstance(scene_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", scene_id):
            raise ClipError("Scene id must use lowercase letters, digits, and hyphens (1-80 characters)")
        if scene_id in ids:
            raise ClipError(f"Duplicate scene id: {scene_id}")
        ids.add(scene_id)
        for field in ("title", "description", "evidenceScope", "recordedAt"):
            text_field(entry.get(field), f"{scene_id}.{field}")
        try:
            recorded = datetime.fromisoformat(entry["recordedAt"].replace("Z", "+00:00"))
            if recorded.tzinfo is None or recorded.utcoffset() is None:
                raise ValueError()
        except ValueError:
            raise ClipError(f"{scene_id}.recordedAt must be an ISO timestamp with a time zone") from None
        source = entry.get("source")
        if not isinstance(source, dict) or source.get("kind") not in KINDS:
            raise ClipError(f"{scene_id}.source.kind must be one of {sorted(KINDS)}")
        if "description" in source:
            text_field(source["description"], f"{scene_id}.source.description")
        relative = local_relative(source.get("raw"), f"{scene_id}.source.raw")
        raw_path = (root / relative).resolve()
        if not raw_path.is_relative_to(root) or not raw_path.is_file():
            raise ClipError(f"{scene_id}.source.raw must be a file inside the manifest directory")
        if raw_path.suffix.lower() not in MEDIA_SUFFIXES:
            raise ClipError(f"Unsupported source extension: {raw_path.suffix}")
        if source["kind"] == "synthetic-tooling-test" and "synthetic" not in entry["evidenceScope"].lower():
            raise ClipError("Synthetic tooling sources must have an explicitly synthetic evidenceScope")
        if raw_path not in source_cache:
            source_cache[raw_path] = {"probe": probe(raw_path, ffprobe, commands), "sha256": sha256(raw_path)}
        src = source_cache[raw_path]
        start, end = number(entry.get("start"), "start"), number(entry.get("end"), "end")
        if start < 0 or end <= start or end > src["probe"]["duration"]:
            raise ClipError(f"{scene_id}: require 0 <= start < end <= source duration ({src['probe']['duration']})")
        if end - start < 0.25:
            raise ClipError(f"{scene_id}: clips must be at least 0.25 seconds")
        cues = entry.get("cues", [])
        if not isinstance(cues, list):
            raise ClipError(f"{scene_id}.cues must be an array")
        clean_cues = []
        for cue in cues:
            if not isinstance(cue, dict):
                raise ClipError("Each cue must be an object")
            time = number(cue.get("time"), "cue.time")
            if not 0 <= time < end - start:
                raise ClipError(f"{scene_id}: cue time must be inside the trimmed clip")
            clean = {"time": time, "label": text_field(cue.get("label"), "cue.label"),
                     "detail": text_field(cue.get("detail"), "cue.detail")}
            if "evidence" in cue:
                clean["evidence"] = evidence_url(cue["evidence"])
            clean_cues.append(clean)
        scenes.append({"entry": entry, "id": scene_id, "raw": raw_path, "source": src,
                       "start": start, "end": end, "cues": sorted(clean_cues, key=lambda c: c["time"])})
    return data, scenes


def collect_evidence(scenes: list[dict], root: Path) -> dict[Path, dict]:
    """Collect only explicit local receipt files; raw media and active HTML are excluded."""
    collected = {}
    reserved = {"manifest.json", "receipt.json", *(scene["id"] for scene in scenes)}
    for scene in scenes:
        for cue in scene["cues"]:
            if "evidence" not in cue:
                continue
            parsed = urlsplit(cue["evidence"])
            if parsed.scheme:
                continue
            relative = local_relative(unquote(parsed.path), "cue.evidence")
            if relative.parts[0] in reserved or relative.suffix.lower() not in RECEIPT_TYPES:
                raise ClipError("Local cue evidence must name a JSON, MD, TXT, PDF, PNG, or JPEG receipt outside generated asset paths")
            source = (root / relative).resolve()
            if not source.is_relative_to(root) or not source.is_file():
                raise ClipError(f"Cue evidence does not exist inside manifest directory: {relative}")
            collected[relative] = {"source": source, "sha256": sha256(source)}
    return collected


def artifact(path: Path, root: Path, media_type: str) -> dict:
    if not path.is_file() or not path.stat().st_size:
        raise ClipError(f"Missing or empty artifact: {path.name}")
    return {"url": path.relative_to(root).as_posix(), "type": media_type,
            "bytes": path.stat().st_size, "sha256": sha256(path)}


def faststart(path: Path) -> bool:
    """Inspect top-level MP4 boxes without loading the video into memory."""
    positions = {}
    size = path.stat().st_size
    with path.open("rb") as stream:
        while stream.tell() + 8 <= size:
            position = stream.tell()
            header = stream.read(8)
            box_size, kind = int.from_bytes(header[:4], "big"), header[4:]
            header_size = 8
            if box_size == 1:
                box_size, header_size = int.from_bytes(stream.read(8), "big"), 16
            elif box_size == 0:
                box_size = size - position
            if box_size < header_size or position + box_size > size:
                return False
            positions.setdefault(kind, position)
            stream.seek(position + box_size)
    return b"moov" in positions and b"mdat" in positions and positions[b"moov"] < positions[b"mdat"]


def compile_clips(manifest: Path, output: Path, *, width: int = 1600, webm: bool = False,
                  audio: bool = False, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> dict:
    if width < 160 or width > 4096 or width % 2:
        raise ClipError("width must be even, between 160 and 4096")
    manifest = manifest.resolve()
    if output.exists() or output.is_symlink():
        raise ClipError("Output directory already exists; choose a fresh output directory")
    output = output.resolve()
    manifest_sha = sha256(manifest)
    script_sha = sha256(Path(__file__))
    commands: list[dict] = []
    data, scenes = read_manifest(manifest, ffprobe, commands)
    evidence = collect_evidence(scenes, manifest.parent)
    if any(s["raw"].is_relative_to(output) for s in scenes) or manifest.is_relative_to(output):
        raise ClipError("Output directory must not contain sources or the input manifest")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}-building-", dir=output.parent))
    try:
        built = []
        copied_evidence = []
        for relative, receipt_source in evidence.items():
            destination = work / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(receipt_source["source"], destination)
            if sha256(destination) != receipt_source["sha256"]:
                raise ClipError("Evidence file changed while copying")
            copied_evidence.append(artifact(destination, work, RECEIPT_TYPES[relative.suffix.lower()]))
        ffmpeg_base = [ffmpeg, "-hide_banner", "-loglevel", "error", "-xerror", "-nostdin", "-n"]
        for scene in scenes:
            scene_dir = work / scene["id"]
            scene_dir.mkdir()
            duration = scene["end"] - scene["start"]
            media = []
            # Decode and seek precisely, preserve timing, and never synthesize padding or repeat a final frame.
            cut = input_options(scene["raw"]) + ["-i", str(scene["raw"]), "-ss", str(scene["start"]),
                   "-t", str(duration), "-map", "0:v:0", "-map_metadata", "-1", "-map_chapters", "-1",
                   "-vf", f"scale=w='min({width},trunc(iw/2)*2)':h=-2", "-fps_mode", "vfr", "-pix_fmt", "yuv420p"]
            for ext, codec, mime in [("mp4", "libx264", "video/mp4")] + ([("webm", "libvpx-vp9", "video/webm")] if webm else []):
                target = scene_dir / f"{scene['id']}.{ext}"
                encoding = ["-c:v", codec, "-crf", "20", "-preset", "medium", "-movflags", "+faststart"] if ext == "mp4" else [
                    "-c:v", codec, "-crf", "30", "-b:v", "0", "-deadline", "good", "-cpu-used", "2"]
                sound = ["-map", "0:a:0?", "-c:a", "aac" if ext == "mp4" else "libopus", "-b:a", "128k"] if audio else ["-an"]
                run(ffmpeg_base + cut + encoding + sound + [str(target)], commands)
                info = probe(target, ffprobe, commands)
                tolerance = max(0.15, 2 / scene["source"]["probe"]["fps"]) if scene["source"]["probe"]["fps"] > 0 else 0.15
                if abs(info["duration"] - duration) > tolerance:
                    raise ClipError(f"{scene['id']}: encoded duration differs from requested cut")
                if any(c["time"] >= info["duration"] for c in scene["cues"]):
                    raise ClipError(f"{scene['id']}: cue falls after the actual encoded duration")
                if info["pixelFormat"] != "yuv420p" or (not audio and info["audio"]):
                    raise ClipError(f"{scene['id']}: output format/audio validation failed")
                if ext == "mp4" and (info["codec"] != "h264" or not faststart(target)):
                    raise ClipError(f"{scene['id']}: MP4 must be H.264 with moov before mdat")
                run(ffmpeg_base + input_options(target) + ["-i", str(target), "-f", "null", "-"], commands)
                media.append({**artifact(target, work, mime), **info, "decodeValidated": True})
            clip = work / media[0]["url"]
            sample_times = [media[0]["duration"] * fraction for fraction in (0.04, 0.20, 0.38, 0.56, 0.74, 0.92)]
            frames = []
            for index, sample in enumerate(sample_times):
                frame = scene_dir / f"frame-{index + 1:02d}.jpg"
                run(ffmpeg_base + ["-i", str(clip), "-ss", str(sample), "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "2", str(frame)], commands)
                frames.append(artifact(frame, work, "image/jpeg") | {"time": sample})
            poster = scene_dir / "poster.jpg"
            run(ffmpeg_base + ["-i", str(clip), "-ss", str(sample_times[0]), "-frames:v", "1", "-q:v", "2", str(poster)], commands)
            contact = scene_dir / "contact-sheet.jpg"
            inputs = [item for frame in frames for item in ("-i", str(work / frame["url"]))]
            run(ffmpeg_base + inputs + ["-filter_complex", "[0:v][1:v][2:v][3:v][4:v][5:v]xstack=inputs=6:layout=0_0|w0_0|w0+w1_0|0_h0|w0_h0|w0+w1_h0[v]",
                "-map", "[v]", "-frames:v", "1", "-q:v", "2", str(contact)], commands)
            entry = scene["entry"]
            public_source = {"kind": entry["source"]["kind"]}
            if "description" in entry["source"]:
                public_source["description"] = entry["source"]["description"]
            built.append({**{key: entry[key] for key in ("id", "title", "description", "evidenceScope", "recordedAt")},
                          "source": public_source,
                          "start": scene["start"], "end": scene["end"], "duration": media[0]["duration"], "cues": scene["cues"],
                          "media": media, "poster": artifact(poster, work, "image/jpeg"),
                          "contactSheet": artifact(contact, work, "image/jpeg"), "frames": frames,
                          "provenance": {"sourceSha256": scene["source"]["sha256"], "sourceDuration": scene["source"]["probe"]["duration"],
                                         "cut": {"start": scene["start"], "end": scene["end"]}, "recordedAt": entry["recordedAt"],
                                         "retimed": False, "padded": False, "audioIncluded": audio and scene["source"]["probe"]["audio"]}})
        for scene in scenes:
            if sha256(scene["raw"]) != scene["source"]["sha256"]:
                raise ClipError("Source recording changed during build")
        if any(sha256(receipt_source["source"]) != receipt_source["sha256"] for receipt_source in evidence.values()):
            raise ClipError("Evidence file changed during build")
        if sha256(manifest) != manifest_sha:
            raise ClipError("Input manifest changed during build")
        if sha256(Path(__file__)) != script_sha:
            raise ClipError("Processor script changed during build")
        now = datetime.now(timezone.utc).isoformat()
        final = {"schemaVersion": 1, "title": data["title"], "generatedAt": now, "scenes": built, "evidence": copied_evidence}
        (work / "manifest.json").write_text(json.dumps(final, indent=2) + "\n")
        receipt = {"schemaVersion": 1, "generatedAt": now, "status": "passed", "manifestSha256": sha256(work / "manifest.json"),
                   "inputManifestSha256": manifest_sha, "scriptSha256": script_sha,
                   "tools": {"ffmpeg": run([ffmpeg, "-version"]).splitlines()[0], "ffprobe": run([ffprobe, "-version"]).splitlines()[0]},
                   "settings": {"width": width, "webm": webm, "audio": audio},
                   "checks": ["source hashes unchanged", "manifest hash unchanged", "script hash unchanged", "cuts and cues bounded by source",
                              "all media fully decoded", "MP4 H.264 yuv420p faststart", "no retiming or padding",
                              "local receipt files copied and source hashes unchanged"],
                   "commands": commands}
        (work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if output.exists():
            raise ClipError("Output appeared during build; refusing to replace it")
        work.rename(output)
        return final
    except BaseException:
        # Only remove our own unique staging directory, never user sources or previous output.
        if work.exists():
            shutil.rmtree(work)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Reviewed JSON manifest; raw paths are relative to its directory")
    parser.add_argument("--output", type=Path, help="New output directory (never overwritten)")
    parser.add_argument("--check", action="store_true", help="Validate input, timing, and cues without encoding")
    parser.add_argument("--width", type=int, default=1600, help="Maximum video width; no upscaling (default 1600)")
    parser.add_argument("--webm", action="store_true", help="Also encode VP9 WebM")
    parser.add_argument("--audio", action="store_true", help="Include source audio; default is silent")
    args = parser.parse_args()
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    try:
        if not ffmpeg or not ffprobe:
            raise ClipError("ffmpeg and ffprobe must be installed")
        if args.check:
            _, scenes = read_manifest(args.manifest.resolve(), ffprobe)
            collect_evidence(scenes, args.manifest.resolve().parent)
            print(json.dumps({"status": "valid", "scenes": len(scenes), "encoded": False}))
            return 0
        if not args.output:
            raise ClipError("--output is required unless --check is used")
        result = compile_clips(args.manifest, args.output, width=args.width, webm=args.webm,
                               audio=args.audio, ffmpeg=ffmpeg, ffprobe=ffprobe)
        print(json.dumps({"status": "passed", "scenes": len(result["scenes"]), "manifest": str(args.output.resolve() / "manifest.json")}))
        return 0
    except (ClipError, OSError, json.JSONDecodeError) as error:
        print(f"demo-clips: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
