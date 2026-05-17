# CHUNITHM Data UI

A small Python web UI for browsing CHUNITHM game data from a read-only game install folder.

## What it scans

- Music metadata from `Music.xml`
- Character metadata from `Chara.xml`
- Name plate metadata from `NamePlate.xml`
- Basic file type and option pack statistics

The scanner only reads the selected game folder. It does not modify game files.

## Run

```powershell
python server.py
```

A folder picker will open. Select the local folder that contains the game files.

Then open:

```text
http://127.0.0.1:8765
```

Optional terminal-only usage:

```powershell
python server.py --host 127.0.0.1 --port 8765 --game-root "<path-to-game-folder>"
```

You can also set `CHUNITHM_GAME_ROOT` before running the server if you do not want to use the folder picker.

## Notes

The game contains many `.dds` textures and proprietary audio/chart formats. This UI catalogs paths and metadata, but browsers do not natively preview `.dds`, `.acb`, `.awb`, or `.c2s` files.
