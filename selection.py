from __future__ import annotations

import os
from pathlib import Path


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
