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

Then open:

```text
http://127.0.0.1:8765
```

The Characters tab renders as a card grid instead of the table used by Music and Name Plates. Clicking a character thumbnail opens a larger in-page image preview modal, and entries without a resolved character image show a placeholder card.

Optional terminal-only usage:

```powershell
python server.py --host 127.0.0.1 --port 8765 --game-root "<path-to-game-folder>"
```

You can also set `CHUNITHM_GAME_ROOT` before running the server if you do not want to use the folder picker.


## Project layout

- `server.py` - HTTP server, routes, and startup.
- `selection.py` - command-line path handling and folder picker.
- `scanner.py` - XML parsing, catalog scanning, filtering, and jacket/character image path lookup.
- `image_utils.py` - DDS-to-PNG conversion helpers.
- `store.py` - in-memory catalog plus jacket and character image PNG caches.
- `models.py` - shared catalog data model.
- `config.py` - shared constants.
- `static/` - browser UI assets.

## API

- `GET /api/jacket?source=<game-relative-path>` - returns a music jacket image as `image/png`.
- `GET /api/character-image?source=<game-relative-path>` - returns a character image as `image/png`.

Both image endpoints convert `.dds` files to PNG on demand and cache the PNG bytes in memory. Running `/api/rescan` clears both image caches along with replacing the catalog, and the Characters UI appends the catalog generation timestamp to character-image requests so browsers fetch refreshed art after a rescan.

## Notes

Song jacket and character `.dds` textures are converted to PNG on demand with [`py_dds`](https://github.com/robertkist/py_dds). Other proprietary audio/chart formats such as `.acb`, `.awb`, and `.c2s` are cataloged as paths and metadata only.
