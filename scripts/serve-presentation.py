#!/usr/bin/env python3
"""Preview only the new standalone presentation on loopback. No directory browsing."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "output/kirocrew-system-design.html"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path not in ("/", "/kirocrew-system-design.html"):
            self.send_error(404)
            return
        body = TARGET.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5605)
    args = parser.parse_args()
    print(f"Presentation: http://127.0.0.1:{args.port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
