# Paginated Category Results

## Goal

Update the browser UI so `music`, `characters`, and `nameplates` all render paginated result pages instead of loading a large first slice into a single screen.

## Scope

This change covers:

- Client-side page state for all three categories
- UI controls for navigating result pages
- Use of the existing backend `limit` and `offset` query parameters
- README updates for the paginated browsing behavior

This change does not cover:

- Infinite scroll
- Server-side changes to filtering semantics
- Deep-linking the current page into the URL

## Current State

- The backend already supports `limit` and `offset` for category endpoints.
- The current UI requests one large page and renders it directly.
- Character cards and table rows both use the same `loadCategory()` fetch flow.

## Recommended Approach

Keep pagination entirely in the existing browser flow:

1. Add a single shared page size constant and current-page state.
2. Add previous/next controls plus a page status line below the result container.
3. Preserve the current page per tab when switching categories.
4. Reset back to page 1 when the search query changes or a rescan completes.
5. Reuse the existing `total` count from the backend to disable navigation at the ends.

This keeps the architecture coherent:

- `server.py` stays unchanged because the API already supports paging.
- `static/index.html` owns the pagination shell.
- `static/app.js` owns the page state, result fetches, and navigation behavior.
- `static/styles.css` owns pagination layout and responsive behavior.

## Validation

- Load each tab and confirm page navigation changes the rendered slice.
- Confirm returning to a tab restores the page that tab was last showing.
- Confirm search resets back to the first page.
- Confirm rescan resets back to the first page.
- Confirm the current page and range text remain accurate for empty, partial, and full pages.
