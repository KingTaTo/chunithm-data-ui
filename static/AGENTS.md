# AGENTS.md

Guidance for agents working in the `static/` subtree.

## Subtree purpose

This directory contains the entire browser UI for `chunithm-data-ui`. It is a small no-build frontend served directly by `server.py` from `/static/*`.

## Files and responsibilities

- `index.html`: page shell, top-level layout, and stable element IDs used by `app.js`
- `app.js`: client-side state, fetch calls, tab switching, search, rescan flow, and table rendering
- `styles.css`: visual theme, layout, responsive behavior, and table/jacket/chart styling

## Working rules

- Keep the frontend dependency-free. Do not introduce bundlers, frameworks, or a build step unless explicitly requested.
- Preserve the existing API contract with `server.py` and `scanner.py`. Category names and field names must stay aligned with backend responses.
- Treat `music`, `characters`, and `nameplates` as stable category keys unless the backend changes first.
- Keep DOM rendering escaped. New user-visible values should go through `escapeHtml()` unless they are trusted static markup.
- Preserve the current direct-file serving model: assets here should remain safe to serve from `/static/`.

## Backend coupling points

- `app.js` expects `GET /api/summary` to return `gameRoot`, `counts`, and `stats.totalFiles`.
- Category fetches expect `{ items, total }` from `/api/music`, `/api/characters`, and `/api/nameplates`.
- Music rows depend on `jacketUrl`, `name` or `dataName`, `artist`, `genre`, and `charts`.
- The rescan button assumes `GET /api/rescan` returns the same summary shape as `/api/summary`.

## UI invariants

- The tabs, search box, result count, and rescan button should continue working without a page reload.
- `index.html` IDs such as `game-root`, `stats`, `table-head`, `table-body`, `search`, `results-count`, and `rescan` are code-coupled to `app.js`.
- CSS class names such as `tab`, `active`, `stat`, `jacket`, `jacket-placeholder`, and `badge` are behaviorally important to the current UI.
- The table must remain usable on narrow screens; keep the mobile rules in `styles.css` intact when changing layout.

## Validation

- After frontend changes, load the app in a browser and verify all three tabs, search, and rescan behavior.
- If you change rendered fields or category names, update `README.md` and the root `AGENTS.md` to match.
