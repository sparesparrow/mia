// MIA web console (ADR-0029, REQ-WEB-006, REQ-WEB-007, REQ-WEB-008). Same origin as the API; every request
// carries the key the user typed (kept in sessionStorage, gone when the tab closes). Text from the Pi is only ever
// set with textContent.
//
// The only requests this page makes: GET /auth/status, /status, /telemetry, /audio/settings, /console/setup,
// /console/agents/shapes, /console/voice/events and /console/agents/events; POST /console/voice/settings;
// PUT /audio/settings and /console/agents/shapes. Nothing that drives the car.
"use strict";

(function () {
  const KEY_STORE = "mia.console.key";
  const LOG_LIMIT = 60;
  const STATUS_MS = 5000;
  const TELEMETRY_MS = 2000;
  const SETUP_MS = 30000;
  const RETRY_MS = [1000, 2000, 5000, 10000];
  const ROLES = ["orchestrator", "evaluator", "executor"];
  const MASK = "••••••••";

  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  };

  function storedKey() {
    try { return sessionStorage.getItem(KEY_STORE) || ""; } catch (e) { return ""; }
  }
  function storeKey(value) {
    try {
      if (value) sessionStorage.setItem(KEY_STORE, value); else sessionStorage.removeItem(KEY_STORE);
    } catch (e) { /* private mode: the key lives for this page only */ }
  }

  let apiKey = storedKey();

  function headers(extra) {
    const h = Object.assign({ Accept: "application/json" }, extra || {});
    if (apiKey) h["X-API-Key"] = apiKey;
    return h;
  }

  function setLink(state, text) {
    const pill = $("link");
    pill.dataset.state = state;
    pill.textContent = text;
  }

  async function call(method, path, body) {
    const init = { method: method, headers: headers(body ? { "Content-Type": "application/json" } : null),
      cache: "no-store", credentials: "omit" };
    if (body) init.body = JSON.stringify(body);
    const res = await fetch(path, init);
    if (res.status === 401 || res.status === 403) {
      setLink("auth", res.status === 401 ? "key needed" : "refused");
    }
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok) {
      const detail = data && data.detail
        ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : res.statusText;
      const err = new Error(detail || ("HTTP " + res.status));
      err.status = res.status;
      throw err;
    }
    return data;
  }

  function say(out, text, bad) {
    out.dataset.kind = bad ? "bad" : "";
    out.textContent = text;
  }

  // ── Key ────────────────────────────────────────────────────────────────

  function wireKey() {
    $("key").value = apiKey ? MASK : "";
    $("key-form").addEventListener("submit", (ev) => {
      ev.preventDefault();
      const v = $("key").value.trim();
      if (v && v !== MASK) { apiKey = v; storeKey(v); }
      $("key").value = apiKey ? MASK : "";
      restartAll();
    });
    $("key-forget").addEventListener("click", () => {
      apiKey = ""; storeKey(""); $("key").value = ""; restartAll();
    });
  }

  async function checkAuth() {
    const note = $("auth-note");
    try {
      const a = await call("GET", "/auth/status");
      const keyed = a && a.enabled && a.keys_configured > 0;
      note.hidden = keyed && !!apiKey;
      if (keyed && !apiKey) say(note, "This Pi requires an API key. Type it above; it is kept only for this tab.", true);
      else if (!keyed) say(note, "No API key is configured on this Pi, so the console only answers on the Pi itself (localhost).");
    } catch (e) {
      note.hidden = false; say(note, "Cannot reach the API: " + e.message, true);
    }
  }

  // ── Setup checklist ────────────────────────────────────────────────────

  const ACTION_TARGET = { voice: "voice-form", audio: "audio-form", agents: "shape-form" };

  function renderSetup(r) {
    const list = $("setup-steps");
    list.replaceChildren();
    for (const step of r.steps || []) {
      const state = step.done === true ? "true" : step.done === false ? "false" : "unknown";
      const li = el("li");
      li.dataset.done = state;
      li.append(el("span", "mark", state === "true" ? "✓" : state === "false" ? "✗" : "?"));
      li.append(el("b", "", step.title));
      const target = ACTION_TARGET[step.action];
      if (target && state !== "true") {
        const go = el("button", "", "Go");
        go.type = "button";
        go.addEventListener("click", () => $(target).scrollIntoView({ behavior: "smooth", block: "center" }));
        li.append(go);
      } else {
        li.append(el("span"));
      }
      li.append(el("span", "detail", step.detail));
      if (state !== "true") li.append(el("span", "how", step.how));
      list.append(li);
    }
    $("setup-sum").textContent = r.message || "";
  }

  async function pollSetup() { renderSetup(await call("GET", "/console/setup")); }

  // ── Status and telemetry ───────────────────────────────────────────────

  function fmtBytes(n) {
    if (typeof n !== "number") return String(n);
    const u = ["B", "KiB", "MiB", "GiB"]; let i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return n.toFixed(i ? 1 : 0) + " " + u[i];
  }

  function short(value) {
    if (value === null || value === undefined) return "–";
    if (typeof value === "object") {
      const s = JSON.stringify(value);
      return s.length > 160 ? s.slice(0, 157) + "…" : s;
    }
    return String(value);
  }

  function renderStatus(s) {
    const rows = [];
    rows.push(["Health", s.status]);
    if (s.uptime_human) rows.push(["Uptime", String(s.uptime_human).split(".")[0]]);
    if (s.cpu) rows.push(["CPU", s.cpu.percent + " % of " + s.cpu.count]);
    if (s.memory) rows.push(["Memory", s.memory.percent + " % (" + fmtBytes(s.memory.available) + " free)"]);
    if ("devices_connected" in s) rows.push(["Devices", s.devices_connected]);
    if (s.telemetry_sources && typeof s.telemetry_sources === "object") {
      const parts = Object.entries(s.telemetry_sources).map(([name, src]) =>
        name + (src && typeof src.age_seconds === "number" ? " (" + src.age_seconds.toFixed(1) + " s ago)" : ""));
      rows.push(["Telemetry sources", parts.join(", ") || "none"]);
    }
    if (s.transport_health && typeof s.transport_health === "object") {
      const parts = Object.entries(s.transport_health).map(([name, t]) =>
        name + (t && t.connected ? " up" : " down"));
      rows.push(["Transports", parts.join(", ") || "none"]);
    }
    if (s.error) rows.push(["Error", s.error]);
    const dl = $("status");
    dl.replaceChildren();
    for (const [k, v] of rows) dl.append(el("dt", "", k), el("dd", "", short(v)));
  }

  function renderTelemetry(t) {
    const box = $("telemetry");
    box.replaceChildren();
    const sources = (t && t.telemetry) || {};
    const names = Object.keys(sources).sort();
    if (!names.length) { box.append(el("p", "note", "No telemetry yet.")); return; }
    for (const name of names) {
      const table = el("table");
      const reading = sources[name];
      const entries = reading && typeof reading === "object" ? Object.entries(reading) : [["value", reading]];
      for (const [k, v] of entries.slice(0, 40)) {
        const tr = el("tr");
        tr.append(el("td", "", k), el("td", "", short(v)));
        table.append(tr);
      }
      box.append(el("h3", "", name), table);
    }
  }

  const timers = [];
  function poll(fn, ms) {
    let stopped = false;
    const run = async () => {
      if (stopped) return;
      try { await fn(); } catch (e) { /* shown by the link pill */ }
      if (!stopped) timers.push(setTimeout(run, ms));
    };
    run();
    return () => { stopped = true; };
  }

  async function pollStatus() {
    try {
      renderStatus(await call("GET", "/status"));
      if ($("link").dataset.state !== "auth") setLink("ok", "connected");
    } catch (e) {
      if (e.status !== 401 && e.status !== 403) setLink("down", "API unreachable");
      throw e;
    }
  }
  async function pollTelemetry() { renderTelemetry(await call("GET", "/telemetry")); }

  // ── Streams (newline-delimited JSON over fetch, so the key can travel in a header) ──

  const streams = {};

  async function stream(name, path, onEvent) {
    if (streams[name]) streams[name].ctl.abort();
    const ctl = new AbortController();
    const state = streams[name] = { ctl: ctl, retry: (streams[name] && streams[name].retry) || 0 };
    try {
      const res = await fetch(path, { headers: headers(), cache: "no-store", credentials: "omit", signal: ctl.signal });
      if (!res.ok || !res.body) {
        onEvent({ type: "unavailable", reason: "HTTP " + res.status });
        if (res.status === 401 || res.status === 403) return; // wait for a key
        throw new Error("HTTP " + res.status);
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let nl;
        while ((nl = buf.indexOf("\n")) >= 0) {
          const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
          if (!line) continue;
          let ev;
          try { ev = JSON.parse(line); } catch (e) { continue; }
          if (ev.type === "hello") state.retry = 0;
          if (ev.type !== "keepalive") onEvent(ev);
        }
      }
    } catch (e) {
      if (ctl.signal.aborted) return;
    }
    if (ctl.signal.aborted) return;
    const wait = RETRY_MS[Math.min(state.retry++, RETRY_MS.length - 1)];
    timers.push(setTimeout(() => stream(name, path, onEvent), wait));
  }

  // ── Voice ──────────────────────────────────────────────────────────────

  function logVoice(ev) {
    let text = ev.type;
    if (ev.type === "state") text = "state " + ev.previous + " → " + ev.current;
    else if (ev.type === "feedback") text = "cue led=" + ev.led + " tone=" + ev.tone + " (" + ev.state + ")";
    else if (ev.type === "speak") text = "said #" + ev.id + " " + (ev.text || ev.phrase);
    else if (ev.type === "transcript") text = "heard “" + ev.text + "”";
    else if (ev.type === "settings") text = "settings " + ev.persona + " / " + ev.language + " / " + ev.verbosity;
    else text = ev.type + " " + short(ev);
    const log = $("voice-log");
    log.prepend(el("li", "", new Date().toLocaleTimeString() + "  " + text));
    while (log.children.length > LOG_LIMIT) log.lastElementChild.remove();
  }

  function fillSelect(sel, values, chosen, labels) {
    const keep = sel.value;
    sel.replaceChildren();
    for (const v of values) {
      const o = el("option", "", labels ? labels[v] || v : v);
      o.value = v;
      sel.append(o);
    }
    sel.value = chosen || keep;
  }

  function onVoiceEvent(ev) {
    const note = $("voice-note");
    switch (ev.type) {
      case "hello":
        $("voice-backend").textContent = ev.backend === "router" ? "voice router" : "simulation";
        note.hidden = true; return;
      case "unavailable":
        note.hidden = false; say(note, "Voice machine unavailable: " + ev.reason, true);
        $("voice-state").dataset.state = "unknown"; $("voice-state").textContent = "–";
        return;
      case "state":
        $("voice-state").dataset.state = ev.current; $("voice-state").textContent = ev.current; break;
      case "feedback":
        $("voice-led").textContent = ev.led; $("voice-tone").textContent = ev.tone; break;
      case "speak":
        $("voice-said").textContent = ev.text || ev.phrase; break;
      case "transcript":
        $("voice-heard").textContent = ev.text; break;
      case "settings":
        $("verbosity").value = ev.verbosity;
        fillSelect($("persona"), ev.personas || [ev.persona], ev.persona);
        fillSelect($("language"), ev.languages || [ev.language], ev.language);
        break;
    }
    logVoice(ev);
  }

  // ── Agents: shapes and handoffs ────────────────────────────────────────

  let shapesDoc = null;

  function avatar(persona, color) {
    const words = String(persona || "?").replace(/^the\s+/i, "").split(/\s+/);
    const a = el("span", "avatar", words.slice(0, 2).map((w) => w.charAt(0).toUpperCase()).join(""));
    a.style.background = color || "";
    a.setAttribute("aria-hidden", "true");
    return a;
  }

  function renderTrio() {
    const list = $("trio");
    list.replaceChildren();
    if (!shapesDoc) return;
    const shape = shapesDoc.shapes[shapesDoc.active];
    for (const role of ROLES) {
      const r = shape.roles[role];
      const li = el("li");
      const who = el("span", "who");
      who.append(el("b", "", r.persona), el("span", "", role + (r.voice ? " · voice " + r.voice : "")));
      li.append(avatar(r.persona, r.color), who);
      list.append(li);
    }
  }

  function roleRow(role, r) {
    const id = "shape-" + role;
    const label = el("label", "role", role);
    label.htmlFor = id + "-persona";
    const persona = el("input"); persona.id = id + "-persona"; persona.maxLength = 40; persona.required = true;
    persona.value = r.persona;
    const color = el("input"); color.type = "color"; color.id = id + "-color"; color.value = r.color;
    color.setAttribute("aria-label", role + " colour");
    const voice = el("input"); voice.id = id + "-voice"; voice.maxLength = 40; voice.value = r.voice || "";
    voice.placeholder = "voice"; voice.setAttribute("aria-label", role + " voice");
    return [label, persona, color, voice];
  }

  function fillShapeForm(shapeId) {
    if (!shapesDoc) return;
    const ids = Object.keys(shapesDoc.shapes);
    const labels = {};
    for (const id of ids) labels[id] = shapesDoc.shapes[id].label + (id === shapesDoc.active ? " (in use)" : "");
    fillSelect($("shape-active"), ids, shapeId || shapesDoc.active, labels);
    const shape = shapesDoc.shapes[$("shape-active").value];
    $("shape-label").value = shape.label;
    const box = $("shape-roles");
    box.replaceChildren(el("legend", "", "Personas for the three roles"));
    for (const role of ROLES) box.append(...roleRow(role, shape.roles[role]));
  }

  function formShape() {
    const roles = {};
    for (const role of ROLES) {
      roles[role] = { persona: $("shape-" + role + "-persona").value.trim(),
        color: $("shape-" + role + "-color").value, voice: $("shape-" + role + "-voice").value.trim() };
    }
    return { label: $("shape-label").value.trim() || $("shape-active").value, roles: roles };
  }

  async function saveShapes(shapeId, shape) {
    const out = $("shape-form-out");
    say(out, "saving…");
    const doc = { active: shapeId, shapes: Object.assign({}, shapesDoc.shapes) };
    doc.shapes[shapeId] = shape;
    try {
      const r = await call("PUT", "/console/agents/shapes", doc);
      shapesDoc = { active: r.active, shapes: r.shapes };
      renderTrio(); fillShapeForm(r.active); say(out, "in use: " + r.shapes[r.active].label);
      pollSetup().catch(() => {});
    } catch (e) { say(out, e.message, true); }
  }

  function wireShapes() {
    $("shape-active").addEventListener("change", () => fillShapeForm($("shape-active").value));
    $("shape-form").addEventListener("submit", (ev) => {
      ev.preventDefault();
      if (shapesDoc) saveShapes($("shape-active").value, formShape());
    });
    $("shape-copy").addEventListener("click", () => {
      const id = $("shape-new").value.trim();
      if (!/^[a-z][a-z0-9_-]{0,23}$/.test(id)) {
        say($("shape-form-out"), "a new id is a short lowercase name, e.g. dwarf", true); return;
      }
      if (shapesDoc) { $("shape-new").value = ""; saveShapes(id, formShape()); }
    });
  }

  function onAgentEvent(ev) {
    const note = $("agents-note");
    switch (ev.type) {
      case "hello":
      case "shapes":
        note.hidden = true;
        shapesDoc = { active: ev.active, shapes: ev.shapes };
        renderTrio(); fillShapeForm(ev.active);
        if (ev.type === "hello") $("handoff-log").replaceChildren();
        return;
      case "unavailable":
        note.hidden = false; say(note, "Handoff stream unavailable: " + ev.reason, true); return;
      case "handoff": {
        const li = el("li");
        const text = el("span", "text");
        text.append(el("b", "", ev.from_persona + " → " + ev.to_persona));
        if (ev.task) text.append(document.createTextNode(" [" + ev.task + "]"));
        if (ev.summary) text.append(document.createTextNode(": " + ev.summary));
        const at = ev.at ? new Date(ev.at) : new Date();
        text.append(el("span", "time", " " + at.toLocaleTimeString()));
        li.append(avatar(ev.from_persona, ev.from_color), avatar(ev.to_persona, ev.to_color), text);
        const log = $("handoff-log");
        log.prepend(li);
        while (log.children.length > LOG_LIMIT) log.lastElementChild.remove();
        return;
      }
    }
  }

  // ── Settings forms ─────────────────────────────────────────────────────

  function wireForms() {
    $("voice-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const out = $("voice-form-out");
      say(out, "saving…");
      const body = { verbosity: $("verbosity").value };
      if ($("persona").value) body.persona = $("persona").value;
      if ($("language").value) body.language = $("language").value;
      try {
        const r = await call("POST", "/console/voice/settings", body);
        const s = r && r.settings;
        say(out, s ? "now " + s.persona + " / " + s.language + " / " + s.verbosity : "sent");
        pollSetup().catch(() => {});
      } catch (e) { say(out, e.message, true); }
    });

    $("audio-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const out = $("audio-form-out");
      say(out, "saving…");
      try {
        const r = await call("PUT", "/audio/settings",
          { mic_transport: $("mic_transport").value, reply_output: $("reply_output").value });
        renderAudio(r); say(out, "saved");
        pollSetup().catch(() => {});
      } catch (e) { say(out, e.message, true); }
    });
  }

  function renderAudio(a) {
    if (!a) return;
    const caps = a.capabilities || {};
    for (const field of ["mic_transport", "reply_output"]) {
      const sel = $(field);
      const can = caps[field] || {};
      for (const o of sel.options) {
        o.disabled = can[o.value] === false;
        o.textContent = o.textContent.replace(/ \(not on this Pi\)$/, "") + (o.disabled ? " (not on this Pi)" : "");
      }
      if (a[field]) sel.value = a[field];
    }
  }

  async function loadAudio() {
    try { renderAudio(await call("GET", "/audio/settings")); }
    catch (e) { say($("audio-form-out"), e.message, true); }
  }

  async function loadShapes() {
    try {
      const r = await call("GET", "/console/agents/shapes");
      shapesDoc = { active: r.active, shapes: r.shapes };
      renderTrio(); fillShapeForm(r.active);
    } catch (e) { say($("shape-form-out"), e.message, true); }
  }

  // ── Start ──────────────────────────────────────────────────────────────

  let stops = [];
  function restartAll() {
    for (const s of stops) s();
    while (timers.length) clearTimeout(timers.pop());
    setLink("idle", "connecting");
    checkAuth();
    loadAudio();
    loadShapes();
    stops = [poll(pollStatus, STATUS_MS), poll(pollTelemetry, TELEMETRY_MS), poll(pollSetup, SETUP_MS)];
    for (const name in streams) streams[name].retry = 0;
    stream("voice", "/console/voice/events", onVoiceEvent);
    stream("agents", "/console/agents/events", onAgentEvent);
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireKey();
    wireForms();
    wireShapes();
    restartAll();
  });
})();
