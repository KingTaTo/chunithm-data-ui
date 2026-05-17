from __future__ import annotations

import argparse
import json
import mimetypes
import os
import posixpath
import re
import threading
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
import xml.etree.ElementTree as ET

APP_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = APP_ROOT / "static"
MAX_ITEMS_PER_CATEGORY = 100000

TAG_PATTERNS = {
    "music": "Music.xml",
    "characters": "Chara.xml",
    "nameplates": "NamePlate.xml",
}


@dataclass
class Catalog:
    game_root: Path
    generated_at: float
    stats: dict[str, Any] = field(default_factory=dict)
    music: list[dict[str, Any]] = field(default_factory=list)
    characters: list[dict[str, Any]] = field(default_factory=list)
    nameplates: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_summary(self) -> dict[str, Any]:
        return {
            "gameRoot": str(self.game_root),
            "generatedAt": self.generated_at,
            "stats": self.stats,
            "counts": {
                "music": len(self.music),
                "characters": len(self.characters),
                "nameplates": len(self.nameplates),
            },
            "warnings": self.warnings[:25],
        }


# Keeps the scanned catalog in memory so API calls do not rescan on every request.
class CatalogStore:
    def __init__(self, game_root: Path) -> None:
        self.game_root = game_root
        self._lock = threading.Lock()
        self._catalog: Catalog | None = None
        self._is_scanning = False
        self._last_error: str | None = None

    def get(self) -> Catalog | None:
        with self._lock:
            return self._catalog

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "isScanning": self._is_scanning,
                "lastError": self._last_error,
                "hasCatalog": self._catalog is not None,
                "summary": self._catalog.as_summary() if self._catalog else None,
            }

    def scan(self) -> Catalog:
        with self._lock:
            if self._is_scanning:
                existing = self._catalog
                if existing:
                    return existing
            self._is_scanning = True
            self._last_error = None

        try:
            catalog = scan_game_root(self.game_root)
            with self._lock:
                self._catalog = catalog
            return catalog
        except Exception as exc:  # pragma: no cover - surfaced through API
            with self._lock:
                self._last_error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            with self._lock:
                self._is_scanning = False


# Opens a local folder picker when no game directory was supplied on the command line.
def select_game_root_dialog() -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    selected = filedialog.askdirectory(title="Select your CHUNITHM game folder")
    root.destroy()
    return Path(selected) if selected else None


# Prefer explicit configuration, then fall back to an interactive folder selection.
def choose_game_root(cli_value: str | None) -> Path:
    if cli_value:
        return Path(cli_value)

    env_value = os.environ.get("CHUNITHM_GAME_ROOT")
    if env_value:
        return Path(env_value)

    selected = select_game_root_dialog()
    if selected:
        return selected

    raise SystemExit(
        "No game folder selected. Run again and choose the game folder, "
        "or pass --game-root with the folder path."
    )

def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.replace("\x00", "").split())


def child_text(node: ET.Element | None, path: str, default: str = "") -> str:
    if node is None:
        return default
    found = node.find(path)
    return clean_text(found.text if found is not None else default)


def child_int(node: ET.Element | None, path: str, default: int = 0) -> int:
    text = child_text(node, path, "")
    try:
        return int(text)
    except ValueError:
        return default


def child_bool(node: ET.Element | None, path: str, default: bool = False) -> bool:
    text = child_text(node, path, "").lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return default


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def parse_xml(path: Path) -> ET.Element | None:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError:
        # Some bundled XML is malformed because text encodings were damaged.
        # Salvage common fields with regex so the catalog remains useful.
        return None
    except OSError:
        return None


# Malformed metadata can still expose useful fields through simple tag recovery.
def fallback_field(path: Path, tag: str) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    match = re.search(rf"<{re.escape(tag)}>\s*(.*?)\s*</{re.escape(tag)}>", text, re.S)
    return clean_text(match.group(1) if match else "")


# Music entries include chart levels, jacket filenames, pack names, and source paths.
def parse_music(path: Path, root_dir: Path) -> dict[str, Any]:
    root = parse_xml(path)
    item = {
        "dataName": child_text(root, "dataName") if root is not None else fallback_field(path, "dataName"),
        "id": child_int(root, "name/id") if root is not None else 0,
        "name": child_text(root, "name/str") if root is not None else "",
        "artist": child_text(root, "artistName/str") if root is not None else "",
        "genre": "",
        "jacket": child_text(root, "jaketFile/path") if root is not None else fallback_field(path, "path"),
        "enabled": not child_bool(root, "disableFlag") if root is not None else True,
        "enableUltima": child_bool(root, "enableUltima") if root is not None else False,
        "source": relpath(path, root_dir),
        "pack": pack_name(path, root_dir),
        "charts": [],
    }
    if root is None:
        item["name"] = item["dataName"] or path.parent.name
        return item

    genre = root.find("genreNames/list/StringID/str")
    item["genre"] = clean_text(genre.text if genre is not None else "")

    for chart in root.findall("fumens/MusicFumenData"):
        enabled = child_bool(chart, "enable")
        if not enabled:
            continue
        level = child_int(chart, "level")
        decimal = child_int(chart, "levelDecimal")
        level_text = str(level) if decimal == 0 else f"{level}.{str(decimal).rstrip('0')}"
        item["charts"].append({
            "type": child_text(chart, "type/data") or child_text(chart, "type/str"),
            "level": level_text,
            "file": child_text(chart, "file/path"),
            "designer": child_text(chart, "notesDesigner"),
        })
    return item


def parse_character(path: Path, root_dir: Path) -> dict[str, Any]:
    root = parse_xml(path)
    return {
        "dataName": child_text(root, "dataName") if root is not None else fallback_field(path, "dataName"),
        "id": child_int(root, "name/id") if root is not None else 0,
        "name": child_text(root, "name/str") if root is not None else path.parent.name,
        "works": child_text(root, "works/str") if root is not None else "",
        "imageKey": child_text(root, "defaultImages/str") if root is not None else "",
        "defaultHave": child_bool(root, "defaultHave") if root is not None else False,
        "enabled": not child_bool(root, "disableFlag") if root is not None else True,
        "source": relpath(path, root_dir),
        "pack": pack_name(path, root_dir),
    }


def parse_nameplate(path: Path, root_dir: Path) -> dict[str, Any]:
    root = parse_xml(path)
    return {
        "dataName": child_text(root, "dataName") if root is not None else fallback_field(path, "dataName"),
        "id": child_int(root, "name/id") if root is not None else 0,
        "name": child_text(root, "name/str") if root is not None else path.parent.name,
        "image": child_text(root, "image/path") if root is not None else "",
        "defaultHave": child_bool(root, "defaultHave") if root is not None else False,
        "enabled": not child_bool(root, "disableFlag") if root is not None else True,
        "source": relpath(path, root_dir),
        "pack": pack_name(path, root_dir),
    }


def pack_name(path: Path, root_dir: Path) -> str:
    rel = path.relative_to(root_dir).parts
    if len(rel) >= 3 and rel[0].lower() == "bin" and rel[1].lower() == "option":
        return rel[2]
    if len(rel) >= 2 and rel[0].lower() in {"data", "option"}:
        return rel[1] if rel[0].lower() == "option" else "base"
    return "base"


# File stats are broad counts only; category details come from the specific XML scans.
def scan_files(root_dir: Path) -> dict[str, Any]:
    extension_counts: dict[str, int] = {}
    option_packs: set[str] = set()
    total = 0
    for path in root_dir.rglob("*"):
        if not path.is_file():
            continue
        total += 1
        ext = path.suffix.lower() or "[no extension]"
        extension_counts[ext] = extension_counts.get(ext, 0) + 1
        parts = path.relative_to(root_dir).parts
        if len(parts) >= 2 and parts[0].lower() == "option":
            option_packs.add(parts[1])
        if len(parts) >= 3 and parts[0].lower() == "bin" and parts[1].lower() == "option":
            option_packs.add(parts[2])
    return {
        "totalFiles": total,
        "extensions": sorted(extension_counts.items(), key=lambda pair: pair[1], reverse=True)[:30],
        "optionPacks": sorted(option_packs),
    }


def scan_category(root_dir: Path, file_name: str, parser) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in root_dir.rglob(file_name):
        if not path.is_file():
            continue
        items.append(parser(path, root_dir))
        if len(items) >= MAX_ITEMS_PER_CATEGORY:
            break
    return items


def scan_game_root(root_dir: Path) -> Catalog:
    root_dir = root_dir.resolve()
    if not root_dir.exists():
        raise FileNotFoundError(f"Game root does not exist: {root_dir}")
    catalog = Catalog(game_root=root_dir, generated_at=time.time())
    catalog.stats = scan_files(root_dir)
    catalog.music = scan_category(root_dir, TAG_PATTERNS["music"], parse_music)
    catalog.characters = scan_category(root_dir, TAG_PATTERNS["characters"], parse_character)
    catalog.nameplates = scan_category(root_dir, TAG_PATTERNS["nameplates"], parse_nameplate)
    for key in ["music", "characters", "nameplates"]:
        if len(getattr(catalog, key)) >= MAX_ITEMS_PER_CATEGORY:
            catalog.warnings.append(f"{key} was capped at {MAX_ITEMS_PER_CATEGORY} items")
    return catalog


# Apply lightweight search and filters server-side before sending rows to the browser.
def filter_items(items: list[dict[str, Any]], query: dict[str, list[str]]) -> list[dict[str, Any]]:
    search = query.get("q", [""])[0].casefold()
    pack = query.get("pack", [""])[0].casefold()
    enabled = query.get("enabled", [""])[0].casefold()
    result = items
    if search:
        result = [item for item in result if search in json.dumps(item, ensure_ascii=False).casefold()]
    if pack:
        result = [item for item in result if item.get("pack", "").casefold() == pack]
    if enabled in {"true", "false"}:
        wanted = enabled == "true"
        result = [item for item in result if bool(item.get("enabled", True)) == wanted]
    limit = min(int(query.get("limit", ["250"])[0] or 250), 1000)
    offset = max(int(query.get("offset", ["0"])[0] or 0), 0)
    return result[offset:offset + limit]


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
        if parsed.path.startswith("/api/"):
            category = parsed.path.removeprefix("/api/")
            catalog = self.ensure_catalog()
            if category not in {"music", "characters", "nameplates"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            items = getattr(catalog, category)
            self.send_json({"items": filter_items(items, parse_qs(parsed.query)), "total": len(items)})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")

    def ensure_catalog(self) -> Catalog:
        return self.store.get() or self.store.scan()

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






