// Forge UI: one in-memory model in the forge.yaml JSON shape; every edit revalidates through the API.

const params = new URLSearchParams(location.search);
const token = params.get("token") || "";
history.replaceState(null, "", location.pathname);

const PROJECT_KEYS = ["project_name", "target_path", "group_id", "artifact_id"];
const $ = (sel) => document.querySelector(sel);

let meta = { templates: [], field_types: [], relation_types: [] };
let model = { template: "base-layered", entities: {} };
let validation = { ok: false, errors: [] };
let previewFiles = [];
let selectedFile = null;

async function api(path, body) {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "X-Forge-Token": token, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  return { status: res.status, data };
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v === true) node.setAttribute(k, "");
    else if (v !== false && v != null) node.setAttribute(k, v);
  }
  for (const c of children.flat()) node.append(c instanceof Node ? c : document.createTextNode(c));
  return node;
}

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

// ---------- model helpers ----------

function renameKey(obj, oldKey, newKey) {
  return Object.fromEntries(Object.entries(obj).map(([k, v]) => [k === oldKey ? newKey : k, v]));
}

function renameEntity(oldName, newName) {
  if (!newName || newName === oldName || newName in model.entities) return false;
  model.entities = renameKey(model.entities, oldName, newName);
  for (const entity of Object.values(model.entities)) {
    for (const rel of Object.values(entity.relations || {})) {
      if (rel.target === oldName) rel.target = newName;
    }
  }
  return true;
}

function uniqueName(base, existing) {
  let name = base;
  for (let i = 2; name in existing; i++) name = base + i;
  return name;
}

function setOrDelete(obj, key, value) {
  if (value === "" || value === null || value === undefined || value === false) delete obj[key];
  else obj[key] = value;
}

function toInt(text) {
  const n = parseInt(text, 10);
  return Number.isNaN(n) ? "" : n;
}

function parseDefault(type, text) {
  if (text === "") return "";
  if (type === "boolean") return text === "true";
  if (["int", "long", "decimal"].includes(type) && !Number.isNaN(Number(text))) return Number(text);
  return text;
}

// ---------- validation ----------

const revalidate = debounce(async () => {
  const { data } = await api("/api/validate", model);
  validation = data;
  renderValidation();
  renderGraph();
  renderEntityErrors();
  updateButtons();
}, 300);

function projectComplete() {
  return PROJECT_KEYS.every((k) => (model[k] || "").trim() !== "");
}

function updateButtons() {
  const ready = validation.ok && projectComplete();
  $("#generate-btn").disabled = !ready;
  $("#tab-preview").disabled = !validation.ok;
}

function renderValidation() {
  const box = $("#validation");
  box.replaceChildren();
  if (!validation.ok) {
    box.append(el("div", { class: "bad" }, "Model has errors"));
    box.append(el("ul", {}, (validation.errors || []).map((e) => el("li", {}, e))));
    return;
  }
  box.append(el("div", { class: "ok" }, `OK: ${validation.entity_count} entities, ${validation.join_tables.length} join tables`));
  if (validation.join_tables.length) box.append(el("div", { class: "muted" }, "Join tables: " + validation.join_tables.join(", ")));
  if (validation.changelog_files.length) {
    box.append(el("div", { class: "muted" }, "Liquibase changelog order:"));
    box.append(el("ol", {}, validation.changelog_files.map((f) => el("li", {}, f))));
  }
  if (!projectComplete()) box.append(el("div", { class: "muted" }, "Fill in all project fields to preview and generate."));
}

function erroredEntities() {
  const names = new Set();
  if (validation.ok) return names;
  for (const msg of validation.errors || []) {
    for (const m of msg.matchAll(/Entity '([^']+)'|entities\.([A-Za-z0-9_]+)/g)) names.add(m[1] || m[2]);
  }
  return names;
}

function renderEntityErrors() {
  const bad = erroredEntities();
  document.querySelectorAll(".entity").forEach((card) => card.classList.toggle("has-error", bad.has(card.dataset.name)));
}

// ---------- project panel ----------

function renderProject() {
  const select = $("#p-template");
  select.replaceChildren(...meta.templates.map((t) => el("option", { value: t }, t)));
  for (const input of document.querySelectorAll("#project-panel [data-key]")) {
    input.value = model[input.dataset.key] ?? "";
  }
  const minimal = model.template === "minimal";
  $("#entities-disabled").hidden = !minimal;
  $("#entities").hidden = minimal;
  $("#add-entity").disabled = minimal;
}

function bindProject() {
  for (const input of document.querySelectorAll("#project-panel [data-key]")) {
    input.addEventListener("input", () => {
      model[input.dataset.key] = input.value;
      if (input.dataset.key === "template" && input.value === "minimal") model.entities = {};
      if (input.dataset.key === "template") {
        renderProject();
        renderEntities();
      }
      revalidate();
      updateButtons();
    });
  }
}

// ---------- entities panel ----------

function textInput(value, onChange, attrs = {}, event = "input") {
  const input = el("input", { value: value ?? "", ...attrs });
  input.value = value ?? "";
  input.addEventListener(event, () => onChange(input.value));
  return input;
}

function checkbox(checked, onChange) {
  const input = el("input", { type: "checkbox" });
  input.checked = !!checked;
  input.addEventListener("change", () => onChange(input.checked));
  return input;
}

function select(options, value, onChange) {
  const node = el("select", {}, options.map((o) => el("option", { value: o }, o)));
  node.value = value;
  node.addEventListener("change", () => onChange(node.value));
  return node;
}

function fieldExtras(field) {
  const set = (key, conv) => (v) => {
    setOrDelete(field, key, conv ? conv(v) : v);
    revalidate();
  };
  const box = el("div", { class: "extras" });
  if (field.type === "string") {
    box.append(textInput(field.length, set("length", toInt), { placeholder: "length", type: "number", min: "1" }));
    box.append(el("label", { class: "inline" }, checkbox(field.text, (v) => { setOrDelete(field, "text", v); if (v) delete field.length; renderEntities(); revalidate(); }), "text"));
  } else if (field.type === "decimal") {
    box.append(textInput(field.precision, set("precision", toInt), { placeholder: "precision", type: "number", min: "1" }));
    box.append(textInput(field.scale, (v) => { const n = toInt(v); if (n === "") delete field.scale; else field.scale = n; revalidate(); }, { placeholder: "scale", type: "number", min: "0" }));
  } else if (field.type === "enum") {
    box.append(textInput((field.values || []).join(", "), (v) => {
      const values = v.split(",").map((s) => s.trim()).filter(Boolean);
      setOrDelete(field, "values", values.length ? values : "");
      revalidate();
    }, { class: "wide", placeholder: "A, B, C" }));
  }
  return box;
}

function fieldRow(entityName, fname, field) {
  const entity = model.entities[entityName];
  const defaultCell = field.type === "boolean"
    ? select(["", "true", "false"], field.default === undefined ? "" : String(field.default), (v) => { setOrDelete(field, "default", v === "" ? "" : v === "true"); if (v === "false") field.default = false; revalidate(); })
    : textInput(field.default === undefined ? "" : String(field.default), (v) => { setOrDelete(field, "default", parseDefault(field.type, v)); revalidate(); }, { placeholder: "default" });
  return el("tr", {},
    el("td", {}, textInput(fname, (v) => {
      if (!v || v === fname || v in entity.fields) { renderEntities(); return; }
      entity.fields = renameKey(entity.fields, fname, v);
      renderEntities();
      revalidate();
    }, { "aria-label": "field name" }, "change")),
    el("td", {}, select(meta.field_types, field.type, (v) => {
      field.type = v;
      for (const k of ["length", "text", "precision", "scale", "values", "default"]) delete field[k];
      renderEntities();
      revalidate();
    })),
    el("td", {}, fieldExtras(field)),
    el("td", {}, checkbox(field.required, (v) => { setOrDelete(field, "required", v); revalidate(); })),
    el("td", {}, checkbox(field.unique, (v) => { setOrDelete(field, "unique", v); revalidate(); })),
    el("td", {}, defaultCell),
    el("td", {}, el("button", { class: "btn small danger", title: "Delete field", onclick: () => { delete entity.fields[fname]; renderEntities(); revalidate(); } }, "×")),
  );
}

function relationExtras(entityName, rel) {
  const box = el("div", { class: "extras" });
  const upd = () => revalidate();
  if (rel.type === "many-to-one") {
    box.append(textInput(rel.inverse, (v) => { setOrDelete(rel, "inverse", v); upd(); }, { placeholder: "inverse" }));
  } else if (rel.type === "one-to-many") {
    box.append(textInput(rel.mappedBy, (v) => { setOrDelete(rel, "mappedBy", v); upd(); }, { placeholder: "mappedBy" }));
    box.append(el("label", { class: "inline" }, checkbox(rel.cascade === "all", (v) => { setOrDelete(rel, "cascade", v ? "all" : ""); upd(); }), "cascade"));
    box.append(el("label", { class: "inline" }, checkbox(rel.orphanRemoval, (v) => { setOrDelete(rel, "orphanRemoval", v); upd(); }), "orphan"));
  }
  return box;
}

function relationRow(entityName, rname, rel) {
  const entity = model.entities[entityName];
  const others = Object.keys(model.entities).filter((n) => n !== entityName);
  const targets = [...new Set([...others, ...(rel.target ? [rel.target] : [])])];
  return el("tr", {},
    el("td", {}, textInput(rname, (v) => {
      if (!v || v === rname || v in entity.relations) { renderEntities(); return; }
      entity.relations = renameKey(entity.relations, rname, v);
      renderEntities();
      revalidate();
    }, { "aria-label": "relation name" }, "change")),
    el("td", {}, select(meta.relation_types, rel.type, (v) => {
      rel.type = v;
      for (const k of ["inverse", "mappedBy", "cascade", "orphanRemoval"]) delete rel[k];
      if (v === "many-to-many") delete rel.required;
      renderEntities();
      revalidate();
    })),
    el("td", {}, select(["", ...targets], rel.target || "", (v) => { rel.target = v; revalidate(); renderGraph(); })),
    el("td", {}, el("label", { class: "inline" }, checkbox(rel.required, (v) => { setOrDelete(rel, "required", v); revalidate(); }), "req")),
    el("td", {}, relationExtras(entityName, rel)),
    el("td", {}, el("button", { class: "btn small danger", title: "Delete relation", onclick: () => { delete entity.relations[rname]; renderEntities(); revalidate(); } }, "×")),
  );
}

function entityCard(name) {
  const entity = model.entities[name];
  entity.fields ||= {};
  entity.relations ||= {};
  const fieldRows = Object.entries(entity.fields).map(([n, f]) => fieldRow(name, n, f));
  const relRows = Object.entries(entity.relations).map(([n, r]) => relationRow(name, n, r));
  return el("div", { class: "entity", "data-name": name },
    el("div", { class: "entity-head" },
      textInput(name, (v) => {
        const ok = renameEntity(name, v.trim());
        renderEntities();
        if (ok) revalidate();
      }, { class: "entity-name", "aria-label": "entity name" }, "change"),
      textInput(entity.table, (v) => { setOrDelete(entity, "table", v); revalidate(); }, { placeholder: "table (optional)" }),
      el("button", { class: "btn danger", onclick: () => {
        delete model.entities[name];
        for (const e of Object.values(model.entities)) {
          for (const [rn, r] of Object.entries(e.relations || {})) if (r.target === name) delete e.relations[rn];
        }
        renderEntities();
        revalidate();
      } }, "Delete"),
    ),
    el("h3", {}, "Fields", el("button", { class: "btn small", onclick: () => { entity.fields[uniqueName("field", entity.fields)] = { type: "string" }; renderEntities(); revalidate(); } }, "+ field")),
    fieldRows.length ? el("table", {}, el("thead", {}, el("tr", {}, ["Name", "Type", "Options", "Req", "Uniq", "Default", ""].map((h) => el("th", {}, h)))), el("tbody", {}, fieldRows)) : el("span", { class: "muted" }, "No fields"),
    el("h3", {}, "Relations", el("button", { class: "btn small", disabled: Object.keys(model.entities).length < 2, title: "Needs a second entity", onclick: () => {
      const target = Object.keys(model.entities).find((n) => n !== name) || "";
      entity.relations[uniqueName("relation", entity.relations)] = { type: "many-to-one", target };
      renderEntities();
      revalidate();
    } }, "+ relation")),
    relRows.length ? el("table", {}, el("thead", {}, el("tr", {}, ["Name", "Type", "Target", "", "Options", ""].map((h) => el("th", {}, h)))), el("tbody", {}, relRows)) : el("span", { class: "muted" }, "No relations"),
  );
}

function renderEntities() {
  const root = $("#entities");
  root.replaceChildren(...Object.keys(model.entities).map(entityCard));
  renderGraph();
  renderEntityErrors();
}

// ---------- graph ----------

const SVG_NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderGraph() {
  const names = Object.keys(model.entities);
  const root = $("#graph");
  root.replaceChildren();
  if (!names.length) {
    root.append(el("span", { class: "muted" }, "No entities yet"));
    return;
  }
  const W = 190, GAP_X = 50, GAP_Y = 60, LINE = 15, HEAD = 26, COLS = 3, MAXF = 8;
  const boxes = {};
  const rowHeights = [];
  names.forEach((n, i) => {
    const shown = Object.keys(model.entities[n].fields || {});
    const lines = Math.min(shown.length, MAXF) + (shown.length > MAXF ? 1 : 0);
    const h = HEAD + Math.max(lines, 1) * LINE + 8;
    const row = Math.floor(i / COLS);
    rowHeights[row] = Math.max(rowHeights[row] || 0, h);
    boxes[n] = { col: i % COLS, row, h, shown };
  });
  const rowY = [];
  let y = 10;
  rowHeights.forEach((h, r) => { rowY[r] = y; y += h + GAP_Y; });
  for (const b of Object.values(boxes)) { b.x = 10 + b.col * (W + GAP_X); b.y = rowY[b.row]; }
  const width = 20 + Math.min(COLS, names.length) * W + (Math.min(COLS, names.length) - 1) * GAP_X;
  const canvas = svg("svg", { viewBox: `0 0 ${width} ${y - GAP_Y + 20}`, role: "img", "aria-label": "Entity graph" });
  const defs = svg("defs");
  const marker = svg("marker", { id: "arrow", viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" });
  marker.append(svg("path", { d: "M 0 0 L 10 5 L 0 10 z" }));
  defs.append(marker);
  canvas.append(defs);

  const bad = erroredEntities();
  for (const [n, b] of Object.entries(boxes)) {
    const g = svg("g");
    g.append(svg("rect", { class: "box" + (bad.has(n) ? " err" : ""), x: b.x, y: b.y, width: W, height: b.h, rx: 6, style: bad.has(n) ? "stroke: var(--error)" : "" }));
    g.append(svg("text", { class: "ename", x: b.x + 10, y: b.y + 18 }, n));
    b.shown.slice(0, MAXF).forEach((f, i) => g.append(svg("text", { class: "fname", x: b.x + 10, y: b.y + HEAD + 12 + i * LINE }, f)));
    if (b.shown.length > MAXF) g.append(svg("text", { class: "fname", x: b.x + 10, y: b.y + HEAD + 12 + MAXF * LINE }, `… +${b.shown.length - MAXF} more`));
    canvas.append(g);
  }

  const centre = (b) => ({ x: b.x + W / 2, y: b.y + b.h / 2 });
  const edge = (b, toward) => {
    const c = centre(b);
    const dx = toward.x - c.x, dy = toward.y - c.y;
    const sx = dx ? (W / 2) / Math.abs(dx) : Infinity;
    const sy = dy ? (b.h / 2) / Math.abs(dy) : Infinity;
    const s = Math.min(sx, sy);
    return { x: c.x + dx * s, y: c.y + dy * s };
  };
  let loop = 0;
  for (const [n, entity] of Object.entries(model.entities)) {
    for (const [rn, rel] of Object.entries(entity.relations || {})) {
      const from = boxes[n], to = boxes[rel.target];
      if (!to) continue;
      if (from === to) {
        const x = from.x + W, y0 = from.y + 20 + 14 * loop++;
        canvas.append(svg("path", { class: "edge", d: `M ${x} ${y0} C ${x + 30} ${y0 - 10}, ${x + 30} ${y0 + 20}, ${x} ${y0 + 10}`, "marker-end": "url(#arrow)" }));
        canvas.append(svg("text", { class: "elabel", x: x + 4, y: y0 - 4 }, rel.type));
        continue;
      }
      const a = edge(from, centre(to)), b = edge(to, centre(from));
      canvas.append(svg("line", { class: "edge", x1: a.x, y1: a.y, x2: b.x, y2: b.y, "marker-end": "url(#arrow)" }));
      canvas.append(svg("text", { class: "elabel", "text-anchor": "middle", x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - 3 }, `${rel.type} (${rn})`));
    }
  }
  root.append(canvas);
}

// ---------- tabs, preview, import/export, generate ----------

function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".view").forEach((v) => { v.hidden = v.id !== `view-${name}`; });
  if (name === "preview") loadPreview();
}

async function loadPreview() {
  $("#preview-error").textContent = "";
  const { data } = await api("/api/preview", model);
  if (data.ok === false) {
    $("#preview-error").textContent = (data.errors || []).join("; ");
    previewFiles = [];
  } else {
    previewFiles = data.files;
  }
  renderFileList();
}

function renderFileList() {
  const filter = $("#file-filter").value.toLowerCase();
  const list = $("#file-list");
  list.replaceChildren(...previewFiles
    .filter((f) => f.path.toLowerCase().includes(filter))
    .map((f) => el("li", { class: f.path === selectedFile ? "sel" : "", onclick: () => { selectedFile = f.path; renderFileList(); showFile(f); } }, f.path)));
}

function showFile(f) {
  $("#file-title").textContent = f.path;
  $("#file-content").textContent = f.content === null ? "binary file" : f.content;
}

async function exportModel() {
  const { data } = await api("/api/export", model);
  const blob = new Blob([data.text], { type: "text/yaml" });
  const a = el("a", { href: URL.createObjectURL(blob), download: "forge.yaml" });
  document.body.append(a);
  a.click();
  a.remove();
}

async function importModel(file) {
  const text = await file.text();
  const { data } = await api("/api/import", { text });
  if (!data.ok) {
    validation = { ok: false, errors: data.errors };
    renderValidation();
    return;
  }
  model = { template: meta.default_template, target_path: meta.default_target_path, ...data.model };
  renderProject();
  renderEntities();
  revalidate();
}

async function generate() {
  const btn = $("#generate-btn");
  btn.disabled = true;
  $("#generate-status").textContent = "Generating…";
  $("#generate-result").replaceChildren();
  const { status, data } = await api("/api/generate", { model, run_compile: $("#run-compile").checked });
  $("#generate-status").textContent = "";
  const out = $("#generate-result");
  if (status === 409 || (!data.checks && data.ok === false)) {
    out.append(el("p", { class: "error-text" }, (data.errors || ["generation failed"]).join("; ")));
  } else {
    for (const c of data.checks) {
      const card = el("div", { class: "check " + (c.passed ? "pass" : "fail") }, el("strong", {}, `${c.passed ? "✔" : "✘"} ${c.name}`), " — " + c.message);
      if (c.details) card.append(el("details", {}, el("summary", {}, "Details"), el("pre", {}, c.details)));
      out.append(card);
    }
    if (data.ok) {
      out.append(el("pre", { class: "next-steps" }, `cd ${data.target_dir}\ndocker compose up -d\nmvn spring-boot:run`));
    } else {
      out.append(el("p", { class: "error-text" }, `Checks failed; the generated folder was left in place: ${data.target_dir}`));
    }
  }
  updateButtons();
}

// ---------- init ----------

async function init() {
  const res = await api("/api/meta");
  meta = res.data;
  model.template = meta.default_template;
  model.target_path = meta.default_target_path;
  bindProject();
  renderProject();
  renderEntities();
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => !t.disabled && showTab(t.dataset.tab)));
  $("#add-entity").addEventListener("click", () => {
    model.entities[uniqueName("Entity", model.entities)] = { fields: {}, relations: {} };
    renderEntities();
    revalidate();
  });
  $("#file-filter").addEventListener("input", renderFileList);
  $("#export-btn").addEventListener("click", exportModel);
  $("#import-file").addEventListener("change", (e) => { if (e.target.files[0]) importModel(e.target.files[0]); e.target.value = ""; });
  $("#generate-btn").addEventListener("click", generate);
  revalidate();
}

init();
