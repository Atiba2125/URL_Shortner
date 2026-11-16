const $ = (id) => document.getElementById(id);
const form = $("form"), urlInput = $("url"), submitBtn = $("submit"), errorEl = $("error");
const resultEl = $("result"), shortEl = $("short"), originalEl = $("original"), copyBtn = $("copy");
const historyWrap = $("history-wrap"), historyEl = $("history"), toastEl = $("toast");

const HISTORY_KEY = "shortener.history";
const THEME_KEY = "shortener.theme";

/* ---------- storage helpers (never throw) ---------- */
function load(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode etc. */ }
}

/* ---------- theme ---------- */
function applyTheme(theme) { document.documentElement.dataset.theme = theme; }
applyTheme(load(THEME_KEY, matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
$("theme").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  save(THEME_KEY, next);
});

/* ---------- toast + copy ---------- */
let toastTimer;
function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("show"), 1800);
}
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const t = document.createElement("textarea");
    t.value = text; document.body.appendChild(t); t.select();
    document.execCommand("copy"); t.remove();
  }
  toast("Copied to clipboard");
}

/* ---------- history ---------- */
function renderHistory() {
  const items = load(HISTORY_KEY, []);
  historyWrap.hidden = items.length === 0;
  historyEl.replaceChildren(...items.map((it) => {
    const li = document.createElement("li");
    const info = document.createElement("div");
    info.className = "h-info";
    const a = document.createElement("a");
    a.className = "h-short"; a.href = it.short_url; a.target = "_blank"; a.rel = "noopener";
    a.textContent = it.short_url;
    const o = document.createElement("span");
    o.className = "h-orig"; o.textContent = it.original_url; o.title = it.original_url;
    info.append(a, o);
    const b = document.createElement("button");
    b.className = "h-copy"; b.type = "button"; b.textContent = "Copy";
    b.addEventListener("click", () => copyText(it.short_url));
    li.append(info, b);
    return li;
  }));
}
function addToHistory(item) {
  const items = load(HISTORY_KEY, []).filter((i) => i.code !== item.code);
  items.unshift(item);
  save(HISTORY_KEY, items.slice(0, 8));
  renderHistory();
}
$("clear").addEventListener("click", () => { save(HISTORY_KEY, []); renderHistory(); });

/* ---------- shorten ---------- */
function showError(msg) {
  errorEl.textContent = msg;
  errorEl.hidden = false;
}
function setLoading(on) {
  submitBtn.disabled = on;
  submitBtn.classList.toggle("loading", on);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.hidden = true;
  resultEl.hidden = true;

  const url = urlInput.value.trim();
  if (!url) { showError("Please paste a link first."); urlInput.focus(); return; }

  setLoading(true);
  try {
    const res = await fetch("/api/shorten", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : "That link doesn't look valid.");
    }
    shortEl.textContent = data.short_url;
    shortEl.href = data.short_url;
    originalEl.textContent = data.original_url;
    originalEl.title = data.original_url;
    copyBtn.textContent = "Copy";
    copyBtn.classList.remove("done");
    resultEl.hidden = false;
    addToHistory(data);
  } catch (err) {
    showError(err.message || "Something went wrong. Please try again.");
  } finally {
    setLoading(false);
  }
});

copyBtn.addEventListener("click", async () => {
  await copyText(shortEl.textContent);
  copyBtn.textContent = "Copied!";
  copyBtn.classList.add("done");
});

renderHistory();
