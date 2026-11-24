"""Serve only the generated public site, on loopback, with portable MIME types."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class PreviewHandler(SimpleHTTPRequestHandler):
    # Windows file associations can otherwise label ES modules as text/plain.
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".mjs": "text/javascript; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".svg": "image/svg+xml",
        ".ttf": "font/ttf",
        ".webp": "image/webp",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    public = Path(__file__).resolve().parents[1] / "site"
    if not (public / "index.html").is_file():
        parser.error("The public site is missing. Run npm run build first.")
    handler = partial(PreviewHandler, directory=str(public))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Bakery prototype: http://127.0.0.1:{args.port}/", flush=True)
        print(f"Public files only: {public}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nPreview stopped.", flush=True)


if __name__ == "__main__":
    main()
