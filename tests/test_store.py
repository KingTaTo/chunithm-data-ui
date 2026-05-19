from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from models import Catalog
from store import CatalogStore


class CatalogStoreTests(unittest.TestCase):
    def test_scan_clears_jacket_and_character_image_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            store = CatalogStore(game_root)
            store._jacket_cache["music.xml"] = b"jacket"
            store._character_image_cache["character.xml"] = b"character"
            catalog = Catalog(game_root=game_root, generated_at=1.0)

            with patch("store.scan_game_root", return_value=catalog):
                result = store.scan()

            self.assertIs(result, catalog)
            self.assertEqual(store._jacket_cache, {})
            self.assertEqual(store._character_image_cache, {})

    def test_character_image_png_reuses_cached_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            image_path = game_root / "data" / "character" / "0001" / "portrait.dds"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"dds")
            source = "data/character/0001/CHU_UI_Character_0001.xml"
            catalog = Catalog(
                game_root=game_root,
                generated_at=1.0,
                characters=[{"source": source, "image": "portrait.dds"}],
            )
            store = CatalogStore(game_root)
            store._catalog = catalog

            with patch("store.dds_to_png", return_value=b"png") as convert:
                first = store.character_image_png(source)
                second = store.character_image_png(source)

            self.assertEqual(first, b"png")
            self.assertIs(second, first)
            convert.assert_called_once_with(image_path.resolve())

    def test_character_image_png_raises_when_image_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            source = "data/character/0002/CHU_UI_Character_0002.xml"
            catalog = Catalog(
                game_root=game_root,
                generated_at=1.0,
                characters=[{"source": source, "image": "missing.dds"}],
            )
            store = CatalogStore(game_root)
            store._catalog = catalog

            with self.assertRaises(FileNotFoundError):
                store.character_image_png(source)


if __name__ == "__main__":
    unittest.main()
