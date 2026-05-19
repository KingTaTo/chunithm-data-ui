# Hide Broken Character Thumbnails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep character cards visible while replacing broken thumbnail UI with the existing placeholder whenever a thumbnail request fails.

**Architecture:** Leave scan-time image discovery unchanged. Handle failed thumbnail responses in `static/app.js` by swapping failed image/button markup for the existing placeholder block, and document the behavior in `README.md`.

**Tech Stack:** Dependency-free browser JavaScript, existing static HTML/CSS shell, existing read-only image endpoints.

---

### Task 1: Add browser fallback for failed character thumbnails

**Files:**
- Modify: `static/app.js`
- Create: `static/character_thumbs.js`
- Create: `tests/test_character_thumbs.js`

- [x] Reuse a single placeholder renderer for character cards.
- [x] Detect thumbnail load failures in the character grid.
- [x] Replace failed thumbnail buttons with the non-clickable placeholder.
- [x] Keep successful thumbnails and modal behavior unchanged.

### Task 2: Update ticket tracking and documentation

**Files:**
- Modify: `docs/superpowers/index.md`
- Create: `docs/superpowers/specs/2026-05-19-hide-broken-character-thumbnails.md`
- Create: `docs/superpowers/plans/2026-05-19-hide-broken-character-thumbnails.md`
- Modify: `README.md`

- [x] Record the new ticket in the docs index.
- [x] Document the thumbnail fallback behavior in the README.

### Task 3: Run final verification

**Files:**
- Modify: `docs/superpowers/plans/2026-05-19-hide-broken-character-thumbnails.md`

- [x] Run `python3 -m py_compile server.py scanner.py selection.py store.py image_utils.py models.py config.py`.
- [x] Run the existing automated tests.
- [x] Verify the thumbnail-fallback behavior with `node --test tests/test_character_thumbs.js` because no headless browser is available in this environment.
- [x] Mark this plan complete after the verification pass. The only follow-up issue found during verification was a duplicate ticket-index entry from the parallel docs pass, and it was fixed within this ticket.
