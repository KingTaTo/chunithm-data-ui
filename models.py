from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
