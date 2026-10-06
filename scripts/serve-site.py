# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Serve the staged GitHub Pages publication."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"


class SiteHandler(SimpleHTTPRequestHandler):
    """Serve staged Pages files and render deep links as the SPA."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS), **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), SiteHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
