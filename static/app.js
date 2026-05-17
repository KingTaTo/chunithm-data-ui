const state = {
  category: "music",
  query: "",
  summary: null,
};

// Column definitions stay paired with the backend category names.
const columns = {
  music: ["Jacket", "ID", "Title", "Artist", "Category", "Charts"],
  characters: ["ID", "Name", "Works", "Image Key"],
  nameplates: ["ID", "Name", "Image"],
};

const el = (id) => document.getElementById(id);

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
  el("table-head").innerHTML = `<tr>${columns[state.category].map((name) => `<th>${name}</th>`).join("")}</tr>`;
}

// Render only the current page of API results to keep large catalogs responsive.
function renderResultCount(total, shown) {
  const label = categoryLabel().toLowerCase();
  const noun = total === 1 ? label.replace(/s$/, "") : label;
  const suffix = shown < total ? `, showing first ${shown}` : "";
  el("results-count").textContent = `${total.toLocaleString()} ${noun}${suffix}`;
}

function renderRows(items) {
  const body = el("table-body");
  if (!items.length) {
    body.innerHTML = `<tr><td colspan="6" class="muted">No matching entries.</td></tr>`;
    return;
  }
  body.innerHTML = items.map((item) => renderRow(item)).join("");
}

function renderJacket(item) {
  if (!item.jacketUrl) {
    return `<div class="jacket-placeholder">No jacket</div>`;
  }
  return `<img class="jacket" src="${escapeHtml(item.jacketUrl)}" alt="${escapeHtml(item.name || item.dataName)} jacket" loading="lazy">`;
}

function renderRow(item) {
  if (state.category === "music") {
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
  if (state.category === "characters") {
    return `<tr>
      <td>${escapeHtml(item.id)}</td>
      <td><strong>${escapeHtml(item.name || item.dataName)}</strong></td>
      <td>${escapeHtml(item.works)}</td>
      <td>${escapeHtml(item.imageKey)}</td>
    </tr>`;
  }
  if (state.category === "nameplates") {
    return `<tr>
      <td>${escapeHtml(item.id)}</td>
      <td><strong>${escapeHtml(item.name || item.dataName)}</strong></td>
      <td>${escapeHtml(item.image)}</td>
    </tr>`;
  }
  return "";
}

let searchTimer = null;
// Each tab asks the backend for its category, preserving the active search text.
async function loadCategory() {
  renderHead();
  el("table-body").innerHTML = `<tr><td colspan="6" class="muted">Loading...</td></tr>`;
  const params = new URLSearchParams({ limit: "400" });
  if (state.query) params.set("q", state.query);
  const data = await fetchJson(`/api/${state.category}?${params.toString()}`);
  renderResultCount(data.total, data.items.length);
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

boot().catch((error) => {
  el("game-root").textContent = error.message;
  el("table-body").innerHTML = `<tr><td class="muted">${escapeHtml(error.message)}</td></tr>`;
});









