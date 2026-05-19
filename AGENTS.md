# AGENTS.md

Guidance for agents working in this repository.

## Repository purpose

`chunithm-data-ui` is a small read-only Python web app for browsing CHUNITHM metadata from a local game install folder. The important behavior is catalog scanning, safe path handling, and a minimal browser UI backed by JSON endpoints.

## Main execution flow

1. `server.py` parses CLI flags and resolves the game root with `choose_game_root()`.
2. `CatalogStore` performs the initial scan and caches the resulting `Catalog`.
3. `Handler` serves the static UI plus `/api/*` endpoints.
4. `scanner.py` owns XML parsing, dedupe logic, filtering, and jacket path resolution.
5. `image_utils.py` converts jacket `.dds` files to PNG bytes when requested.

## Safety boundaries

- Keep the app read-only with respect to the selected game folder.
- Preserve path-safety checks around `safe_game_path()` and static file serving.
- Do not broaden file access beyond the selected root without an explicit request.
- Avoid introducing assumptions about undocumented CHUNITHM file formats unless the repository already proves them.

## High-value files

- `server.py`: request routing and response semantics
- `scanner.py`: metadata extraction, result filtering, and path validation
- `store.py`: scan lifecycle and in-memory cache behavior
- `static/app.js`: UI interactions and category rendering
- `README.md`: user-facing run and API documentation

## Local validation

- Install dependencies: `python -m pip install -r requirements.txt` or `python3 -m pip install -r requirements.txt`
- Syntax check: `python3 -m py_compile server.py scanner.py selection.py store.py image_utils.py models.py config.py`
- Manual smoke test: run `python server.py --game-root "<path>"` or `python3 server.py --game-root "<path>"` and verify `http://127.0.0.1:8765`

## Documentation expectations

- Update `README.md` when changing CLI flags, endpoints, scan behavior, or requirements.
- Keep backend-only query parameters and response-shape notes aligned with `scanner.py`, `models.py`, and `server.py`.
- Document cache invalidation behavior when changing `CatalogStore.scan()` or jacket rendering.
- Prefer small, accurate doc updates over broad template expansion.
- Keep documentation tied to observed behavior in the codebase.
