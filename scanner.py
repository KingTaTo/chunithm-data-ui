from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote
import xml.etree.ElementTree as ET

from config import MAX_ITEMS_PER_CATEGORY, TAG_PATTERNS
from models import Catalog

MusicItem = dict[str, Any]


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


def pack_name(path: Path, root_dir: Path) -> str:
    rel = path.relative_to(root_dir).parts
    if len(rel) >= 3 and rel[0].lower() == "bin" and rel[1].lower() == "option":
        return rel[2]
    if len(rel) >= 2 and rel[0].lower() in {"data", "option"}:
        return rel[1] if rel[0].lower() == "option" else "base"
    return "base"


def parse_chart(chart: ET.Element) -> dict[str, str]:
    level = child_int(chart, "level")
    decimal = child_int(chart, "levelDecimal")
    level_text = str(level) if decimal == 0 else f"{level}.{str(decimal).rstrip('0')}"
    return {
        "type": child_text(chart, "type/data") or child_text(chart, "type/str"),
        "level": level_text,
        "file": child_text(chart, "file/path"),
        "designer": child_text(chart, "notesDesigner"),
    }


# Music entries include chart levels, jacket filenames, pack names, and source paths.
def parse_music(path: Path, root_dir: Path) -> MusicItem:
    root = parse_xml(path)
    jacket = child_text(root, "jaketFile/path") if root is not None else ""
    source = relpath(path, root_dir)
    item: MusicItem = {
        "dataName": child_text(root, "dataName") if root is not None else fallback_field(path, "dataName"),
        "id": child_int(root, "name/id") if root is not None else 0,
        "name": child_text(root, "name/str") if root is not None else "",
        "artist": child_text(root, "artistName/str") if root is not None else "",
        "genre": "",
        "jacket": jacket,
        "jacketUrl": f"/api/jacket?source={quote(source)}" if jacket else "",
        "enabled": not child_bool(root, "disableFlag") if root is not None else True,
        "enableUltima": child_bool(root, "enableUltima") if root is not None else False,
        "source": source,
        "pack": pack_name(path, root_dir),
        "charts": [],
    }
    if root is None:
        item["name"] = item["dataName"] or path.parent.name
        return item

    genre = root.find("genreNames/list/StringID/str")
    item["genre"] = clean_text(genre.text if genre is not None else "")
    item["charts"] = [parse_chart(chart) for chart in root.findall("fumens/MusicFumenData") if child_bool(chart, "enable")]
    return item


def parse_character(path: Path, root_dir: Path) -> dict[str, Any]:
    root = parse_xml(path)
    image = child_text(root, "image/path") if root is not None else ""
    image_key = child_text(root, "defaultImages/str") if root is not None else ""
    source = relpath(path, root_dir)
    image_path = resolve_character_image_path(path, root_dir, image, image_key)
    image_url = f"/api/character-image?source={quote(source)}" if image_path is not None else ""
    return {
        "dataName": child_text(root, "dataName") if root is not None else fallback_field(path, "dataName"),
        "id": child_int(root, "name/id") if root is not None else 0,
        "name": child_text(root, "name/str") if root is not None else path.parent.name,
        "works": child_text(root, "works/str") if root is not None else "",
        "image": image,
        "imageUrl": image_url,
        "imageKey": image_key,
        "defaultHave": child_bool(root, "defaultHave") if root is not None else False,
        "enabled": not child_bool(root, "disableFlag") if root is not None else True,
        "source": source,
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


def find_jacket_path(catalog: Catalog, source: str) -> Path | None:
    item = next((entry for entry in catalog.music if entry.get("source") == source), None)
    if not item or not item.get("jacket"):
        return None

    source_path = safe_game_path(catalog.game_root, source)
    jacket_path = (source_path.parent / item["jacket"]).resolve()
    if not is_under_root(jacket_path, catalog.game_root) or not jacket_path.is_file():
        return None
    return jacket_path


def find_character_image_path(catalog: Catalog, source: str) -> Path | None:
    try:
        source_path = safe_game_path(catalog.game_root, source)
    except ValueError:
        return None

    item = next((entry for entry in catalog.characters if entry.get("source") == source), None)
    if not item:
        return None

    return resolve_character_image_path(
        source_path,
        catalog.game_root,
        str(item.get("image") or ""),
        str(item.get("imageKey") or ""),
    )


def resolve_character_image_path(
    character_xml_path: Path,
    root_dir: Path,
    image: str,
    image_key: str,
) -> Path | None:
    direct_image_path = resolve_character_direct_image_path(character_xml_path, root_dir, image)
    if direct_image_path is not None:
        return direct_image_path
    return resolve_character_manifest_image_path(character_xml_path, root_dir, image_key)


def resolve_character_direct_image_path(character_xml_path: Path, root_dir: Path, image: str) -> Path | None:
    if not image:
        return None
    image_path = (character_xml_path.parent / image).resolve()
    if not is_under_root(image_path, root_dir) or not image_path.is_file():
        return None
    return image_path


def resolve_character_manifest_image_path(character_xml_path: Path, root_dir: Path, image_key: str) -> Path | None:
    if not image_key:
        return None

    manifest_path = character_dds_manifest_path(character_xml_path, root_dir)
    if manifest_path is None or not manifest_path.is_file():
        return None

    manifest_root = parse_xml(manifest_path)
    if manifest_root is None:
        return None

    if child_text(manifest_root, "name/str") != image_key:
        return None

    dds_relative_path = child_text(manifest_root, "ddsFile0/path")
    if not dds_relative_path:
        return None

    image_path = (manifest_path.parent / dds_relative_path).resolve()
    if not is_under_root(image_path, root_dir) or not image_path.is_file():
        return None
    return image_path


def character_dds_manifest_path(character_xml_path: Path, root_dir: Path) -> Path | None:
    try:
        relative_parts = character_xml_path.relative_to(root_dir).parts
    except ValueError:
        return None

    chara_dir_name = character_xml_path.parent.name
    if not chara_dir_name.startswith("chara"):
        return None
    suffix = chara_dir_name[len("chara") :]
    if not suffix:
        return None

    lower_parts = tuple(part.casefold() for part in relative_parts)
    if len(relative_parts) >= 4 and lower_parts[0] == "option":
        pack_root = root_dir / relative_parts[0] / relative_parts[1]
    elif len(relative_parts) >= 5 and lower_parts[0] == "bin" and lower_parts[1] == "option":
        pack_root = root_dir / relative_parts[0] / relative_parts[1] / relative_parts[2]
    else:
        return None

    manifest_path = (pack_root / "ddsImage" / f"ddsImage{suffix}" / "DDSImage.xml").resolve()
    if not is_under_root(manifest_path, root_dir):
        return None
    return manifest_path


def safe_game_path(root_dir: Path, relative_path: str) -> Path:
    relative = Path(relative_path.replace("/", os.sep))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid game-relative path")
    resolved = (root_dir / relative).resolve()
    if not is_under_root(resolved, root_dir):
        raise ValueError("Resolved path escaped the selected game folder")
    return resolved


def is_under_root(path: Path, root_dir: Path) -> bool:
    try:
        path.relative_to(root_dir.resolve())
        return True
    except ValueError:
        return False


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


def music_dedupe_rank(item: MusicItem) -> tuple[int, int, str]:
    source = str(item.get("source", "")).replace("\\", "/").casefold()
    pack = str(item.get("pack", "")).casefold()
    if source.startswith("bin/option/"):
        location_rank = 0
    elif source.startswith("data/"):
        location_rank = 1
    else:
        location_rank = 2
    pack_rank = 1 if pack == "azen" else 0
    return (location_rank, pack_rank, source)


def music_dedupe_key(item: MusicItem) -> tuple[str, int | str]:
    music_id = int(item.get("id") or 0)
    if music_id >= 0:
        return ("id", music_id)
    data_name = str(item.get("dataName") or item.get("source") or "")
    return ("dataName", data_name)


def dedupe_music(items: list[MusicItem]) -> list[MusicItem]:
    by_key: dict[tuple[str, int | str], MusicItem] = {}
    for item in items:
        key = music_dedupe_key(item)
        current = by_key.get(key)
        if current is None or music_dedupe_rank(item) < music_dedupe_rank(current):
            by_key[key] = item
    return sorted(by_key.values(), key=lambda item: (int(item.get("id") or 0), str(item.get("source", ""))))


def scan_game_root(root_dir: Path) -> Catalog:
    root_dir = root_dir.resolve()
    if not root_dir.exists():
        raise FileNotFoundError(f"Game root does not exist: {root_dir}")
    catalog = Catalog(game_root=root_dir, generated_at=time.time())
    catalog.stats = scan_files(root_dir)
    catalog.music = dedupe_music(scan_category(root_dir, TAG_PATTERNS["music"], parse_music))
    catalog.characters = scan_category(root_dir, TAG_PATTERNS["characters"], parse_character)
    catalog.nameplates = scan_category(root_dir, TAG_PATTERNS["nameplates"], parse_nameplate)
    for key in ["music", "characters", "nameplates"]:
        if len(getattr(catalog, key)) >= MAX_ITEMS_PER_CATEGORY:
            catalog.warnings.append(f"{key} was capped at {MAX_ITEMS_PER_CATEGORY} items")
    return catalog


def searchable_text(item: dict[str, Any]) -> str:
    return json.dumps(item, ensure_ascii=False, sort_keys=True).casefold()


# Apply lightweight search and filters server-side before sending rows to the browser.
def filter_items(items: list[dict[str, Any]], query: dict[str, list[str]]) -> tuple[list[dict[str, Any]], int]:
    search = query.get("q", [""])[0].casefold()
    pack = query.get("pack", [""])[0].casefold()
    enabled = query.get("enabled", [""])[0].casefold()
    result = items
    if search:
        result = [item for item in result if search in searchable_text(item)]
    if pack:
        result = [item for item in result if item.get("pack", "").casefold() == pack]
    if enabled in {"true", "false"}:
        wanted = enabled == "true"
        result = [item for item in result if bool(item.get("enabled", True)) == wanted]
    limit = min(int(query.get("limit", ["250"])[0] or 250), 1000)
    offset = max(int(query.get("offset", ["0"])[0] or 0), 0)
    return result[offset:offset + limit], len(result)
