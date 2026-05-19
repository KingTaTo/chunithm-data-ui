from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from image_utils import dds_to_png
from models import Catalog
from scanner import find_character_image_path, find_jacket_path, scan_game_root


# Keeps the scanned catalog and converted jacket images in memory between API calls.
class CatalogStore:
    def __init__(self, game_root: Path) -> None:
        self.game_root = game_root
        self._lock = threading.Lock()
        self._catalog: Catalog | None = None
        self._jacket_cache: dict[str, bytes] = {}
        self._character_image_cache: dict[str, bytes] = {}
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
                self._jacket_cache.clear()
                self._character_image_cache.clear()
            return catalog
        except Exception as exc:  # pragma: no cover - surfaced through API
            with self._lock:
                self._last_error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            with self._lock:
                self._is_scanning = False

    def jacket_png(self, source: str) -> bytes:
        with self._lock:
            cached = self._jacket_cache.get(source)
            if cached is not None:
                return cached

        catalog = self.get() or self.scan()
        jacket_path = find_jacket_path(catalog, source)
        if jacket_path is None:
            raise FileNotFoundError("No jacket DDS file was found for this music entry")

        png_data = dds_to_png(jacket_path)
        with self._lock:
            self._jacket_cache[source] = png_data
        return png_data

    def character_image_png(self, source: str) -> bytes:
        with self._lock:
            cached = self._character_image_cache.get(source)
            if cached is not None:
                return cached

        catalog = self.get() or self.scan()
        image_path = find_character_image_path(catalog, source)
        if image_path is None:
            raise FileNotFoundError("No character DDS file was found for this character entry")

        png_data = dds_to_png(image_path)
        with self._lock:
            self._character_image_cache[source] = png_data
        return png_data
