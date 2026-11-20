# CHUNITHM Data UI

A small Python web UI for browsing CHUNITHM game data from a read-only game install folder.

## What it scans

- Music metadata from `Music.xml`
- Character metadata from `Chara.xml`
- Name plate metadata from `NamePlate.xml`
- Basic file type and option pack statistics

The scanner only reads the selected game folder. It does not modify game files.

## Install

```powershell
python -m pip install -r requirements.txt
```

## Run

```powershell
python server.py
```

A folder picker will open. Select the local folder that contains the game files.

```
chunithm-folder/ <--- Select this
├── bin/
├── data/
├── firm/
├── license/
└──  ...
```

Optional terminal-only usage:

```powershell
python server.py --host 127.0.0.1 --port 8765 --game-root "<path-to-game-folder>"
```

You can also set `CHUNITHM_GAME_ROOT` before running the server if you do not want to use the folder picker.


## Project layout

- `server.py` - HTTP server, routes, and startup.
- `selection.py` - command-line path handling and folder picker.
- `scanner.py` - XML parsing, catalog scanning, filtering, and jacket path lookup.
- `image_utils.py` - DDS-to-PNG conversion helpers.
- `store.py` - in-memory catalog and jacket cache.
- `models.py` - shared catalog data model.
- `config.py` - shared constants.
- `static/` - browser UI assets.
## Notes

Song jacket `.dds` textures are converted to PNG on demand with [`py_dds`](https://github.com/robertkist/py_dds). Other proprietary audio/chart formats such as `.acb`, `.awb`, and `.c2s` are cataloged as paths and metadata only.


