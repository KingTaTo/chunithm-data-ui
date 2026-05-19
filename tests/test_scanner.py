from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from models import Catalog
from scanner import find_character_image_path, parse_character


class ScannerCharacterTests(unittest.TestCase):
    def test_parse_character_includes_image_and_character_image_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = Path(tmpdir)
            xml_path = game_root / "data" / "character" / "0001" / "CHU_UI_Character_0001.xml"
            xml_path.parent.mkdir(parents=True)
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

            item = parse_character(xml_path, game_root)

            self.assertEqual(item["image"], "images/character-card.dds")
            self.assertEqual(
                item["imageUrl"],
                "/api/character-image?source=data/character/0001/CHU_UI_Character_0001.xml",
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


if __name__ == "__main__":
    unittest.main()
