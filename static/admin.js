const $ = (id) => document.getElementById(id);
const PAGE = 25;
let offset = 0, total = 0, timer;

function toast(msg) {
  const t = $("toast");
  t.textContent = msg; t.classList.add("show");
  clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove("show"), 1800);
}
function showError(msg) { $("msg").textContent = msg; $("msg").hidden = !msg; }

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (res.status === 401) { location.reload(); throw new Error("Login required."); }
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(typeof d.detail === "string" ? d.detail : `Request failed (${res.status}).`);
  }
  return res.status === 204 ? null : res.json();
}

function cell(tag, text, cls) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  el.textContent = text;
  return el;
}

function row(l) {
  const tr = document.createElement("tr");
  const a = document.createElement("a");
  a.href = l.short_url; a.target = "_blank"; a.rel = "noopener"; a.textContent = l.short_url;
  const c1 = document.createElement("td"); c1.append(a);
  const c2 = cell("td", l.original_url, "url"); c2.title = l.original_url;
  const c3 = cell("td", String(l.click_count), "num");
  const c4 = cell("td", new Date(l.created_at).toLocaleString(), "when");

  const actions = document.createElement("td"); actions.className = "actions";
  const mk = (label, cls, fn) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "act " + (cls || ""); b.textContent = label;
    b.addEventListener("click", fn); return b;
  };
  actions.append(
    mk("Copy", "", async () => { await navigator.clipboard?.writeText(l.short_url); toast("Copied"); }),
    mk("Edit", "", async () => {
      const url = prompt("New destination URL for " + l.code + ":", l.original_url);
      if (url === null || url.trim() === "" || url.trim() === l.original_url) return;
      try {
        await api(`/api/admin/links/${encodeURIComponent(l.code)}`, {
          method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }),
        });
        toast("Updated"); load();
      } catch (e) { showError(e.message); }
    }),
    mk("Delete", "danger", async () => {
      if (!confirm(`Delete ${l.short_url}?\nThis cannot be undone and the short link will stop working.`)) return;
      try {
        await api(`/api/admin/links/${encodeURIComponent(l.code)}`, { method: "DELETE" });
        toast("Deleted"); load();
      } catch (e) { showError(e.message); }
    }),
  );
  tr.append(c1, c2, c3, c4, actions);
  return tr;
}

async function load() {
  showError("");
  try {
    const q = encodeURIComponent($("q").value.trim());
    const d = await api(`/api/admin/links?q=${q}&limit=${PAGE}&offset=${offset}`);
    total = d.total;
    if (offset >= total && offset > 0) { offset = Math.max(0, total - PAGE); return load(); }
    $("s-links").textContent = d.total;
    $("s-clicks").textContent = d.total_clicks;
    $("rows").replaceChildren(...d.items.map(row));
    $("empty").hidden = d.items.length > 0;
    const from = d.items.length ? offset + 1 : 0;
    $("page-info").textContent = `${from}-${offset + d.items.length} of ${total}`;
    $("prev").disabled = offset === 0;
    $("next").disabled = offset + PAGE >= total;
  } catch (e) { showError(e.message); }
}

$("q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { offset = 0; load(); }, 250); });
$("reload").addEventListener("click", load);
$("prev").addEventListener("click", () => { offset = Math.max(0, offset - PAGE); load(); });
$("next").addEventListener("click", () => { offset += PAGE; load(); });
load();
