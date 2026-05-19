# Character Grid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add character thumbnails to the `characters` tab, render that tab as a card grid, and open the full image in an in-page modal.

**Architecture:** Keep the existing read-only category API contract and add one new character-specific PNG endpoint parallel to `/api/jacket`. Resolve character art paths in `scanner.py`, convert and cache the original PNG bytes in `store.py`, and branch the frontend so only `characters` uses the new grid and modal UI while `music` and `nameplates` stay table-based.

**Tech Stack:** Python 3 standard library, `py_dds`, dependency-free browser JavaScript, static CSS.

---

### Task 1: Add scanner coverage for character images

**Files:**
- Create: `tests/test_scanner.py`
- Modify: `scanner.py`

- [ ] **Step 1: Write the failing scanner tests**

```python
from pathlib import Path

from models import Catalog
from scanner import find_character_image_path, parse_character


def test_parse_character_includes_image_fields(tmp_path):
    xml_path = tmp_path / "data" / "character" / "hero.xml"
    xml_path.parent.mkdir(parents=True)
    xml_path.write_text(
        """<CharacterData>
  <dataName>CHARA_HERO</dataName>
  <name><id>42</id><str>Hero</str></name>
  <works><str>Original</str></works>
  <defaultImages><str>hero_default</str></defaultImages>
  <image><path>ui/hero.dds</path></image>
</CharacterData>""",
        encoding="utf-8",
    )

    item = parse_character(xml_path, tmp_path)

    assert item["image"] == "ui/hero.dds"
    assert item["imageUrl"] == "/api/character-image?source=data/character/hero.xml"


def test_find_character_image_path_resolves_relative_image(tmp_path):
    xml_path = tmp_path / "data" / "character" / "hero.xml"
    image_path = tmp_path / "data" / "character" / "ui" / "hero.dds"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"DDS ")
    xml_path.write_text("<CharacterData/>", encoding="utf-8")

    catalog = Catalog(
        game_root=tmp_path,
        generated_at=0.0,
        characters=[{"source": "data/character/hero.xml", "image": "ui/hero.dds"}],
    )

    assert find_character_image_path(catalog, "data/character/hero.xml") == image_path.resolve()


def test_find_character_image_path_rejects_escaped_or_missing_paths(tmp_path):
    xml_path = tmp_path / "data" / "character" / "hero.xml"
    xml_path.parent.mkdir(parents=True)
    xml_path.write_text("<CharacterData/>", encoding="utf-8")

    catalog = Catalog(
        game_root=tmp_path,
        generated_at=0.0,
        characters=[{"source": "data/character/hero.xml", "image": "../outside.dds"}],
    )

    assert find_character_image_path(catalog, "data/character/hero.xml") is None
    assert find_character_image_path(catalog, "data/character/missing.xml") is None
```

- [ ] **Step 2: Run the scanner tests to verify they fail**

Run: `python3 -m unittest -v tests.test_scanner`

Expected: `ImportError` for `tests.test_scanner` before the file exists, then assertion failures because `parse_character()` does not expose `image`/`imageUrl` and `find_character_image_path()` does not exist yet.

- [ ] **Step 3: Write the minimal scanner implementation**

```python
def parse_character(path: Path, root_dir: Path) -> dict[str, Any]:
    root = parse_xml(path)
    source = relpath(path, root_dir)
    image = child_text(root, "image/path") if root is not None else ""
    return {
        "dataName": child_text(root, "dataName") if root is not None else fallback_field(path, "dataName"),
        "id": child_int(root, "name/id") if root is not None else 0,
        "name": child_text(root, "name/str") if root is not None else path.parent.name,
        "works": child_text(root, "works/str") if root is not None else "",
        "imageKey": child_text(root, "defaultImages/str") if root is not None else "",
        "image": image,
        "imageUrl": f"/api/character-image?source={quote(source)}" if image else "",
        "defaultHave": child_bool(root, "defaultHave") if root is not None else False,
        "enabled": not child_bool(root, "disableFlag") if root is not None else True,
        "source": source,
        "pack": pack_name(path, root_dir),
    }


def find_character_image_path(catalog: Catalog, source: str) -> Path | None:
    item = next((entry for entry in catalog.characters if entry.get("source") == source), None)
    if not item or not item.get("image"):
        return None

    source_path = safe_game_path(catalog.game_root, source)
    image_path = (source_path.parent / str(item["image"])).resolve()
    if not is_under_root(image_path, catalog.game_root) or not image_path.is_file():
        return None
    return image_path
```

- [ ] **Step 4: Run the scanner tests to verify they pass**

Run: `python3 -m unittest -v tests.test_scanner`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add scanner.py tests/test_scanner.py
git commit -m "test: cover character image scanner paths"
```

### Task 2: Add cached character image serving on the backend

**Files:**
- Create: `tests/test_store.py`
- Create: `tests/test_server.py`
- Modify: `store.py`
- Modify: `server.py`

- [ ] **Step 1: Write the failing backend tests**

```python
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from models import Catalog
from store import CatalogStore


class CatalogStoreTests(TestCase):
    def test_scan_clears_jacket_and_character_caches(self):
        root = Path("/tmp/game-root")
        store = CatalogStore(root)
        store._jacket_cache["music.xml"] = b"png"
        store._character_image_cache["character.xml"] = b"png"
        catalog = Catalog(game_root=root, generated_at=1.0)

        with patch("store.scan_game_root", return_value=catalog):
            store.scan()

        self.assertEqual(store._jacket_cache, {})
        self.assertEqual(store._character_image_cache, {})


class CharacterImageStoreTests(TestCase):
    @patch("store.find_character_image_path")
    @patch("store.dds_to_png", return_value=b"png-bytes")
    def test_character_image_png_uses_cache(self, convert_mock, find_mock):
        root = Path("/tmp/game-root")
        store = CatalogStore(root)
        store._catalog = Catalog(game_root=root, generated_at=1.0)
        find_mock.return_value = root / "data" / "hero.dds"

        first = store.character_image_png("data/hero.xml")
        second = store.character_image_png("data/hero.xml")

        self.assertEqual(first, b"png-bytes")
        self.assertEqual(second, b"png-bytes")
        convert_mock.assert_called_once()
```

```python
from http import HTTPStatus
from unittest import TestCase
from unittest.mock import Mock

from server import Handler


class CharacterImageRouteTests(TestCase):
    def test_serve_character_image_returns_400_without_source(self):
        handler = Handler.__new__(Handler)
        handler.store = Mock()
        handler.send_error = Mock()

        handler.serve_character_image({})

        handler.send_error.assert_called_once_with(HTTPStatus.BAD_REQUEST, "Missing source parameter")
```

- [ ] **Step 2: Run the backend tests to verify they fail**

Run: `python3 -m unittest -v tests.test_store tests.test_server`

Expected: failures because `_character_image_cache`, `character_image_png()`, and `serve_character_image()` do not exist yet.

- [ ] **Step 3: Write the minimal store and server implementation**

```python
from scanner import find_character_image_path, find_jacket_path, scan_game_root


class CatalogStore:
    def __init__(self, game_root: Path) -> None:
        self.game_root = game_root
        self._lock = threading.Lock()
        self._catalog: Catalog | None = None
        self._jacket_cache: dict[str, bytes] = {}
        self._character_image_cache: dict[str, bytes] = {}
        self._is_scanning = False
        self._last_error: str | None = None

    def scan(self) -> Catalog:
        ...
            with self._lock:
                self._catalog = catalog
                self._jacket_cache.clear()
                self._character_image_cache.clear()
        ...

    def character_image_png(self, source: str) -> bytes:
        with self._lock:
            cached = self._character_image_cache.get(source)
            if cached is not None:
                return cached

        catalog = self.get() or self.scan()
        image_path = find_character_image_path(catalog, source)
        if image_path is None:
            raise FileNotFoundError("No character DDS file was found for this character entry")

        png_data = dds_to_png(image_path)
        with self._lock:
            self._character_image_cache[source] = png_data
        return png_data
```

```python
API_CATEGORIES = {"music", "characters", "nameplates"}


def do_GET(self) -> None:
    ...
    if parsed.path == "/api/character-image":
        self.serve_character_image(query)
        return
    ...


def serve_character_image(self, query: dict[str, list[str]]) -> None:
    source = query.get("source", [""])[0]
    if not source:
        self.send_error(HTTPStatus.BAD_REQUEST, "Missing source parameter")
        return

    try:
        data = self.store.character_image_png(source)
    except RuntimeError as exc:
        self.send_error(HTTPStatus.NOT_IMPLEMENTED, str(exc))
        return
    except (FileNotFoundError, ValueError) as exc:
        self.send_error(HTTPStatus.NOT_FOUND, str(exc))
        return

    self.send_response(HTTPStatus.OK)
    self.send_header("Content-Type", "image/png")
    self.send_header("Cache-Control", "public, max-age=3600")
    self.send_header("Content-Length", str(len(data)))
    self.end_headers()
    self.wfile.write(data)
```

- [ ] **Step 4: Expand the route test to cover success and 404 behavior**

```python
from io import BytesIO


def test_serve_character_image_returns_png_bytes(self):
    handler = Handler.__new__(Handler)
    handler.store = Mock()
    handler.store.character_image_png.return_value = b"png"
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = BytesIO()

    handler.serve_character_image({"source": ["data/hero.xml"]})

    handler.send_response.assert_called_once_with(HTTPStatus.OK)
    self.assertEqual(handler.wfile.getvalue(), b"png")


def test_serve_character_image_returns_404_when_missing(self):
    handler = Handler.__new__(Handler)
    handler.store = Mock()
    handler.store.character_image_png.side_effect = FileNotFoundError("missing")
    handler.send_error = Mock()

    handler.serve_character_image({"source": ["data/hero.xml"]})

    handler.send_error.assert_called_once_with(HTTPStatus.NOT_FOUND, "missing")
```

- [ ] **Step 5: Run the backend tests to verify they pass**

Run: `python3 -m unittest -v tests.test_store tests.test_server`

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add store.py server.py tests/test_store.py tests/test_server.py
git commit -m "feat: serve cached character images"
```

### Task 3: Switch the characters tab to a grid with an in-page modal

**Files:**
- Modify: `static/index.html`
- Modify: `static/app.js`
- Modify: `static/styles.css`

- [ ] **Step 1: Add dedicated containers for table, character grid, and modal shell**

```html
<section class="content">
  <div id="table-view" class="table-wrap">
    <table>
      <thead id="table-head"></thead>
      <tbody id="table-body"></tbody>
    </table>
  </div>
  <div id="character-grid" class="character-grid hidden" aria-live="polite"></div>
</section>

<div id="image-modal" class="image-modal hidden" aria-hidden="true">
  <div class="image-modal__backdrop" data-close-modal="true"></div>
  <div class="image-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="image-modal-title">
    <button id="image-modal-close" class="image-modal__close" type="button" aria-label="Close image viewer">Close</button>
    <h2 id="image-modal-title" class="sr-only">Character Image Viewer</h2>
    <img id="image-modal-image" class="image-modal__image" alt="">
  </div>
</div>
```

- [ ] **Step 2: Update the frontend renderer for character cards and modal behavior**

```javascript
const state = {
  category: "music",
  query: "",
  summary: null,
  modalOpen: false,
};

function renderCharacterCard(item) {
  const name = item.name || item.dataName;
  const image = item.imageUrl
    ? `<button class="character-card__thumb-button" type="button" data-full-image="${escapeHtml(item.imageUrl)}" data-image-name="${escapeHtml(name)}">
         <img class="character-card__thumb" src="${escapeHtml(item.imageUrl)}" alt="${escapeHtml(name)}" loading="lazy">
       </button>`
    : `<div class="character-card__placeholder">No image</div>`;

  return `<article class="character-card">
    ${image}
    <div class="character-card__body">
      <strong>${escapeHtml(name)}</strong>
      <span>ID ${escapeHtml(item.id)}</span>
      <span>${escapeHtml(item.works || "No works text")}</span>
      <small>${escapeHtml(item.imageKey || "No image key")}</small>
    </div>
  </article>`;
}

function renderCharacterGrid(items) {
  const grid = el("character-grid");
  if (!items.length) {
    grid.innerHTML = `<p class="muted grid-message">No matching entries.</p>`;
    return;
  }
  grid.innerHTML = items.map(renderCharacterCard).join("");
}

function setCategoryView() {
  const tableView = el("table-view");
  const grid = el("character-grid");
  const showGrid = state.category === "characters";
  tableView.classList.toggle("hidden", showGrid);
  grid.classList.toggle("hidden", !showGrid);
}

function openImageModal(url, name) {
  el("image-modal-image").src = url;
  el("image-modal-image").alt = name;
  el("image-modal").classList.remove("hidden");
  el("image-modal").setAttribute("aria-hidden", "false");
  state.modalOpen = true;
}

function closeImageModal() {
  el("image-modal").classList.add("hidden");
  el("image-modal").setAttribute("aria-hidden", "true");
  el("image-modal-image").src = "";
  el("image-modal-image").alt = "";
  state.modalOpen = false;
}
```

- [ ] **Step 3: Wire the category load path and delegated click handlers**

```javascript
async function loadCategory() {
  setCategoryView();
  renderHead();
  if (state.category === "characters") {
    el("character-grid").innerHTML = `<p class="muted grid-message">Loading...</p>`;
  } else {
    renderTableMessage("Loading...");
  }

  const params = new URLSearchParams({ limit: "400" });
  if (state.query) params.set("q", state.query);

  const data = await fetchJson(`/api/${state.category}?${params.toString()}`);
  renderResultCount(data.total, data.items.length);

  if (state.category === "characters") {
    renderCharacterGrid(data.items);
    return;
  }
  renderRows(data.items);
}

document.addEventListener("click", (event) => {
  const thumb = event.target.closest("[data-full-image]");
  if (thumb) {
    openImageModal(thumb.dataset.fullImage, thumb.dataset.imageName || "Character image");
    return;
  }
  if (event.target.closest("[data-close-modal='true']") || event.target.id === "image-modal-close") {
    closeImageModal();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.modalOpen) {
    closeImageModal();
  }
});
```

- [ ] **Step 4: Add the grid and modal styles**

```css
.hidden { display: none !important; }

.character-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  padding: 16px;
}

.character-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel);
  overflow: hidden;
}

.character-card__thumb,
.character-card__placeholder {
  width: 100%;
  aspect-ratio: 1 / 1;
  display: block;
  object-fit: cover;
  background: #0b0e10;
}

.image-modal {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  z-index: 20;
}

.image-modal__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(4, 6, 7, 0.82);
}

.image-modal__dialog {
  position: relative;
  max-width: min(92vw, 1100px);
  max-height: 92vh;
  padding: 18px;
  border-radius: 12px;
  background: #12161a;
  border: 1px solid var(--line);
}

.image-modal__image {
  max-width: 100%;
  max-height: calc(92vh - 72px);
  display: block;
}
```

- [ ] **Step 5: Run a syntax check after the frontend changes**

Run: `python3 -m py_compile server.py scanner.py selection.py store.py image_utils.py models.py config.py`

Expected: no output

- [ ] **Step 6: Commit**

```bash
git add static/index.html static/app.js static/styles.css
git commit -m "feat: render character grid with modal viewer"
```

### Task 4: Update docs and run the final verification pass

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README for the new endpoint and UI behavior**

```md
- The characters tab renders image-first cards instead of table rows when character art is available.
- Clicking a character thumbnail opens the full image in an in-page modal.
- `GET /api/character-image?source=<game-relative-path>`: converts and serves a character image as PNG
- A successful rescan replaces the cached catalog and clears both the jacket PNG cache and the character image PNG cache.
```

- [ ] **Step 2: Run the full automated verification**

Run: `python3 -m unittest -v tests.test_scanner tests.test_store tests.test_server`

Expected: `OK`

Run: `python3 -m py_compile server.py scanner.py selection.py store.py image_utils.py models.py config.py`

Expected: no output

- [ ] **Step 3: Run the manual smoke test**

Run: `python3 server.py --game-root "<path-to-game-root>"`

Expected:
- The app starts on `http://127.0.0.1:8765`
- `Characters` shows a card grid
- Clicking a thumbnail opens the in-page modal
- `Escape`, backdrop click, and close button dismiss the modal
- `Music` and `Name Plates` still use the table layout

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: describe character image grid and endpoint"
```
