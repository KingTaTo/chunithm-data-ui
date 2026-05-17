from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from config import STATIC_ROOT
from scanner import filter_items
from selection import choose_game_root
from store import CatalogStore


# Serves the static UI and read-only JSON endpoints from the selected game folder.
class Handler(SimpleHTTPRequestHandler):
    store: CatalogStore

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.serve_file(STATIC_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/static/"):
            relative = Path(unquote(parsed.path.removeprefix("/static/")))
            target = (STATIC_ROOT / relative).resolve()
            if not str(target).startswith(str(STATIC_ROOT.resolve())):
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            self.serve_file(target)
            return
        if parsed.path == "/api/status":
            self.send_json(self.store.status())
            return
        if parsed.path == "/api/rescan":
            catalog = self.store.scan()
            self.send_json(catalog.as_summary())
            return
        if parsed.path == "/api/summary":
            catalog = self.ensure_catalog()
            self.send_json(catalog.as_summary())
            return
        if parsed.path == "/api/jacket":
            self.serve_jacket(parse_qs(parsed.query))
            return
        if parsed.path.startswith("/api/"):
            category = parsed.path.removeprefix("/api/")
            catalog = self.ensure_catalog()
            if category not in {"music", "characters", "nameplates"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            items = getattr(catalog, category)
            filtered_items, total = filter_items(items, parse_qs(parsed.query))
            self.send_json({"items": filtered_items, "total": total})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")

    def ensure_catalog(self):
        return self.store.get() or self.store.scan()

    def serve_jacket(self, query: dict[str, list[str]]) -> None:
        source = query.get("source", [""])[0]
        if not source:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing source parameter")
            return
        try:
            data = self.store.jacket_png(source)
        except RuntimeError as exc:
            self.send_error(HTTPStatus.NOT_IMPLEMENTED, str(exc))
            return
        except (FileNotFoundError, ValueError) as exc:
            self.send_error(HTTPStatus.NOT_FOUND, str(exc))
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        guessed = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", guessed)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: Any) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Browse CHUNITHM game data in a local web UI.")
    parser.add_argument("--game-root", help="Path to the CHUNITHM game folder. If omitted, a folder picker opens.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    game_root = choose_game_root(args.game_root)
    store = CatalogStore(game_root)
    Handler.store = store
    print(f"Scanning {store.game_root} ...")
    store.scan()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"CHUNITHM Data UI running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()


