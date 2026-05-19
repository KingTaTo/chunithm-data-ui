const state = {
  category: "music",
  query: "",
  summary: null,
  pageByCategory: {
    music: 0,
    characters: 0,
    nameplates: 0,
  },
  modalImageUrl: "",
  activeRequestToken: 0,
  lastFocusedElement: null,
};

const PAGE_SIZE = 100;

// Column definitions stay paired with the backend category names.
const columns = {
  music: ["Jacket", "ID", "Title", "Artist", "Category", "Charts"],
  nameplates: ["ID", "Name", "Image"],
};

const el = (id) => document.getElementById(id);
const currentColumns = () => columns[state.category] || [];
const currentPage = () => state.pageByCategory[state.category] || 0;
const setCurrentPage = (page) => {
  state.pageByCategory[state.category] = Math.max(0, page);
};

function categoryLabel() {
  return document.querySelector(`.tab[data-category="${state.category}"]`)?.textContent || state.category;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;",
  }[char]));
}

function versionedImageUrl(url) {
  if (!url) return "";
  const version = state.summary?.generatedAt;
  if (!version) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}v=${encodeURIComponent(version)}`;
}

function chartClass(type) {
  return `level-${String(type || "").toLowerCase().replace(/[^a-z]/g, "")}`;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function renderStats(summary) {
  state.summary = summary;
  el("game-root").textContent = summary.gameRoot;

  const stats = [
    [summary.counts.music, "Music entries"],
    [summary.counts.characters, "Characters"],
    [summary.counts.nameplates, "Name plates"],
    [summary.stats.totalFiles, "Total files"],
  ];
  el("stats").innerHTML = stats.map(([value, label]) => `
    <article class="stat"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></article>
  `).join("");
}

function renderHead() {
  el("table-head").innerHTML = `<tr>${currentColumns().map((name) => `<th>${name}</th>`).join("")}</tr>`;
}

function setCategoryView(category) {
  const showCharacters = category === "characters";
  el("table-shell").classList.toggle("hidden", showCharacters);
  el("character-grid").classList.toggle("hidden", !showCharacters);
}

// Render only the current page of API results to keep large catalogs responsive.
function renderResultCount(total, shown) {
  const label = categoryLabel().toLowerCase();
  const noun = total === 1 ? label.replace(/s$/, "") : label;
  const offset = currentPage() * PAGE_SIZE;
  const start = total === 0 ? 0 : offset + 1;
  const end = total === 0 ? 0 : Math.min(offset + shown, total);
  el("results-count").textContent = `${total.toLocaleString()} ${noun}, showing ${start.toLocaleString()}-${end.toLocaleString()}`;
}

function renderPagination(total) {
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const activePage = Math.min(currentPage() + 1, pageCount);
  el("page-status").textContent = `Page ${activePage} of ${pageCount}`;
  el("page-prev").disabled = currentPage() <= 0;
  el("page-next").disabled = activePage >= pageCount;
}

function renderLoadingState() {
  el("page-status").textContent = "Loading page...";
  el("page-prev").disabled = true;
  el("page-next").disabled = true;
}

function renderTableMessage(message) {
  el("table-body").innerHTML = `<tr><td colspan="${currentColumns().length}" class="muted">${escapeHtml(message)}</td></tr>`;
}

function renderGridMessage(message) {
  el("character-grid").innerHTML = `<div class="grid-message muted">${escapeHtml(message)}</div>`;
}

function renderRows(items) {
  if (!items.length) {
    renderTableMessage("No matching entries.");
    return;
  }
  el("table-body").innerHTML = items.map((item) => renderRow(item)).join("");
}

function renderJacket(item) {
  if (!item.jacketUrl) {
    return `<div class="jacket-placeholder">No jacket</div>`;
  }
  return `<img class="jacket" src="${escapeHtml(item.jacketUrl)}" alt="${escapeHtml(item.name || item.dataName)} jacket" loading="lazy">`;
}

function renderMusicRow(item) {
  const charts = (item.charts || []).map((chart) => `
    <span class="badge ${chartClass(chart.type)}">${escapeHtml(chart.type)} ${escapeHtml(chart.level)}</span>
  `).join("");

  return `<tr>
    <td>${renderJacket(item)}</td>
    <td>${escapeHtml(item.id)}</td>
    <td><strong>${escapeHtml(item.name || item.dataName)}</strong></td>
    <td>${escapeHtml(item.artist)}</td>
    <td>${escapeHtml(item.genre)}</td>
    <td>${charts || "<small>None</small>"}</td>
  </tr>`;
}

function renderNameplateRow(item) {
  return `<tr>
    <td>${escapeHtml(item.id)}</td>
    <td><strong>${escapeHtml(item.name || item.dataName)}</strong></td>
    <td>${escapeHtml(item.image)}</td>
  </tr>`;
}

function renderRow(item) {
  if (state.category === "music") return renderMusicRow(item);
  if (state.category === "nameplates") return renderNameplateRow(item);
  return "";
}

function modalFocusableElements() {
  return Array.from(el("image-modal").querySelectorAll(
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )).filter((node) => !node.closest(".hidden"));
}

function renderCharacterCard(item) {
  const name = item.name || item.dataName || "Unknown character";
  const imageUrl = versionedImageUrl(item.imageUrl);
  const imageThumbUrl = versionedImageUrl(item.imageThumbUrl);
  const thumb = item.imageUrl && item.imageThumbUrl ? `
    <button class="character-thumb-button" type="button" data-image-url="${escapeHtml(imageUrl)}" data-image-name="${escapeHtml(name)}">
      <img class="character-thumb" src="${escapeHtml(imageThumbUrl)}" alt="${escapeHtml(name)}" loading="lazy">
    </button>
  ` : `
    <div class="character-thumb-placeholder">No image</div>
  `;

  return `<article class="character-card">
    <div class="character-thumb-wrap">${thumb}</div>
    <div class="character-card-body">
      <h2>${escapeHtml(name)}</h2>
      <dl class="character-meta">
        <div><dt>ID</dt><dd>${escapeHtml(item.id)}</dd></div>
        <div><dt>Works</dt><dd>${escapeHtml(item.works || "Unknown")}</dd></div>
        <div><dt>Image Key</dt><dd>${escapeHtml(item.imageKey || "None")}</dd></div>
      </dl>
    </div>
  </article>`;
}

function renderCharacterGrid(items) {
  if (!items.length) {
    renderGridMessage("No matching entries.");
    return;
  }
  el("character-grid").innerHTML = items.map((item) => renderCharacterCard(item)).join("");
}

function openImageModal(imageUrl, imageName) {
  if (!imageUrl) return;
  state.lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  state.modalImageUrl = imageUrl;
  el("image-modal-image").src = imageUrl;
  el("image-modal-image").alt = imageName;
  el("image-modal-title").textContent = imageName;
  el("image-modal").classList.remove("hidden");
  el("image-modal").setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  const focusTarget = modalFocusableElements()[0] || el("image-modal-close");
  focusTarget.focus();
}

function closeImageModal(options = {}) {
  if (!state.modalImageUrl) return;
  const { restoreFocus = true } = options;
  state.modalImageUrl = "";
  el("image-modal").classList.add("hidden");
  el("image-modal").setAttribute("aria-hidden", "true");
  el("image-modal-image").src = "";
  el("image-modal-image").alt = "";
  document.body.classList.remove("modal-open");
  if (restoreFocus && state.lastFocusedElement && document.contains(state.lastFocusedElement)) {
    state.lastFocusedElement.focus();
  }
  state.lastFocusedElement = null;
}

let searchTimer = null;

// Each tab asks the backend for its category, preserving the active search text.
async function loadCategory() {
  const requestCategory = state.category;
  const requestQuery = state.query;
  const requestToken = state.activeRequestToken + 1;
  state.activeRequestToken = requestToken;

  setCategoryView(requestCategory);

  if (requestCategory === "characters") {
    closeImageModal({ restoreFocus: false });
    renderGridMessage("Loading...");
  } else {
    renderHead();
    renderTableMessage("Loading...");
  }

  renderLoadingState();

  const params = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String(currentPage() * PAGE_SIZE),
  });
  if (requestQuery) params.set("q", requestQuery);

  try {
    const data = await fetchJson(`/api/${requestCategory}?${params.toString()}`);
    if (requestToken !== state.activeRequestToken || requestCategory !== state.category || requestQuery !== state.query) {
      return;
    }
    renderResultCount(data.total, data.items.length);
    renderPagination(data.total);

    if (requestCategory === "characters") {
      renderCharacterGrid(data.items);
      return;
    }
    renderRows(data.items);
  } catch (error) {
    if (requestToken !== state.activeRequestToken || requestCategory !== state.category || requestQuery !== state.query) {
      return;
    }
    const message = error instanceof Error ? error.message : String(error);
    el("results-count").textContent = "Unable to load results";
    el("page-status").textContent = "Pagination unavailable";
    el("page-prev").disabled = true;
    el("page-next").disabled = true;
    if (requestCategory === "characters") {
      renderGridMessage(message);
      return;
    }
    renderTableMessage(message);
  }
}

async function boot() {
  const summary = await fetchJson("/api/summary");
  renderStats(summary);
  await loadCategory();
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", async () => {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    button.classList.add("active");
    state.category = button.dataset.category;
    if (state.category !== "characters") closeImageModal({ restoreFocus: false });
    await loadCategory();
  });
});

el("search").addEventListener("input", () => {
  state.query = el("search").value.trim();
  Object.keys(state.pageByCategory).forEach((category) => {
    state.pageByCategory[category] = 0;
  });
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(loadCategory, 180);
});

el("rescan").addEventListener("click", async () => {
  el("rescan").disabled = true;
  el("rescan").textContent = "Scanning...";
  try {
    const summary = await fetchJson("/api/rescan");
    renderStats(summary);
    Object.keys(state.pageByCategory).forEach((category) => {
      state.pageByCategory[category] = 0;
    });
    await loadCategory();
  } finally {
    el("rescan").disabled = false;
    el("rescan").textContent = "Rescan";
  }
});

el("page-prev").addEventListener("click", async () => {
  if (currentPage() <= 0) return;
  setCurrentPage(currentPage() - 1);
  await loadCategory();
});

el("page-next").addEventListener("click", async () => {
  setCurrentPage(currentPage() + 1);
  await loadCategory();
});

el("character-grid").addEventListener("click", (event) => {
  const button = event.target.closest(".character-thumb-button");
  if (!button) return;
  openImageModal(button.dataset.imageUrl || "", button.dataset.imageName || "Character image preview");
});

el("image-modal-close").addEventListener("click", closeImageModal);
el("image-modal-backdrop").addEventListener("click", closeImageModal);

document.addEventListener("keydown", (event) => {
  if (!state.modalImageUrl) return;
  if (event.key === "Escape") {
    closeImageModal();
    return;
  }
  if (event.key !== "Tab") return;

  const focusables = modalFocusableElements();
  if (!focusables.length) {
    event.preventDefault();
    el("image-modal-close").focus();
    return;
  }

  const first = focusables[0];
  const last = focusables[focusables.length - 1];

  if (!el("image-modal").contains(document.activeElement)) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
    return;
  }

  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
    return;
  }
  if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
});

boot().catch((error) => {
  el("game-root").textContent = error.message;
  setCategoryView(state.category);
  if (state.category === "characters") {
    renderGridMessage(error.message);
    return;
  }
  renderTableMessage(error.message);
});
