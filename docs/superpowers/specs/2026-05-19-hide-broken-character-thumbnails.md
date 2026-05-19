# Hide Broken Character Thumbnails

## Goal

Prevent the `characters` grid from showing broken thumbnail images when a character thumbnail URL exists in scan output but the browser request does not produce a usable image.

## Scope

This change covers:

- Character-grid behavior when a thumbnail request fails in the browser
- Replacing failed thumbnail UI with the existing non-clickable placeholder treatment
- README updates for the degraded thumbnail behavior

This change does not cover:

- Changing jacket rendering behavior
- Retrying failed image requests
- Broadening character image discovery rules beyond the existing scanner logic
- Adding a new client-side test framework

## Current State

- `parse_character()` already omits `imageThumbUrl` when no validated image path can be resolved during scanning.
- Some real-world character entries can still reach the browser with a thumbnail URL that later fails to render, producing a broken image element in the grid.
- The current UI only shows the `No image` placeholder when `imageUrl` or `imageThumbUrl` is empty before rendering.

## Recommended Approach

Keep the scanner and backend endpoint contract unchanged for this ticket, and make the grid resilient to image-request failure:

1. Continue rendering the existing button-and-image markup when a thumbnail URL is present.
2. Listen for thumbnail image load errors in the `characters` grid.
3. Replace the failed thumbnail button with the existing placeholder block so the card remains visible but no broken image is shown.
4. Leave cards without a working image non-clickable.

This keeps the fix narrow:

- `scanner.py` stays responsible for conservative path discovery.
- `server.py` and `store.py` keep the existing image endpoint behavior.
- `static/app.js` owns the browser-only fallback for failed thumbnail requests.

## Validation

- Confirm characters with no `imageThumbUrl` still render the placeholder immediately.
- Confirm a thumbnail request that fails in the browser is replaced with the placeholder instead of leaving a broken image icon.
- Confirm successful thumbnails remain clickable and still open the modal.
- Confirm music jackets and name plates are unchanged.
