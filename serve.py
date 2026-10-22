"""Static server for the Skillstorm site.

  python serve.py          # http://127.0.0.1:8099
  python serve.py 9000     # another port

Serves site/ with correct charset and Range support, and accepts POST /__shot
(JSON {name, data: "data:image/...;base64,..."}) which writes site frames into
shots/ so they can be inspected without relying on the browser pane painting.
"""
import base64
import http.server
import json
import os
import re
import socketserver
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE / "site"
SHOTS = HERE / "shots"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8099

TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".mp4": "video/mp4",
    ".glb": "model/gltf-binary",
    ".svg": "image/svg+xml",
}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def guess_type(self, path):
        return TYPES.get(Path(path).suffix.lower(), "application/octet-stream")

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        if "__shot" in (args[0] if args else ""):
            super().log_message(fmt, *args)

    def do_POST(self):
        if self.path != "/__shot":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            name = re.sub(r"[^A-Za-z0-9_.-]", "_", payload.get("name", "frame"))
            data = payload["data"].split(",", 1)[1]
            SHOTS.mkdir(exist_ok=True)
            ext = ".jpg" if "jpeg" in payload["data"][:30] else ".png"
            out = SHOTS / (name + ext)
            out.write_bytes(base64.b64decode(data))
            body = json.dumps({"saved": str(out), "bytes": out.stat().st_size}).encode()
        except Exception as exc:
            body = json.dumps({"error": str(exc)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_head(self):
        """Serve a byte range when the browser asks for one (video seeking)."""
        rng = self.headers.get("Range")
        if not rng:
            return super().send_head()

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404)
            return None

        size = os.fstat(f.fileno()).st_size
        m = re.match(r"bytes=(\d*)-(\d*)", rng.strip())
        if not m:
            f.close()
            self.send_error(400)
            return None
        start = int(m.group(1)) if m.group(1) else 0
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end:
            f.close()
            self.send_error(416)
            return None

        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(64 * 1024, remaining))
            if not chunk:
                break
            self.wfile.write(chunk)
            remaining -= len(chunk)
        f.close()
        return None


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Skillstorm site: http://127.0.0.1:{PORT}/  (root: {ROOT}, shots: {SHOTS})")
        httpd.serve_forever()
