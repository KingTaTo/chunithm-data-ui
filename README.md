# CHUNITHM Data UI

A small read-only Python web UI for browsing CHUNITHM game data from a local install folder.

The app scans extracted metadata files, exposes a few JSON endpoints, and renders a lightweight browser UI for music, character, and name plate browsing. It does not patch or rewrite game assets.

## Features

- Scans `Music.xml`, `Chara.xml`, and `NamePlate.xml` files anywhere under the selected game root.
- Deduplicates music entries so the preferred copy is shown when the same song appears in multiple packs.
- Deduplicates character entries by character ID so repeated pack copies do not render duplicate cards.
- Reports coarse file-extension statistics and detected option packs.
- Filters category results server-side with search, pagination, and enabled-state filtering.
- Converts jacket `.dds` textures to PNG on demand for browser display.
- Serves character previews as smaller PNG thumbnails and loads full-resolution character art only when selected.
- Keeps the last scanned catalog plus generated jacket, character thumbnail, and full character PNGs in memory for fast repeated requests.

## Requirements

- Python 3
- Network access the first time you install dependencies, because `py_dds` is installed from GitHub
- A local CHUNITHM game folder to scan

Optional:

- `tkinter` if you want the interactive folder picker shown by `python server.py`

If `tkinter` is unavailable, start the server with `--game-root` or set `CHUNITHM_GAME_ROOT`.

## Install

```bash
python -m pip install -r requirements.txt
```

If your shell does not provide `python`, use `python3` for the same commands.

Current dependency:

- [`py_dds`](https://github.com/robertkist/py_dds) for `.dds` to `.png` conversion

## Run

Interactive folder picker:

```bash
python server.py
```

Terminal-only startup:

```bash
python server.py --host 127.0.0.1 --port 8765 --game-root "<path-to-game-folder>"
```

Environment-variable startup:

```bash
CHUNITHM_GAME_ROOT="<path-to-game-folder>" python server.py
```

Then open `http://127.0.0.1:8765`.

Startup notes:

- The server performs an initial scan before it starts accepting requests.
- `--game-root` takes precedence over `CHUNITHM_GAME_ROOT`.
- If neither is set, the app tries to open a `tkinter` folder picker and exits if no folder is chosen.

## How scanning works

The scan is recursive from the selected root directory.

- Music records come from `Music.xml`
- Character records come from `Chara.xml`
- Name plate records come from `NamePlate.xml`
- File statistics are counted across all files under the root

The app caps each scanned category at `100000` items and reports a warning if the cap is reached.

If an XML file is malformed, the scanner falls back to a limited regex-based field recovery path for a few basic fields so the catalog remains partially usable.

Music entries are deduplicated before they are returned. When the same song appears in multiple locations, the scanner prefers:

1. `bin/option/...` copies first
2. then `data/...` copies
3. then any remaining locations

Within that ranking, the current logic gives the `azen` pack lower priority than other packs.

## UI behavior

- The browser UI loads the summary first, then fetches the active tab's rows.
- The search box sends debounced `q` requests to the current category endpoint.
- The Rescan button triggers `GET /api/rescan`, refreshes the summary, and clears the in-memory jacket, character thumbnail, and full character PNG caches as part of the new scan.
- All tabs page through results in slices of `100` items using the backend `limit` and `offset` parameters.
- Each tab remembers its own current result page when you switch away and back.
- Changing the search query or rescanning resets all tabs back to the first result page.
- The Characters tab uses thumbnail previews in the grid and requests the full PNG only when you open the modal.

## HTTP API

The UI is backed by a small read-only HTTP API:

- `GET /api/status`: current scan state, last error, and cached summary
- `GET /api/rescan`: re-scan the selected game root and return a new summary
- `GET /api/summary`: catalog summary including counts, stats, and warnings
- `GET /api/music`: paginated music results
- `GET /api/characters`: paginated character results
- `GET /api/nameplates`: paginated name plate results
- `GET /api/jacket?source=<game-relative-path>`: converts and serves a jacket image as PNG
- `GET /api/character-image?source=<game-relative-path>`: serves the full character image as PNG
- `GET /api/character-image?source=<game-relative-path>&variant=thumb`: serves a thumbnail PNG for character grid previews

Category endpoints support these query parameters:

- `q`: case-insensitive text search across the serialized item
- `pack`: exact pack filter
- `enabled=true|false`: enabled-state filter
- `limit`: result page size, capped at `1000`
- `offset`: zero-based result offset

Response notes:

- `GET /api/music`, `GET /api/characters`, and `GET /api/nameplates` return `{ "items": [...], "total": <filtered-count> }`.
- Character items include both `imageUrl` for the full modal image and `imageThumbUrl` for grid previews when a valid image can be resolved.
- `GET /api/summary` and `GET /api/rescan` return the catalog summary shape from `Catalog.as_summary()`.
- `GET /api/status` returns scan lifecycle fields plus the cached summary when one exists.
- `GET /api/jacket` and `GET /api/character-image` return `404` for missing or invalid sources and `501` when `py_dds` is not installed.

## Project layout

- `server.py`: HTTP server, route dispatch, and startup flow
- `selection.py`: command-line path handling and optional folder picker
- `scanner.py`: XML parsing, catalog scanning, dedupe logic, filtering, and jacket path lookup
- `image_utils.py`: DDS decoding bridge and raw PNG encoder
- `store.py`: in-memory catalog state, scan lifecycle, and jacket cache
- `models.py`: shared catalog dataclass and summary projection
- `config.py`: shared constants for roots, caps, and scan target names
- `static/index.html`: UI shell
- `static/app.js`: browser-side fetch, tabs, search, and rendering
- `static/styles.css`: layout and visual styling

## Development notes

- The server uses `ThreadingHTTPServer` and keeps state in a process-local `CatalogStore`.
- Jacket conversion happens lazily per request and is cached by source path.
- Character previews and full character images are cached separately so the grid can stay light while the modal still uses the original resolution.
- A successful rescan replaces the cached catalog and clears the jacket, character thumbnail, and full character image caches.
- Paths used for jacket lookup are validated to stay under the selected game root.
- The project currently has no automated test suite in the repository.

## Local validation

```bash
python3 -m py_compile server.py scanner.py selection.py store.py image_utils.py models.py config.py
```

## Limitations

- The app is read-only and intentionally does not expose write operations.
- Some malformed XML files can only be partially recovered.
- Proprietary audio and chart formats such as `.acb`, `.awb`, and `.c2s` are cataloged as paths and metadata only.
- The in-memory cache is reset when the process restarts.
