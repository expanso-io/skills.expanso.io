# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Serve the generated site with repository reports and SPA routes."""

from __future__ import annotations

import argparse
import mimetypes
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
ROOT_ASSETS = {
    "/catalog.json": REPO / "catalog.json",
    "/catalog-minimal.json": REPO / "catalog-minimal.json",
    "/validation-report.json": REPO / "validation-report.json",
    "/example-conformance.json": REPO / "example-conformance.json",
}


class SiteHandler(SimpleHTTPRequestHandler):
    """Use authoritative root reports and render deep links as the SPA."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS), **kwargs)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        asset = ROOT_ASSETS.get(path)
        if asset is not None:
            self._send_file(asset, "application/json")
            return
        if re.fullmatch(r"/skill/[^/]+/?", path):
            self._send_file(DOCS / "404.html", "text/html; charset=utf-8")
            return
        skill_asset = self._skill_asset(path)
        if skill_asset is not None:
            content_type = mimetypes.guess_type(skill_asset.name)[0]
            self._send_file(skill_asset, content_type or "application/octet-stream")
            return
        super().do_GET()

    @staticmethod
    def _skill_asset(request_path: str) -> Path | None:
        match = re.fullmatch(
            r"/(?P<skill>[A-Za-z0-9-]+)/(?P<file>[A-Za-z0-9._-]+)",
            request_path,
        )
        if match is None:
            return None
        for category in (REPO / "skills").iterdir():
            candidate = category / match.group("skill") / match.group("file")
            if category.is_dir() and candidate.is_file():
                return candidate
        return None

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


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
