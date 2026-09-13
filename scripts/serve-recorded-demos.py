#!/usr/bin/env python3
"""Serve one bound recorded-demo edition and its explicit assets on loopback."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD = ROOT / "output/kirocrew-recorded-demos-build.json"


def secure_open(relative):
    """Resolve the entire allowlisted path using directory FDs and O_NOFOLLOW."""
    if not isinstance(relative, str) or relative.startswith("/") or "\\" in relative:
        raise ValueError("Invalid allowlist path")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Invalid allowlist path")
    folder = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=folder)
            os.close(folder)
            folder = child
        result = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=folder)
    finally:
        os.close(folder)
    if not stat.S_ISREG(os.fstat(result).st_mode):
        os.close(result)
        raise ValueError("Allowlisted path is not a regular file")
    return result


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def bound_file(relative, expected):
    fd = secure_open(relative)
    try:
        info = os.fstat(fd)
        digest = hashlib.sha256()
        with os.fdopen(os.dup(fd), "rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if info.st_size != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
            raise ValueError(f"Artifact differs from build receipt: {Path(relative).name}")
        return {**expected, "identity": identity(info)}
    finally:
        os.close(fd)


def load_allowlist(build_path):
    relative = Path(build_path).absolute().relative_to(ROOT).as_posix()
    with os.fdopen(secure_open(relative), "rb") as stream:
        build_bytes = stream.read()
    build = json.loads(build_bytes)
    if build.get("schemaVersion") != 1 or not build.get("serveFiles"):
        raise ValueError("Expected a recorded-demo build receipt")
    allowed = {}
    for route, item in build["serveFiles"].items():
        if not re.fullmatch(r"/[A-Za-z0-9_./%~-]+", route) or any(part in {".", ".."} for part in route.split("/")):
            raise ValueError("Invalid allowlist route")
        if Path(item["path"]).suffix.lower() not in {".html", ".mp4", ".webm", ".jpg", ".jpeg", ".png", ".webp", ".json", ".md", ".txt", ".pdf"}:
            raise ValueError("Unsupported allowlist type")
        if "raw" in PurePosixPath(item["path"]).parts:
            raise ValueError("Raw captures cannot be served")
        allowed[route] = bound_file(item["path"], item)
    edition = next((item for item in allowed.values() if item["path"] == build["edition"]), None)
    if not edition or edition["sha256"] != build["editionSha256"]:
        raise ValueError("Edition missing or mismatched")
    allowed["/"] = edition
    # The build receipt contains paths and hashes, never raw capture content.
    build_route = "/" + Path(relative).name
    allowed[build_route] = bound_file(relative, {"path": relative, "bytes": len(build_bytes), "sha256": hashlib.sha256(build_bytes).hexdigest()})
    return allowed


def byte_range(header, size):
    if header is None:
        return 0, size - 1, False
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if not match or (not match[1] and not match[2]) or size == 0:
        raise ValueError("Invalid byte range")
    if not match[1]:
        suffix = int(match[2])
        if suffix < 1:
            raise ValueError("Invalid suffix")
        return max(0, size - suffix), size - 1, True
    start = int(match[1])
    end = int(match[2]) if match[2] else size - 1
    if start >= size or start > end:
        raise ValueError("Unsatisfiable byte range")
    return start, min(end, size - 1), True


def make_handler(allowed):
    class Handler(BaseHTTPRequestHandler):
        server_version = "RecordedDemoPreview/1"
        sys_version = ""

        def log_message(self, *args):
            pass

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("X-Frame-Options", "DENY")
            super().end_headers()

        def send_error(self, code, message=None, explain=None):
            # Avoid reflecting a request path or local exception in response HTML.
            super().send_error(code, message or self.responses.get(code, ("Error",))[0])

        def do_HEAD(self):
            self.serve(False)

        def do_GET(self):
            self.serve(True)

        def serve(self, body):
            host = self.headers.get("Host", "")
            port = self.server.server_address[1]
            if host not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
                self.send_error(403)
                return
            parsed = urlsplit(self.path)
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or "\\" in parsed.path:
                self.send_error(404)
                return
            item = allowed.get(parsed.path)
            if item is None:
                self.send_error(404)
                return
            try:
                fd = secure_open(item["path"])
            except (OSError, ValueError):
                self.send_error(409)
                return
            try:
                if identity(os.fstat(fd)) != item["identity"]:
                    self.send_error(409)
                    return
                try:
                    start, end, partial = byte_range(self.headers.get("Range"), item["bytes"])
                except ValueError:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{item['bytes']}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(206 if partial else 200)
                self.send_header("Content-Type", mimetypes.guess_type(item["path"])[0] or "application/octet-stream")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(max(0, end - start + 1)))
                self.send_header("ETag", '"' + item["sha256"] + '"')
                if partial:
                    self.send_header("Content-Range", f"bytes {start}-{end}/{item['bytes']}")
                self.end_headers()
                if body:
                    os.lseek(fd, start, os.SEEK_SET)
                    remaining = end - start + 1
                    while remaining > 0:
                        block = os.read(fd, min(256 * 1024, remaining))
                        if not block:
                            break
                        self.wfile.write(block)
                        remaining -= len(block)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                os.close(fd)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--port", type=int, default=5606)
    args = parser.parse_args()
    allowed = load_allowlist(args.build)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(allowed))
    print(f"Recorded demo preview: http://127.0.0.1:{args.port}/ ({len(allowed)} allowlisted routes)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
