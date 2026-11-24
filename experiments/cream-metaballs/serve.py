"""Serve only this isolated experiment on loopback with explicit module MIME types."""

import argparse
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit


VERSIONED_FILES = ("index.html", "preview.css", "static-clumps.css", "preview.mjs", "model.mjs")


def preview_revision(directory):
    fingerprint = sha256()
    for name in VERSIONED_FILES:
        payload = (directory / name).read_bytes()
        fingerprint.update(name.encode("ascii") + b"\0" + str(len(payload)).encode("ascii") + b"\0")
        fingerprint.update(payload)
    return fingerprint.hexdigest()[:12]


def versioned_index(directory, revision):
    page = (directory / "index.html").read_text(encoding="utf-8")
    for attribute, name in (("href", "preview.css"), ("href", "static-clumps.css"), ("src", "preview.mjs")):
        reference = f'{attribute}="{name}"'
        if page.count(reference) != 1:
            raise ValueError(f"The preview must reference {name} exactly once.")
        page = page.replace(reference, f'{attribute}="{name}?v={revision}"')
    if page.count("<body>") != 1:
        raise ValueError("The preview body marker is missing or ambiguous.")
    return page.replace("<body>", f'<body data-preview-revision="{revision}">').encode("utf-8")


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".mjs": "text/javascript; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".ttf": "font/ttf",
    }

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_head(self):
        # Old Last-Modified validators must not preserve a mixed local-development bundle.
        for name in ("If-Modified-Since", "If-None-Match"):
            if name in self.headers:
                del self.headers[name]
        if urlsplit(self.path).path in {"/", "/index.html"}:
            directory = Path(self.directory)
            revision = preview_revision(directory)
            payload = versioned_index(directory, revision)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Preview-Revision", revision)
            self.end_headers()
            return BytesIO(payload)
        return super().send_head()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4174)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Use a port between1and65535.")
    handler = partial(Handler, directory=str(Path(__file__).resolve().parent))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Isolated cream study: http://127.0.0.1:{args.port}/", flush=True)
        server.serve_forever()
