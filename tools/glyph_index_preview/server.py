"""
Local web UI for Manim glyph-index debugging.

Run from the **repository root** (so ``manim`` and ``hebrew_utils`` resolve)::

    python tools/glyph_index_preview/server.py

Open http://127.0.0.1:8765/ — paste LaTeX for :class:`~manim.mobject.text.tex_mobject.MathTex`
(no surrounding ``$``), click Render.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
SCENE_FILE = ROOT / "scene_glyph_debug.py"
HOST = "127.0.0.1"
PORT = 8765


def _render_png(latex: str, hebrew_template: bool) -> bytes:
    if len(latex) > 200_000:
        raise ValueError("LaTeX string too long.")
    tmp = Path(tempfile.mkdtemp(prefix="glyph_preview_"))
    try:
        # Manim writes under ``<media_dir>/images/...`` — use temp root, not ``.../media``.
        media_root = tmp
        env = os.environ.copy()
        env["GLYPH_DEBUG_LATEX"] = latex
        env["GLYPH_DEBUG_HEBREW"] = "1" if hebrew_template else "0"
        env.setdefault("PYTHONIOENCODING", "utf-8")
        cmd = [
            sys.executable,
            "-m",
            "manim",
            "-s",
            "-ql",
            "--media_dir",
            str(media_root),
            str(SCENE_FILE),
            "GlyphDebugScene",
        ]
        r = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "manim failed").strip()
            raise RuntimeError(msg[-8000:])
        pngs = sorted(tmp.rglob("*.png"))
        if not pngs:
            raise RuntimeError("No PNG produced; manim output:\n" + (r.stderr or "")[-4000:])
        return pngs[0].read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        if path in ("/", "/index.html"):
            data = (ROOT / "index.html").read_bytes()
            self._send(200, data, "text/html; charset=utf-8")
            return
        self._send(404, b"Not found", "text/plain")

    def do_POST(self) -> None:
        if self.path != "/api/render":
            self._send(404, b"Not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
            latex = str(payload.get("latex", ""))
            hebrew = bool(payload.get("hebrew_template", False))
            png = _render_png(latex, hebrew)
            self._send(200, png, "image/png")
        except Exception as e:
            err = json.dumps({"error": str(e)})
            self._send(400, err.encode("utf-8"), "application/json; charset=utf-8")


def main() -> None:
    if not SCENE_FILE.is_file():
        print("Missing scene file:", SCENE_FILE, file=sys.stderr)
        sys.exit(1)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving http://{HOST}:{PORT}/  (repo root: {REPO_ROOT})")
    print("Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
