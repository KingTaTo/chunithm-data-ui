# Character Grid Design

## Goal

Update the `characters` tab so it presents character entries as image-first cards instead of table rows. Each card should show a thumbnail and open a full-resolution image in an in-page modal when clicked.

## Scope

This change covers:

- Character image discovery and URL generation in scan output
- A read-only backend endpoint for serving character images as PNG
- Character image caching in memory alongside the existing jacket cache
- A character-only grid renderer in the browser UI
- An in-page modal for full-resolution character art
- README updates for the new endpoint and characters-tab behavior

This change does not cover:

- Name plate thumbnails
- Generic asset serving for arbitrary game files
- Changes to music or name plate layouts

## Current State

- `scanner.py` returns character metadata including `imageKey`, but not a browser-ready image URL.
- `store.py` converts jacket DDS files to PNG and caches them by source path.
- `server.py` exposes `/api/jacket` as the only image endpoint.
- `static/app.js` renders all categories into the same table shell.
- `static/index.html` only contains table-based result markup.

## Recommended Approach

Implement a character-specific image flow that mirrors the existing jacket flow where practical:

1. Extend character scan output with `image` and `imageUrl` fields.
2. Resolve the character image path from the character metadata file and validate it stays under the selected game root.
3. Add a store method and HTTP endpoint that convert the character image to PNG and cache it in memory.
4. Keep the existing result loading and filtering flow, but render the `characters` tab into a responsive card grid instead of the shared table.
5. Add a modal overlay that displays the full-resolution character image without leaving the page.

This keeps the change narrow and consistent with the current architecture:

- `scanner.py` remains responsible for metadata extraction and safe file resolution inputs.
- `store.py` remains responsible for image conversion and caching.
- `server.py` remains responsible for read-only endpoint dispatch.
- `static/app.js` remains responsible for category-specific presentation.

## Backend Design

### Scanner Changes

`parse_character()` should include:

- `image`: the raw image-relative path from XML if present
- `imageUrl`: `/api/character-image?source=<game-relative-path>` when an image path exists, otherwise `""`

Add a `find_character_image_path(catalog, source)` helper parallel to `find_jacket_path()`:

- Find the character item by `source`
- Return `None` when the item has no `image`
- Resolve the metadata XML file with `safe_game_path()`
- Resolve the referenced image relative to the metadata file’s parent directory
- Reject paths that escape the selected game root
- Return `None` when the file does not exist

The helper should assume only repository-proven behavior: image paths are used as stored in the metadata and resolved relative to the source XML location.

### Store Changes

Extend `CatalogStore` with a second in-memory image cache keyed by character `source`.

Add `character_image_png(source: str) -> bytes`:

- Reuse the active catalog or trigger a scan if needed
- Resolve the validated character image path
- Raise `FileNotFoundError` when no valid image exists
- Convert the DDS file to PNG with the same conversion utility used for jackets
- Cache the PNG bytes by `source`

Rescans should clear both the jacket cache and the character-image cache.

### Server Changes

Add a new `GET /api/character-image?source=<game-relative-path>` route.

Behavior should match `/api/jacket`:

- `400` when `source` is missing
- `404` for missing or invalid character image paths
- `501` when DDS decoding support is unavailable
- `200 image/png` with cache headers on success

No other API response shapes should change.

## Frontend Design

### Rendering Model

Keep music and name plates on the existing table layout. Only the `characters` tab should switch to a card view.

The content area should support two mutually exclusive result containers:

- Table view for `music` and `nameplates`
- Grid view for `characters`

`loadCategory()` should keep the same fetch flow and search behavior, but branch rendering by category:

- `music` and `nameplates`: render the existing table
- `characters`: hide the table shell and render cards into a dedicated grid container

### Character Cards

Each card should render:

- Thumbnail image when `imageUrl` exists
- A placeholder block when no image is available
- Character name
- Character ID
- Works
- Image key

The thumbnail should use lazy loading.

### Modal

Clicking a thumbnail opens an in-page modal overlay that shows the full-resolution image from the same `imageUrl`.

Modal behavior:

- Open on thumbnail click
- Close on backdrop click
- Close on close button click
- Close on `Escape`
- Preserve current search text and scroll position in the underlying page

The modal only needs image viewing support. It does not need carousel behavior, zoom controls, or keyboard navigation between characters.

## Styling

Add styles for:

- Responsive character grid using `repeat(auto-fill, minmax(...))`
- Card surfaces aligned with the existing dark UI
- Thumbnail sizing and placeholders
- Modal backdrop, panel, close button, and constrained full-resolution image sizing

The grid should remain usable on narrow mobile widths and should not affect music or name plate layout.

## Error Handling

- Missing character image metadata: render the card without a clickable image and show the existing text fields
- Broken image endpoint response: keep the card visible and let the browser image fail naturally
- Missing full-resolution image after click: modal should still open only when an image URL exists

No new client-side retry behavior is required.

## Testing And Validation

Follow TDD for the backend changes.

Add targeted tests for:

- `parse_character()` including `image` and `imageUrl`
- `find_character_image_path()` valid path resolution
- `find_character_image_path()` rejection of missing or escaping paths
- `CatalogStore.scan()` clearing both image caches
- Character image endpoint success and error behavior

Run:

- `python3 -m py_compile server.py scanner.py selection.py store.py image_utils.py models.py config.py`
- The relevant automated tests added for this feature

Manual smoke test:

1. Run `python3 server.py --game-root "<path>"`
2. Open the browser UI
3. Switch to `Characters`
4. Confirm cards render thumbnails
5. Click a thumbnail and confirm the full image opens in-page
6. Confirm modal close interactions work

## Documentation Changes

Update `README.md` to document:

- Character tab grid behavior
- `GET /api/character-image?source=<game-relative-path>`
- Character image cache clearing on rescan

## Risks And Tradeoffs

- This adds a second image cache, but keeps cache semantics explicit and localized.
- The UI gains category-specific layout branching, but only for one tab and without changing the fetch contract.
- The design assumes character images can be resolved relative to their metadata XML path; if some game assets use a different convention, those entries will degrade safely to a placeholder instead of broadening file access rules.
