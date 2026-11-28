// MIA web console (ADR-0029, REQ-WEB-006). Same origin as the API; every request carries the key the user
// typed (kept in sessionStorage, gone when the tab closes). Text from the Pi is only ever set with textContent.
//
// The only requests this page makes: GET /auth/status, /status, /telemetry, /audio/settings and
// /console/voice/events; POST /console/voice/settings; PUT /audio/settings. Nothing that drives the car.
"use strict";

(function () {
  const KEY_STORE = "mia.console.key";
  const LOG_LIMIT = 60;
  const STATUS_MS = 5000;
  const TELEMETRY_MS = 2000;
  const RETRY_MS = [1000, 2000, 5000, 10000];

  const $ = (id) => document.getElementById(id);

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
    const el = $("link");
    el.dataset.state = state;
    el.textContent = text;
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
      const detail = data && data.detail ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : res.statusText;
      const err = new Error(detail || ("HTTP " + res.status));
      err.status = res.status;
      throw err;
    }
    return data;
  }

  // ── Key ────────────────────────────────────────────────────────────────

  function wireKey() {
    $("key").value = apiKey ? "••••••••" : "";
    $("key-form").addEventListener("submit", (ev) => {
      ev.preventDefault();
      const v = $("key").value.trim();
      if (v && v !== "••••••••") { apiKey = v; storeKey(v); }
      $("key").value = apiKey ? "••••••••" : "";
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
      if (a && a.enabled && a.keys_configured > 0 && !apiKey) {
        note.hidden = false; note.dataset.kind = "bad";
        note.textContent = "This Pi requires an API key. Type it above; it is kept only for this tab.";
      } else if (a && !(a.enabled && a.keys_configured > 0)) {
        note.hidden = false; note.dataset.kind = "";
        note.textContent = "No API key is configured on this Pi, so the console only answers on the Pi itself (localhost).";
      } else {
        note.hidden = true;
      }
    } catch (e) {
      note.hidden = false; note.dataset.kind = "bad"; note.textContent = "Cannot reach the API: " + e.message;
    }
  }

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
    for (const [k, v] of rows) {
      const dt = document.createElement("dt"); dt.textContent = k;
      const dd = document.createElement("dd"); dd.textContent = short(v);
      dl.append(dt, dd);
    }
  }

  function renderTelemetry(t) {
    const box = $("telemetry");
    box.replaceChildren();
    const sources = (t && t.telemetry) || {};
    const names = Object.keys(sources).sort();
    if (!names.length) {
      const p = document.createElement("p"); p.className = "note"; p.textContent = "No telemetry yet.";
      box.append(p); return;
    }
    for (const name of names) {
      const h = document.createElement("h3"); h.textContent = name;
      const table = document.createElement("table");
      const reading = sources[name];
      const entries = reading && typeof reading === "object" ? Object.entries(reading) : [["value", reading]];
      for (const [k, v] of entries.slice(0, 40)) {
        const tr = document.createElement("tr");
        const a = document.createElement("td"); a.textContent = k;
        const b = document.createElement("td"); b.textContent = short(v);
        tr.append(a, b); table.append(tr);
      }
      box.append(h, table);
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

  // ── Voice stream ───────────────────────────────────────────────────────

  let voiceAbort = null;
  let voiceRetry = 0;

  function logEvent(ev) {
    const li = document.createElement("li");
    const time = new Date().toLocaleTimeString();
    let text = ev.type;
    if (ev.type === "state") text = "state " + ev.previous + " → " + ev.current;
    else if (ev.type === "feedback") text = "cue led=" + ev.led + " tone=" + ev.tone + " (" + ev.state + ")";
    else if (ev.type === "speak") text = "said #" + ev.id + " " + (ev.text || ev.phrase);
    else if (ev.type === "transcript") text = "heard “" + ev.text + "”";
    else if (ev.type === "settings") text = "settings " + ev.persona + " / " + ev.language + " / " + ev.verbosity;
    else text = ev.type + " " + short(ev);
    li.textContent = time + "  " + text;
    const log = $("voice-log");
    log.prepend(li);
    while (log.children.length > LOG_LIMIT) log.lastElementChild.remove();
  }

  function fillSelect(sel, values, chosen) {
    const keep = sel.value;
    sel.replaceChildren();
    for (const v of values) {
      const o = document.createElement("option"); o.value = v; o.textContent = v; sel.append(o);
    }
    sel.value = chosen || keep;
  }

  function onVoiceEvent(ev) {
    const note = $("voice-note");
    switch (ev.type) {
      case "hello":
        $("voice-backend").textContent = ev.backend === "router" ? "voice router" : "simulation";
        note.hidden = true; voiceRetry = 0; return;
      case "keepalive": return;
      case "unavailable":
        note.hidden = false; note.dataset.kind = "bad"; note.textContent = "Voice machine unavailable: " + ev.reason;
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
    logEvent(ev);
  }

  async function streamVoice() {
    if (voiceAbort) voiceAbort.abort();
    const ctl = new AbortController();
    voiceAbort = ctl;
    try {
      const res = await fetch("/console/voice/events", { headers: headers(), cache: "no-store",
        credentials: "omit", signal: ctl.signal });
      if (!res.ok || !res.body) {
        onVoiceEvent({ type: "unavailable", reason: "HTTP " + res.status });
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
          try { onVoiceEvent(JSON.parse(line)); } catch (e) { /* a partial or foreign line */ }
        }
      }
    } catch (e) {
      if (ctl.signal.aborted) return;
    }
    if (ctl.signal.aborted) return;
    const wait = RETRY_MS[Math.min(voiceRetry++, RETRY_MS.length - 1)];
    timers.push(setTimeout(streamVoice, wait));
  }

  // ── Settings forms ─────────────────────────────────────────────────────

  function wireForms() {
    $("voice-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const out = $("voice-form-out");
      out.dataset.kind = ""; out.textContent = "saving…";
      const body = { verbosity: $("verbosity").value };
      if ($("persona").value) body.persona = $("persona").value;
      if ($("language").value) body.language = $("language").value;
      try {
        const r = await call("POST", "/console/voice/settings", body);
        const s = r && r.settings;
        out.textContent = s ? "now " + s.persona + " / " + s.language + " / " + s.verbosity : "sent";
      } catch (e) { out.dataset.kind = "bad"; out.textContent = e.message; }
    });

    $("audio-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const out = $("audio-form-out");
      out.dataset.kind = ""; out.textContent = "saving…";
      try {
        const r = await call("PUT", "/audio/settings",
          { mic_transport: $("mic_transport").value, reply_output: $("reply_output").value });
        renderAudio(r); out.textContent = "saved";
      } catch (e) { out.dataset.kind = "bad"; out.textContent = e.message; }
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
    catch (e) { $("audio-form-out").dataset.kind = "bad"; $("audio-form-out").textContent = e.message; }
  }

  // ── Start ──────────────────────────────────────────────────────────────

  let stops = [];
  function restartAll() {
    for (const s of stops) s();
    while (timers.length) clearTimeout(timers.pop());
    setLink("idle", "connecting");
    checkAuth();
    loadAudio();
    stops = [poll(pollStatus, STATUS_MS), poll(pollTelemetry, TELEMETRY_MS)];
    voiceRetry = 0;
    streamVoice();
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireKey();
    wireForms();
    restartAll();
  });
})();
