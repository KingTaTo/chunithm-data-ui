# Paginated Category Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Page all category views in the browser UI so each tab renders a bounded slice and users can move between result pages.

**Architecture:** Reuse the backend `limit` and `offset` contract. Keep the server unchanged, add a shared pagination control shell in `static/index.html`, store page state in `static/app.js`, and style the controls in `static/styles.css`.

**Tech Stack:** Dependency-free browser JavaScript, static HTML, static CSS, existing read-only JSON API.

---

### Task 1: Add pagination controls and state

**Files:**
- Modify: `static/index.html`
- Modify: `static/app.js`
- Modify: `static/styles.css`

- [ ] Add previous/next buttons and a page status element to the page shell.
- [ ] Add per-tab page state and a shared page-size constant in `app.js`.
- [ ] Fetch every category with `limit` and `offset`.
- [ ] Preserve each tab's page when switching categories.
- [ ] Reset pagination when updating search or rescanning.
- [ ] Disable navigation buttons at the start and end of the result set.

### Task 2: Update documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/index.md`
- Create: `docs/superpowers/specs/2026-05-19-paginated-category-results.md`
- Create: `docs/superpowers/plans/2026-05-19-paginated-category-results.md`

- [ ] Document that all tabs page results through the existing API.
- [ ] Record the new ticket in the docs index.
