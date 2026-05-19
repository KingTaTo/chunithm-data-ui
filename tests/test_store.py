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

    def test_character_image_png_resolves_manifest_backed_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            source = "Option/A133/chara/chara018150/Chara.xml"
            image_path = (
                game_root / "Option" / "A133" / "ddsImage" / "ddsImage018150" / "CHU_UI_Character_1815_00_00.dds"
            )
            manifest_path = image_path.parent / "DDSImage.xml"
            manifest_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"dds")
            manifest_path.write_text(
                """<DDSImageData>
                <name><str>chara1815_00</str></name>
                <ddsFile0><path>CHU_UI_Character_1815_00_00.dds</path></ddsFile0>
                </DDSImageData>""",
                encoding="utf-8",
            )
            store = CatalogStore(game_root)
            store._catalog = Catalog(
                game_root=game_root,
                generated_at=1.0,
                characters=[{"source": source, "image": "", "imageKey": "chara1815_00"}],
            )

            with patch("store.dds_to_png", return_value=b"png") as convert:
                png = store.character_image_png(source)

            self.assertEqual(png, b"png")
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
