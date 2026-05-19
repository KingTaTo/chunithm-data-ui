from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from models import Catalog
from scanner import dedupe_characters, find_character_image_path, parse_character


class ScannerCharacterTests(unittest.TestCase):
    def test_dedupe_characters_prefers_option_character_for_repeated_id(self) -> None:
        items = [
            {
                "id": 42,
                "name": "Base Character",
                "source": "data/character/0042/Chara.xml",
                "pack": "base",
                "imageUrl": "/api/character-image?source=data/character/0042/Chara.xml",
                "imageThumbUrl": "/api/character-image?source=data/character/0042/Chara.xml&variant=thumb",
            },
            {
                "id": 42,
                "name": "Option Character",
                "source": "bin/option/A001/chara/chara0042/Chara.xml",
                "pack": "A001",
                "imageUrl": "/api/character-image?source=bin/option/A001/chara/chara0042/Chara.xml",
                "imageThumbUrl": "/api/character-image?source=bin/option/A001/chara/chara0042/Chara.xml&variant=thumb",
            },
            {
                "id": 43,
                "name": "Unique Character",
                "source": "data/character/0043/Chara.xml",
                "pack": "base",
            },
        ]

        result = dedupe_characters(items)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 42)
        self.assertEqual(result[0]["source"], "bin/option/A001/chara/chara0042/Chara.xml")
        self.assertEqual(result[1]["id"], 43)

    def test_parse_character_includes_image_and_character_image_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "data" / "character" / "0001" / "CHU_UI_Character_0001.xml"
            image_path = game_root / "data" / "character" / "0001" / "images" / "character-card.dds"
            xml_path.parent.mkdir(parents=True)
            image_path.parent.mkdir(parents=True, exist_ok=True)
            xml_path.write_text(
                """<CharacterData>
                <dataName>character0001</dataName>
                <name><id>1</id><str>Test Character</str></name>
                <works><str>Test Works</str></works>
                <defaultImages><str>card</str></defaultImages>
                <image><path>images/character-card.dds</path></image>
                <defaultHave>true</defaultHave>
                </CharacterData>""",
                encoding="utf-8",
            )
            image_path.write_bytes(b"dds")

            item = parse_character(xml_path, game_root)

            self.assertEqual(item["image"], "images/character-card.dds")
            self.assertEqual(
                item["imageUrl"],
                "/api/character-image?source=data/character/0001/CHU_UI_Character_0001.xml",
            )
            self.assertEqual(
                item["imageThumbUrl"],
                "/api/character-image?source=data/character/0001/CHU_UI_Character_0001.xml&variant=thumb",
            )

    def test_parse_character_uses_empty_image_url_when_image_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "data" / "character" / "0002" / "CHU_UI_Character_0002.xml"
            xml_path.parent.mkdir(parents=True)
            xml_path.write_text(
                """<CharacterData>
                <dataName>character0002</dataName>
                <name><id>2</id><str>No Image</str></name>
                <defaultImages><str>none</str></defaultImages>
                </CharacterData>""",
                encoding="utf-8",
            )

            item = parse_character(xml_path, game_root)

            self.assertEqual(item["image"], "")
            self.assertEqual(item["imageUrl"], "")
            self.assertEqual(item["imageThumbUrl"], "")

    def test_find_character_image_path_resolves_relative_to_character_xml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "data" / "character" / "0003" / "CHU_UI_Character_0003.xml"
            image_path = game_root / "data" / "character" / "0003" / "images" / "portrait.dds"
            image_path.parent.mkdir(parents=True)
            xml_path.write_text(
                """<CharacterData>
                <name><id>3</id><str>Relative Path</str></name>
                <image><path>images/portrait.dds</path></image>
                </CharacterData>""",
                encoding="utf-8",
            )
            image_path.write_bytes(b"dds")
            item = parse_character(xml_path, game_root)
            catalog = Catalog(game_root=game_root, generated_at=0.0, characters=[item])

            resolved = find_character_image_path(catalog, item["source"])

            self.assertEqual(resolved, image_path.resolve())

    def test_parse_character_uses_dds_manifest_backed_default_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "Option" / "A133" / "chara" / "chara018150" / "Chara.xml"
            manifest_path = game_root / "Option" / "A133" / "ddsImage" / "ddsImage018150" / "DDSImage.xml"
            image_path = manifest_path.parent / "CHU_UI_Character_1815_00_00.dds"
            xml_path.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            xml_path.write_text(
                """<CharacterData>
                <name><id>1815</id><str>Real Layout</str></name>
                <defaultImages><str>chara1815_00</str></defaultImages>
                </CharacterData>""",
                encoding="utf-8",
            )
            manifest_path.write_text(
                """<DDSImageData>
                <name><str>chara1815_00</str></name>
                <ddsFile0><path>CHU_UI_Character_1815_00_00.dds</path></ddsFile0>
                </DDSImageData>""",
                encoding="utf-8",
            )
            image_path.write_bytes(b"dds")

            item = parse_character(xml_path, game_root)

            self.assertEqual(item["image"], "")
            self.assertEqual(item["imageKey"], "chara1815_00")
            self.assertEqual(
                item["imageUrl"],
                "/api/character-image?source=Option/A133/chara/chara018150/Chara.xml",
            )
            self.assertEqual(
                item["imageThumbUrl"],
                "/api/character-image?source=Option/A133/chara/chara018150/Chara.xml&variant=thumb",
            )

    def test_find_character_image_path_resolves_dds_manifest_relative_to_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "Option" / "A133" / "chara" / "chara018150" / "Chara.xml"
            manifest_path = game_root / "Option" / "A133" / "ddsImage" / "ddsImage018150" / "DDSImage.xml"
            image_path = manifest_path.parent / "CHU_UI_Character_1815_00_00.dds"
            xml_path.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            xml_path.write_text(
                """<CharacterData>
                <name><id>1815</id><str>Real Layout</str></name>
                <defaultImages><str>chara1815_00</str></defaultImages>
                </CharacterData>""",
                encoding="utf-8",
            )
            manifest_path.write_text(
                """<DDSImageData>
                <name><str>chara1815_00</str></name>
                <ddsFile0><path>CHU_UI_Character_1815_00_00.dds</path></ddsFile0>
                </DDSImageData>""",
                encoding="utf-8",
            )
            image_path.write_bytes(b"dds")
            item = parse_character(xml_path, game_root)
            catalog = Catalog(game_root=game_root, generated_at=0.0, characters=[item])

            resolved = find_character_image_path(catalog, item["source"])

            self.assertEqual(resolved, image_path.resolve())

    def test_find_character_image_path_rejects_missing_and_escaping_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            missing_xml = game_root / "data" / "character" / "0004" / "CHU_UI_Character_0004.xml"
            escape_xml = game_root / "data" / "character" / "0005" / "CHU_UI_Character_0005.xml"
            missing_xml.parent.mkdir(parents=True)
            escape_xml.parent.mkdir(parents=True)
            missing_xml.write_text(
                """<CharacterData>
                <name><id>4</id><str>Missing Image</str></name>
                <image><path>images/missing.dds</path></image>
                </CharacterData>""",
                encoding="utf-8",
            )
            escape_xml.write_text(
                """<CharacterData>
                <name><id>5</id><str>Escaping Image</str></name>
                <image><path>../../../../outside.dds</path></image>
                </CharacterData>""",
                encoding="utf-8",
            )
            catalog = Catalog(
                game_root=game_root,
                generated_at=0.0,
                characters=[
                    parse_character(missing_xml, game_root),
                    parse_character(escape_xml, game_root),
                ],
            )

            self.assertEqual(catalog.characters[0]["image"], "images/missing.dds")
            self.assertEqual(catalog.characters[0]["imageUrl"], "")
            self.assertEqual(catalog.characters[0]["imageThumbUrl"], "")
            self.assertEqual(catalog.characters[1]["image"], "../../../../outside.dds")
            self.assertEqual(catalog.characters[1]["imageUrl"], "")
            self.assertEqual(catalog.characters[1]["imageThumbUrl"], "")

            self.assertIsNone(
                find_character_image_path(catalog, "data/character/0004/CHU_UI_Character_0004.xml")
            )
            self.assertIsNone(
                find_character_image_path(catalog, "data/character/0005/CHU_UI_Character_0005.xml")
            )

    def test_find_character_image_path_returns_none_for_invalid_source_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "data" / "character" / "0006" / "CHU_UI_Character_0006.xml"
            image_path = game_root / "data" / "character" / "0006" / "images" / "portrait.dds"
            image_path.parent.mkdir(parents=True)
            xml_path.write_text(
                """<CharacterData>
                <name><id>6</id><str>Invalid Source</str></name>
                <image><path>images/portrait.dds</path></image>
                </CharacterData>""",
                encoding="utf-8",
            )
            image_path.write_bytes(b"dds")
            item = parse_character(xml_path, game_root)
            item["source"] = "../escape.xml"
            catalog = Catalog(game_root=game_root, generated_at=0.0, characters=[item])

            self.assertIsNone(find_character_image_path(catalog, "../escape.xml"))

    def test_find_character_image_path_rejects_missing_and_escaping_manifest_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            missing_xml = game_root / "Option" / "A133" / "chara" / "chara018151" / "Chara.xml"
            escape_xml = game_root / "Option" / "A133" / "chara" / "chara018152" / "Chara.xml"
            missing_manifest = game_root / "Option" / "A133" / "ddsImage" / "ddsImage018151" / "DDSImage.xml"
            escape_manifest = game_root / "Option" / "A133" / "ddsImage" / "ddsImage018152" / "DDSImage.xml"
            missing_xml.parent.mkdir(parents=True)
            escape_xml.parent.mkdir(parents=True)
            missing_manifest.parent.mkdir(parents=True)
            escape_manifest.parent.mkdir(parents=True)
            missing_xml.write_text(
                """<CharacterData>
                <name><id>18151</id><str>Missing Manifest Image</str></name>
                <defaultImages><str>chara18151_00</str></defaultImages>
                </CharacterData>""",
                encoding="utf-8",
            )
            escape_xml.write_text(
                """<CharacterData>
                <name><id>18152</id><str>Escaping Manifest Image</str></name>
                <defaultImages><str>chara18152_00</str></defaultImages>
                </CharacterData>""",
                encoding="utf-8",
            )
            missing_manifest.write_text(
                """<DDSImageData>
                <name><str>chara18151_00</str></name>
                <ddsFile0><path>missing.dds</path></ddsFile0>
                </DDSImageData>""",
                encoding="utf-8",
            )
            escape_manifest.write_text(
                """<DDSImageData>
                <name><str>chara18152_00</str></name>
                <ddsFile0><path>../../../../outside.dds</path></ddsFile0>
                </DDSImageData>""",
                encoding="utf-8",
            )
            catalog = Catalog(
                game_root=game_root,
                generated_at=0.0,
                characters=[
                    parse_character(missing_xml, game_root),
                    parse_character(escape_xml, game_root),
                ],
            )

            self.assertEqual(catalog.characters[0]["imageUrl"], "")
            self.assertEqual(catalog.characters[0]["imageThumbUrl"], "")
            self.assertEqual(catalog.characters[1]["imageUrl"], "")
            self.assertEqual(catalog.characters[1]["imageThumbUrl"], "")
            self.assertIsNone(find_character_image_path(catalog, catalog.characters[0]["source"]))
            self.assertIsNone(find_character_image_path(catalog, catalog.characters[1]["source"]))

    def test_parse_character_uses_data_a000_manifest_for_azen_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "Option" / "AZEN" / "chara" / "chara000000" / "Chara.xml"
            manifest_path = game_root / "data" / "a000" / "ddsImage" / "ddsImage000000" / "DDSImage.xml"
            image_path = manifest_path.parent / "CHU_UI_Character_0000_00_00.dds"
            xml_path.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            xml_path.write_text(
                """<CharacterData>
                <name><id>0</id><str>Chuni Penguin</str></name>
                <defaultImages><str>chara0000_00</str></defaultImages>
                </CharacterData>""",
                encoding="utf-8",
            )
            manifest_path.write_text(
                """<DDSImageData>
                <name><str>chara0000_00</str></name>
                <ddsFile0><path>CHU_UI_Character_0000_00_00.dds</path></ddsFile0>
                </DDSImageData>""",
                encoding="utf-8",
            )
            image_path.write_bytes(b"dds")

            item = parse_character(xml_path, game_root)

            self.assertEqual(
                item["imageUrl"],
                "/api/character-image?source=Option/AZEN/chara/chara000000/Chara.xml",
            )
            self.assertEqual(
                item["imageThumbUrl"],
                "/api/character-image?source=Option/AZEN/chara/chara000000/Chara.xml&variant=thumb",
            )

    def test_find_character_image_path_uses_data_a000_manifest_for_azen_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "bin" / "option" / "AZEN" / "chara" / "chara000000" / "Chara.xml"
            manifest_path = game_root / "data" / "a000" / "ddsImage" / "ddsImage000000" / "DDSImage.xml"
            image_path = manifest_path.parent / "CHU_UI_Character_0000_00_00.dds"
            xml_path.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            xml_path.write_text(
                """<CharacterData>
                <name><id>0</id><str>Chuni Penguin</str></name>
                <defaultImages><str>chara0000_00</str></defaultImages>
                </CharacterData>""",
                encoding="utf-8",
            )
            manifest_path.write_text(
                """<DDSImageData>
                <name><str>chara0000_00</str></name>
                <ddsFile0><path>CHU_UI_Character_0000_00_00.dds</path></ddsFile0>
                </DDSImageData>""",
                encoding="utf-8",
            )
            image_path.write_bytes(b"dds")
            item = parse_character(xml_path, game_root)
            catalog = Catalog(game_root=game_root, generated_at=0.0, characters=[item])

            resolved = find_character_image_path(catalog, item["source"])

            self.assertEqual(resolved, image_path.resolve())

    def test_parse_character_does_not_use_data_a000_manifest_for_non_azen_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "Option" / "A133" / "chara" / "chara000000" / "Chara.xml"
            manifest_path = game_root / "data" / "a000" / "ddsImage" / "ddsImage000000" / "DDSImage.xml"
            image_path = manifest_path.parent / "CHU_UI_Character_0000_00_00.dds"
            xml_path.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            xml_path.write_text(
                """<CharacterData>
                <name><id>0</id><str>Wrong Pack</str></name>
                <defaultImages><str>chara0000_00</str></defaultImages>
                </CharacterData>""",
                encoding="utf-8",
            )
            manifest_path.write_text(
                """<DDSImageData>
                <name><str>chara0000_00</str></name>
                <ddsFile0><path>CHU_UI_Character_0000_00_00.dds</path></ddsFile0>
                </DDSImageData>""",
                encoding="utf-8",
            )
            image_path.write_bytes(b"dds")

            item = parse_character(xml_path, game_root)

            self.assertEqual(item["imageUrl"], "")
            self.assertEqual(item["imageThumbUrl"], "")

    def test_find_character_image_path_prefers_pack_local_manifest_for_azen_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "Option" / "AZEN" / "chara" / "chara000000" / "Chara.xml"
            local_manifest_path = game_root / "Option" / "AZEN" / "ddsImage" / "ddsImage000000" / "DDSImage.xml"
            local_image_path = local_manifest_path.parent / "local.dds"
            fallback_manifest_path = game_root / "data" / "a000" / "ddsImage" / "ddsImage000000" / "DDSImage.xml"
            fallback_image_path = fallback_manifest_path.parent / "fallback.dds"
            xml_path.parent.mkdir(parents=True)
            local_manifest_path.parent.mkdir(parents=True)
            fallback_manifest_path.parent.mkdir(parents=True)
            xml_path.write_text(
                """<CharacterData>
                <name><id>0</id><str>Chuni Penguin</str></name>
                <defaultImages><str>chara0000_00</str></defaultImages>
                </CharacterData>""",
                encoding="utf-8",
            )
            local_manifest_path.write_text(
                """<DDSImageData>
                <name><str>chara0000_00</str></name>
                <ddsFile0><path>local.dds</path></ddsFile0>
                </DDSImageData>""",
                encoding="utf-8",
            )
            fallback_manifest_path.write_text(
                """<DDSImageData>
                <name><str>chara0000_00</str></name>
                <ddsFile0><path>fallback.dds</path></ddsFile0>
                </DDSImageData>""",
                encoding="utf-8",
            )
            local_image_path.write_bytes(b"local")
            fallback_image_path.write_bytes(b"fallback")
            item = parse_character(xml_path, game_root)
            catalog = Catalog(game_root=game_root, generated_at=0.0, characters=[item])

            resolved = find_character_image_path(catalog, item["source"])

            self.assertEqual(resolved, local_image_path.resolve())


if __name__ == "__main__":
    unittest.main()
