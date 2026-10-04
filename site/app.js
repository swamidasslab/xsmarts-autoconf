// SMARTS Library Parity: renders data.json (built by `xsmarts-autoconf site`).
// State lives in the query string: ?libs=a@v,b@v&tab=smarts&q=&colors=red,orange&diff=1&open=flag
"use strict";

const RANK = { red: 3, orange: 2, gray: 1, green: 0 };
// Rule areas per tab: SMARTS (query parsing and matching) vs SMIRKS (transforms and their products).
const TABS = { smarts: { areas: ["match", "syntax"] }, smirks: { areas: ["smirks", "products"] } };
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let DATA, BY_ID, state;

function readState() {
  const p = new URLSearchParams(location.search);
  const ids = (p.get("libs") || "").split(",").filter((id) => BY_ID[id]);
  return {
    libs: ids.length ? ids : defaultLibs(),
    tab: TABS[p.get("tab")] ? p.get("tab") : "smarts",
    q: p.get("q") || "",
    colors: new Set((p.get("colors") || "red,orange,green,gray").split(",")),
    diff: p.get("diff") === "1",
    open: new Set((p.get("open") || "").split(",").filter(Boolean)),
  };
}

function writeState() {
  const p = new URLSearchParams();
  p.set("libs", state.libs.join(","));
  p.set("tab", state.tab);
  if (state.q) p.set("q", state.q);
  const c = [...state.colors].sort((a, b) => RANK[b] - RANK[a]).join(",");
  if (c !== "red,orange,gray,green") p.set("colors", c);
  if (state.diff) p.set("diff", "1");
  if (state.open.size) p.set("open", [...state.open].join(","));
  history.replaceState(null, "", "?" + p.toString().replace(/%2C/g, ",").replace(/%40/g, "@"));
}

// Newest stored version of every library.
function defaultLibs() {
  const newest = {};
  for (const c of DATA.configs) newest[c.adapter] = c.id;
  return Object.values(newest);
}

function color(flag, value) {
  if (value == null) return "none";
  if (value === "UNKNOWN" || value === "AMBIGUOUS") return "gray";
  const sev = (DATA.severity[flag] || {})[value];
  if (sev === "bug") return "red";
  if (sev === "confusion") return "orange";
  return DATA.consensus[flag] === value ? "green" : "orange";
}

function rowInfo(rule) {
  const cells = state.libs.map((id) => {
    const v = BY_ID[id].flags[rule.flag];
    return { id, value: v ? v.value : null, observed: v ? v.observed : {}, color: color(rule.flag, v && v.value) };
  });
  const present = cells.filter((c) => c.value != null);
  const worst = present.reduce((w, c) => (RANK[c.color] > RANK[w] ? c.color : w), "green");
  const distinct = new Set(present.map((c) => c.value)).size;
  const n = (k) => present.filter((c) => c.color === k).length;
  return { cells, color: present.length ? worst : "gray", differs: distinct > 1, distinct, red: n("red"), orange: n("orange") };
}

// Newest config of every other library, colored for this flag.
function othersInfo(rule) {
  const self = BY_ID[state.libs[0]].adapter;
  const newest = {};
  for (const c of DATA.configs) if (c.adapter !== self && c.flags[rule.flag]) newest[c.adapter] = c;
  const list = Object.values(newest).map((c) => {
    const value = c.flags[rule.flag].value;
    return { id: c.id, adapter: c.adapter, value, color: color(rule.flag, value) };
  });
  const pts = { red: 2, orange: 1 };
  return { list, green: list.filter((o) => o.color === "green").length, score: list.reduce((n, o) => n + (pts[o.color] || 0), 0) };
}

function matches(rule, info) {
  if (!state.colors.has(info.color)) return false;
  if (state.diff && !info.differs) return false;
  if (state.q) {
    const hay = [rule.flag, rule.summary, ...Object.keys(rule.values), ...Object.values(rule.values),
      ...rule.cases.map((c) => `${c.query} ${c.mol}`), ...info.cells.map((c) => c.value)].join(" ").toLowerCase();
    if (!hay.includes(state.q.toLowerCase())) return false;
  }
  return true;
}

function renderLibs() {
  const groups = {};
  for (const c of DATA.configs) (groups[c.adapter] ||= []).push(c);
  $("#libs").innerHTML = Object.entries(groups).map(([lib, cs]) =>
    `<span class="lib"><b>${esc(lib)}</b>${cs.map((c) =>
      `<span class="chip${state.libs.includes(c.id) ? " on" : ""}" data-id="${esc(c.id)}" title="generated ${esc(c.generated || "?")}">${esc(c.version)}</span>`).join("")}</span>`).join("")
    + `<span class="chip" data-all="1">all newest</span>`;
}

function renderDetail(rule, info, extraCols = 0) {
  const vals = Object.entries(rule.values).map(([v, d]) =>
    `<dt><span class="cell ${color(rule.flag, v)}">${esc(v)}</span></dt><dd>${esc(d)}${DATA.consensus[rule.flag] === v ? " <b>(consensus)</b>" : ""}</dd>`).join("");
  const head = info.cells.map((c) => `<th>${esc(BY_ID[c.id].adapter)}<div class="meta">${esc(BY_ID[c.id].version)}</div></th>`).join("");
  const rows = rule.cases.map((cs) => {
    const obs = info.cells.map((c) => {
      const o = c.observed[cs.id];
      const expected = c.value && cs.expect ? cs.expect[c.value] : undefined;
      return `<td class="mono" title="${esc(expected === undefined ? "" : "expected for " + c.value + ": " + JSON.stringify(expected))}">${esc(o ?? "—")}</td>`;
    }).join("");
    const opts = [cs.view && `view ${cs.view}`, cs.explicit_h && "explicit H"].filter(Boolean).join(", ");
    return `<tr><td>${esc(cs.id)}${cs.note ? `<div class="meta">${esc(cs.note)}</div>` : ""}</td><td>${esc(cs.op)}${opts ? `<div class="meta">${esc(opts)}</div>` : ""}</td>
      <td class="mono">${esc(cs.query)}</td><td class="mono">${esc(cs.mol)}</td>${obs}</tr>`;
  }).join("");
  const prov = rule.provenance ? `<p class="meta">Provenance: ${esc(rule.provenance.discovered || "")}</p>` : "";
  const proc = rule.processing ? `<p class="meta">Processing: ${esc(rule.processing)}</p>` : "";
  return `<tr class="detail"><td colspan="${info.cells.length + 1 + extraCols}">
    <h4>Values</h4><dl>${vals}</dl>
    <h4>Cases and observed outputs</h4>
    <div style="overflow-x:auto"><table class="cases"><thead><tr><th>case</th><th>op</th><th>query</th><th>molecule</th>${head}</tr></thead><tbody>${rows}</tbody></table></div>
    ${proc}${prov}</td></tr>`;
}

function render() {
  writeState();
  renderLibs();
  document.querySelectorAll("#tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === state.tab));
  $("#q").value = state.q;
  $("#diff").checked = state.diff;
  document.querySelectorAll("#colors input").forEach((i) => (i.checked = state.colors.has(i.value)));

  const single = state.libs.length === 1;
  $("#grid thead").innerHTML = `<tr><th>behavior</th>${state.libs.map((id) => `<th>${esc(BY_ID[id].adapter)}<div class="meta">${esc(BY_ID[id].version)}</div></th>`).join("")}${single
    ? '<th>other libraries<div class="meta">newest version, colored by their result; underlined = same value</div></th>' : ""}</tr>`;

  const counts = { red: 0, orange: 0, green: 0, gray: 0 };
  let shown = 0;
  const body = [];
  let rows = DATA.rules.map((rule, i) => ({ rule, i, info: rowInfo(rule), others: single ? othersInfo(rule) : null }));
  if (single) {
    // One library: its own severity first. Within a severity, rows where the other libraries
    // comply better (lower score: red 2, orange 1, green 0) rank higher, then more of them green.
    rows.sort((a, b) => RANK[b.info.color] - RANK[a.info.color] || a.others.score - b.others.score
      || b.others.green - a.others.green || a.i - b.i);
  } else {
    // Comparing: most distinct values first, then severity score (red 2, orange 1, green 0), then most red.
    const score = (x) => 2 * x.red + x.orange;
    rows.sort((a, b) => b.info.distinct - a.info.distinct || score(b.info) - score(a.info) || b.info.red - a.info.red || a.i - b.i);
  }
  for (const { rule, info, others } of rows) {
    if (!TABS[state.tab].areas.includes(rule.area)) continue;
    if (!info.cells.some((c) => c.value != null)) continue;
    counts[info.color]++;
    if (!matches(rule, info)) continue;
    shown++;
    const cells = info.cells.map((c) => `<td>${c.value == null ? '<span class="cell none">not tested</span>'
      : `<span class="cell ${c.color}" title="${esc(rule.values[c.value] || c.value)}">${esc(c.value)}</span>`}</td>`).join("");
    let extra = "";
    if (single) {
      const v = info.cells[0].value;
      const chips = others.list.map((o) => `<span class="cell ${o.color}${o.value === v ? " same" : ""}" title="${esc(o.id)}: ${esc(o.value)}">${esc(o.adapter)}</span>`).join(" ");
      extra = `<td class="others"><b>${others.green}/${others.list.length}</b> <span class="meta">green</span><div>${chips || '<span class="meta">none tested</span>'}</div></td>`;
    }
    body.push(`<tr class="row ${info.color}" data-flag="${esc(rule.flag)}"><td class="flag"><div class="name">${esc(rule.flag)}</div><div class="sum">${esc(rule.summary)}</div></td>${cells}${extra}</tr>`);
    if (state.open.has(rule.flag)) body.push(renderDetail(rule, info, single ? 1 : 0));
  }
  $("#grid tbody").innerHTML = body.join("") || `<tr><td colspan="${state.libs.length + 1}">No rows match.</td></tr>`;
  $("#summary").innerHTML = `${shown} of ${Object.values(counts).reduce((a, b) => a + b, 0)} behaviors shown · ` +
    ["red", "orange", "green", "gray"].map((k) => `<i class="dot ${k}"></i>${counts[k]}`).join(" &nbsp;");
}

function bind() {
  $("#libs").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    if (chip.dataset.all) state.libs = defaultLibs();
    else {
      const id = chip.dataset.id;
      state.libs = state.libs.includes(id) ? state.libs.filter((x) => x !== id) : [...state.libs, id];
      if (!state.libs.length) state.libs = [id];
      const order = DATA.configs.map((c) => c.id);
      state.libs.sort((a, b) => order.indexOf(a) - order.indexOf(b));
    }
    render();
  });
  $("#tabs").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) { state.tab = b.dataset.tab; render(); }
  });
  let t;
  $("#q").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { state.q = e.target.value.trim(); render(); }, 150); });
  $("#diff").addEventListener("change", (e) => { state.diff = e.target.checked; render(); });
  $("#colors").addEventListener("change", (e) => {
    e.target.checked ? state.colors.add(e.target.value) : state.colors.delete(e.target.value);
    render();
  });
  $("#grid tbody").addEventListener("click", (e) => {
    const row = e.target.closest("tr.row");
    if (!row) return;
    const f = row.dataset.flag;
    state.open.has(f) ? state.open.delete(f) : state.open.add(f);
    render();
  });
  window.addEventListener("popstate", () => { state = readState(); render(); });
}

fetch("data.json").then((r) => r.json()).then((d) => {
  DATA = d;
  BY_ID = Object.fromEntries(d.configs.map((c) => [c.id, c]));
  state = readState();
  bind();
  render();
}).catch((e) => { $("#summary").textContent = "Could not load data.json: " + e; });
