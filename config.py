from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = APP_ROOT / "static"
MAX_ITEMS_PER_CATEGORY = 100000

TAG_PATTERNS = {
    "music": "Music.xml",
    "characters": "Chara.xml",
    "nameplates": "NamePlate.xml",
}
