# AZEN Character Image Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve character images for `AZEN` pack entries from `data/a000` when the normal pack-local `ddsImage` manifest path is missing.

**Architecture:** Keep character image discovery centralized in `scanner.py`. Preserve the current manifest-first lookup, add an `AZEN`-specific fallback into `data/a000`, and verify the resolved path still flows through the existing safe-path and image-serving code unchanged.

**Tech Stack:** Python 3, `xml.etree.ElementTree`, existing scanner/store pipeline, existing unittest coverage.

---

### Task 1: Cover AZEN fallback behavior with scanner tests

**Files:**
- Modify: `tests/test_scanner.py`

- [x] Add a test fixture for an `AZEN` character whose pack-local `ddsImage/.../DDSImage.xml` path is absent but whose image asset exists under `data/a000`.
- [x] Assert that the scan output populates `imageUrl` and `imageThumbUrl` for that character from the fallback path.
- [x] Add a test that a non-`AZEN` character with the same missing pack-local manifest does not resolve through `data/a000`.
- [x] Add a test that an `AZEN` character still prefers a valid pack-local manifest when both locations exist.

### Task 2: Implement the AZEN-only manifest fallback

**Files:**
- Modify: `scanner.py`

- [x] Keep the existing pack-local manifest lookup as the first attempt.
- [x] Detect when the character source belongs to the `AZEN` pack and the pack-local manifest path is missing.
- [x] Add a fallback lookup that searches the equivalent manifest/image path under `data/a000`.
- [x] Reuse the current safe path validation and unresolved-character behavior when the fallback does not produce a valid file.

### Task 3: Document and verify the ticket

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/index.md`
- Create: `docs/superpowers/specs/2026-05-19-azen-character-image-fallback.md`
- Create: `docs/superpowers/plans/2026-05-19-azen-character-image-fallback.md`

- [x] Update `README.md` to note that `AZEN` character image discovery now falls back to `data/a000` when pack-local manifests are absent.
- [x] Record the new ticket in the docs index.
- [x] Run `python3 -m py_compile server.py scanner.py selection.py store.py image_utils.py models.py config.py`.
- [x] Run the scanner-focused automated tests and any broader test suite already used by the repo.
- [x] Perform a final verification pass confirming no additional follow-up tickets are required for this narrow fallback.
