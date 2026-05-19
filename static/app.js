const state = {
  category: "music",
  query: "",
  summary: null,
  modalImageUrl: "",
  activeRequestToken: 0,
  lastFocusedElement: null,
};

// Column definitions stay paired with the backend category names.
const columns = {
  music: ["Jacket", "ID", "Title", "Artist", "Category", "Charts"],
  nameplates: ["ID", "Name", "Image"],
};

const el = (id) => document.getElementById(id);
const currentColumns = () => columns[state.category] || [];

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
  const suffix = shown < total ? `, showing first ${shown}` : "";
  el("results-count").textContent = `${total.toLocaleString()} ${noun}${suffix}`;
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
  const thumb = item.imageUrl ? `
    <button class="character-thumb-button" type="button" data-image-url="${escapeHtml(item.imageUrl)}" data-image-name="${escapeHtml(name)}">
      <img class="character-thumb" src="${escapeHtml(item.imageUrl)}" alt="${escapeHtml(name)}" loading="lazy">
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

function closeImageModal() {
  if (!state.modalImageUrl) return;
  state.modalImageUrl = "";
  el("image-modal").classList.add("hidden");
  el("image-modal").setAttribute("aria-hidden", "true");
  el("image-modal-image").src = "";
  el("image-modal-image").alt = "";
  document.body.classList.remove("modal-open");
  if (state.lastFocusedElement && document.contains(state.lastFocusedElement)) {
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
    renderGridMessage("Loading...");
  } else {
    renderHead();
    renderTableMessage("Loading...");
  }

  const params = new URLSearchParams({ limit: "400" });
  if (requestQuery) params.set("q", requestQuery);

  const data = await fetchJson(`/api/${requestCategory}?${params.toString()}`);
  if (requestToken !== state.activeRequestToken || requestCategory !== state.category || requestQuery !== state.query) {
    return;
  }
  renderResultCount(data.total, data.items.length);

  if (requestCategory === "characters") {
    renderCharacterGrid(data.items);
    return;
  }
  renderRows(data.items);
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
    if (state.category !== "characters") closeImageModal();
    await loadCategory();
  });
});

el("search").addEventListener("input", () => {
  state.query = el("search").value.trim();
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(loadCategory, 180);
});

el("rescan").addEventListener("click", async () => {
  el("rescan").disabled = true;
  el("rescan").textContent = "Scanning...";
  try {
    const summary = await fetchJson("/api/rescan");
    renderStats(summary);
    await loadCategory();
  } finally {
    el("rescan").disabled = false;
    el("rescan").textContent = "Rescan";
  }
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
