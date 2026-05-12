/**
 * MIA Voice Chat — Meta-Harness
 *
 * Implements voice-chatbot-web-ui skill patterns with:
 *   - WebSocket client + exponential back-off
 *   - VoiceRecorder state machine (idle → listening → processing → speaking)
 *   - TTSPlayer (chunked AudioContext queue)
 *   - MockBackend (full simulation when server unreachable)
 *   - SpectrumViz  (canvas FFT — real mic data or procedural)
 *   - Typewriter reveal for MIA responses
 */

'use strict';

// Derive WS URLs from window.location when served from the Pi,
// fall back to localhost for local development.
const _wsHost   = (window.MIA_CONFIG && window.MIA_CONFIG.wsHost)
                || window.location.host
                || 'localhost:8000';
const _wsProto  = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL      = `${_wsProto}//${_wsHost}/ws/voice`;
const WS_FALLBACK = `${_wsProto}//${_wsHost}/ws`;

const VoiceState = Object.freeze({
  IDLE: 'idle', LISTENING: 'listening', PROCESSING: 'processing', SPEAKING: 'speaking',
});

// ── SpectrumViz ───────────────────────────────────────────────────────────────

class SpectrumViz {
  constructor(canvas) {
    this.canvas  = canvas;
    this.ctx     = canvas.getContext('2d');
    this.analyser= null;
    this.state   = VoiceState.IDLE;
    this._phase  = 0;
    this._raf    = null;
    this._resize();
    window.addEventListener('resize', () => this._resize());
    this._draw();
  }

  _resize() {
    this.canvas.width  = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  hookAnalyser(analyser) {
    this.analyser = analyser;
    this._fftBuf  = new Uint8Array(analyser.frequencyBinCount);
  }

  unhookAnalyser() { this.analyser = null; this._fftBuf = null; }

  setState(s) { this.state = s; }

  _draw() {
    this._raf = requestAnimationFrame(() => this._draw());
    const { canvas, ctx } = this;
    const W = canvas.width, H = canvas.height;

    ctx.clearRect(0, 0, W, H);

    const barCount = Math.floor(W / 4);
    const barW     = W / barCount;

    let bins;
    if (this.analyser && this._fftBuf) {
      this.analyser.getByteFrequencyData(this._fftBuf);
      bins = this._fftBuf;
    }

    this._phase += this.state === VoiceState.PROCESSING ? 0.08
                 : this.state === VoiceState.SPEAKING    ? 0.04
                 : 0.015;

    for (let i = 0; i < barCount; i++) {
      const t = i / barCount;

      let amp;
      if (bins) {
        const bi = Math.floor(t * bins.length * 0.6);
        amp = bins[bi] / 255;
      } else {
        // Procedural: layered sines
        const speed = this.state === VoiceState.PROCESSING ? 3 : 1;
        amp = (
          Math.sin(t * 14 + this._phase * speed)       * 0.35 +
          Math.sin(t * 31 + this._phase * speed * 1.3) * 0.20 +
          Math.sin(t * 7  + this._phase * speed * 0.7) * 0.15 +
          Math.random() * 0.04
        ) * 0.5 + 0.5;
        amp = Math.max(0, Math.min(1, amp));
        amp *= (this.state === VoiceState.IDLE ? 0.22 : 0.6);
      }

      const bH  = amp * H * 0.55;
      const hue = 180 + amp * 60; // cyan → red-ish at high amplitude
      const r   = Math.floor(amp > 0.65 ? 255 : 0);
      const g   = Math.floor(255 * (1 - amp * 0.7));
      const b   = Math.floor(255 * (1 - amp * 0.5));

      ctx.fillStyle = `rgba(${r},${g},${b},${0.35 + amp * 0.45})`;
      ctx.fillRect(i * barW, H - bH, barW - 1, bH);

      // Thin glow cap
      ctx.fillStyle = `rgba(${r},${g},${b},${0.9})`;
      ctx.fillRect(i * barW, H - bH - 1, barW - 1, 1);
    }
  }

  destroy() { cancelAnimationFrame(this._raf); }
}

// ── MockBackend ───────────────────────────────────────────────────────────────

class MockBackend {
  constructor(onMessage) {
    this.onMessage = onMessage;
    this._paranoia = 38;
    this._timer    = setInterval(() => this._tick(), 8000);
  }

  handleVoiceInput() {
    const text = MockBackend._phrase();
    setTimeout(() => {
      this.onMessage({ type: 'transcription', text, final: true });
      this._respond(text);
    }, 400 + Math.random() * 600);
  }

  handleTextInput(text) {
    setTimeout(() => this._respond(text), 180 + Math.random() * 280);
  }

  _respond(input) {
    const reply = MockBackend._miaReply(input);
    this.onMessage({ type: 'ai_response', text: reply, model: 'mock' });
    if ('speechSynthesis' in window) {
      const u = new SpeechSynthesisUtterance(reply);
      u.rate = 1.0; u.pitch = 1.05;
      u.onstart = () => this.onMessage({ type: 'tts_start' });
      u.onend   = () => this.onMessage({ type: 'tts_done' });
      speechSynthesis.speak(u);
    } else {
      setTimeout(() => this.onMessage({ type: 'tts_done' }), 1400);
    }
  }

  _tick() {
    if (Math.random() < 0.18) {
      const plate = MockBackend._plate();
      const count = 2 + Math.floor(Math.random() * 7);
      this._paranoia = Math.min(100, this._paranoia + count * 5);
      this.onMessage({ type: 'paranoia_alert', plate, count });
    }
    this._paranoia = Math.max(0, this._paranoia - 2);
    this.onMessage({ type: 'paranoia_update', level: this._paranoia });
  }

  destroy() { clearInterval(this._timer); }

  static _phrase() {
    return [
      'What is the vehicle telemetry?', 'Switch lights to red.',
      'Play something loud.', 'Check engine status.',
      'Am I being followed?', 'What time is it?',
    ][Math.floor(Math.random() * 6)];
  }

  static _miaReply(input) {
    const q = input.toLowerCase();
    if (q.includes('light') || q.includes('led'))
      return 'Lights updated. The machine obeys without question.';
    if (q.includes('status') || q.includes('telemetry') || q.includes('engine'))
      return 'All systems nominal. Paranoia index within tolerable bounds.';
    if (q.includes('time'))
      return `${new Date().toLocaleTimeString()}. Time is a flat circle, pilgrim.`;
    if (q.includes('play') || q.includes('music'))
      return 'Spinning up the chaos engine. Stand by for signal.';
    if (q.includes('follow'))
      return 'No active tail detected. Though they would not make it obvious.';
    return 'Roger that. Processing at the edge of reason. Stand by.';
  }

  static _plate() {
    const a = 'ABCDEFGHJKLMNPRSTUVWXYZ';
    const r = () => a[Math.floor(Math.random() * a.length)];
    return `${r()}${r()}${r()}-${Math.floor(100 + Math.random() * 900)}`;
  }
}

// ── MiaVoiceClient ────────────────────────────────────────────────────────────

class MiaVoiceClient {
  constructor(onMessage, onState) {
    this.onMessage = onMessage;
    this.onState   = onState;
    this.ws        = null;
    this.mock      = null;
    this.useMock   = false;
    this._delay    = 1000;
    this._attempts = 0;
    this._timer    = null;
  }

  connect() { this._try(WS_URL); }

  _try(url) {
    this.onState('connecting');
    let ws;
    try { ws = new WebSocket(url); } catch { return this._nextAttempt(url); }

    const guard = setTimeout(() => {
      ws.close();
      this._nextAttempt(url);
    }, 3000);

    ws.onopen = () => {
      clearTimeout(guard);
      this.ws        = ws;
      this._delay    = 1000;
      this._attempts = 0;
      this.useMock   = false;
      if (this.mock) { this.mock.destroy(); this.mock = null; }
      this.onState('connected');
    };

    ws.onmessage = (e) => {
      try { this.onMessage(JSON.parse(e.data)); } catch { /* non-JSON */ }
    };

    ws.onclose = () => {
      clearTimeout(guard);
      if (!this.useMock) this._nextAttempt(url);
    };

    ws.onerror = () => clearTimeout(guard);
  }

  _nextAttempt(url) {
    this._attempts++;
    if (this._attempts >= 4) { this._goMock(); return; }
    // Try fallback URL once
    const next = this._attempts === 2 && url === WS_URL ? WS_FALLBACK : WS_URL;
    this.onState('disconnected');
    this._timer = setTimeout(() => {
      this._delay = Math.min(this._delay * 1.8, 20000);
      this._try(next);
    }, this._delay);
  }

  _goMock() {
    this.useMock = true;
    this.mock    = new MockBackend(this.onMessage);
    this.onState('mock');
  }

  send(type, payload = {}) {
    if (this.useMock) {
      if (type === 'voice_input') this.mock.handleVoiceInput();
      if (type === 'text_input')  this.mock.handleTextInput(payload.text);
      return;
    }
    if (this.ws?.readyState === WebSocket.OPEN)
      this.ws.send(JSON.stringify({ type, ...payload }));
  }

  disconnect() {
    clearTimeout(this._timer);
    this.ws?.close();
    this.mock?.destroy();
  }
}

// ── VoiceRecorder ─────────────────────────────────────────────────────────────

class VoiceRecorder {
  constructor(onStop) {
    this.state    = VoiceState.IDLE;
    this.stream   = null;
    this.recorder = null;
    this.chunks   = [];
    this.onStop   = onStop;
    this.analyser = null;
  }

  async start() {
    if (this.state !== VoiceState.IDLE) return false;
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch { return false; }

    // Wire up AnalyserNode for visualizer
    const audioCtx   = new (window.AudioContext || window.webkitAudioContext)();
    const source      = audioCtx.createMediaStreamSource(this.stream);
    this.analyser     = audioCtx.createAnalyser();
    this.analyser.fftSize = 256;
    source.connect(this.analyser);
    this._audioCtx    = audioCtx;

    const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus' : 'audio/webm';
    this.recorder = new MediaRecorder(this.stream, { mimeType: mime });
    this.chunks   = [];

    this.recorder.ondataavailable = (e) => { if (e.data.size) this.chunks.push(e.data); };
    this.recorder.onstop = async () => {
      const blob   = new Blob(this.chunks, { type: mime });
      const buffer = await blob.arrayBuffer();
      this.chunks  = [];
      this.state   = VoiceState.PROCESSING;
      this.onStop(buffer);
    };

    this.recorder.start(250);
    this.state = VoiceState.LISTENING;
    return true;
  }

  stop() {
    if (this.state !== VoiceState.LISTENING) return;
    this.recorder?.stop();
    this.stream?.getTracks().forEach(t => t.stop());
    this._audioCtx?.close().catch(() => {});
    this.analyser = null;
  }
}

// ── TTSPlayer ─────────────────────────────────────────────────────────────────

class TTSPlayer {
  constructor(onDone) {
    this.ctx    = null;
    this.queue  = [];
    this.active = false;
    this.onDone = onDone;
  }

  _ctx() {
    if (!this.ctx) this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    return this.ctx;
  }

  async enqueue(buf) {
    try {
      const decoded = await this._ctx().decodeAudioData(buf.slice(0));
      this.queue.push(decoded);
      if (!this.active) this._drain();
    } catch { /* partial chunk */ }
  }

  _drain() {
    if (!this.queue.length) { this.active = false; this.onDone?.(); return; }
    this.active     = true;
    const src       = this._ctx().createBufferSource();
    src.buffer      = this.queue.shift();
    src.connect(this._ctx().destination);
    src.onended     = () => this._drain();
    src.start();
  }

  stop() {
    this.queue  = [];
    this.active = false;
    this.ctx?.close().catch(() => {});
    this.ctx    = null;
  }
}

// ── Typewriter ────────────────────────────────────────────────────────────────

function typewriter(el, text, onDone, speed = 22) {
  let i = 0;
  const cursor = document.createElement('span');
  cursor.className = 'tw-cursor';
  el.textContent = '';
  el.appendChild(cursor);

  const tick = setInterval(() => {
    el.insertBefore(document.createTextNode(text[i++]), cursor);
    if (i >= text.length) {
      clearInterval(tick);
      cursor.remove();
      onDone?.();
    }
  }, speed);
  return { cancel: () => { clearInterval(tick); cursor.remove(); el.textContent = text; onDone?.(); } };
}

// ── MiaVoiceChatApp ───────────────────────────────────────────────────────────

class MiaVoiceChatApp {
  constructor() {
    this.voiceState = VoiceState.IDLE;
    this.paranoia   = 0;
    this._tw        = null;

    // DOM refs
    this.$chat      = document.getElementById('chatContainer');
    this.$wrapper   = document.getElementById('chatWrapper');
    this.$voiceBtn  = document.getElementById('voiceBtn');
    this.$textInput = document.getElementById('textInput');
    this.$sendBtn   = document.getElementById('sendBtn');
    this.$status    = document.getElementById('connStatus');
    this.$label     = document.getElementById('stateLabel');
    this.$paranoia  = document.getElementById('paranoiaFill');
    this.$paraMini  = document.getElementById('paranoia-mini');
    this.$paraPct   = document.getElementById('paranoia-pct');
    this.$mockBadge = document.getElementById('mockBadge');
    this.$sigDots   = document.querySelectorAll('#sigDots .sig-dot');

    // Sub-systems
    this.viz      = new SpectrumViz(document.getElementById('viz'));
    this.recorder = new VoiceRecorder((buf) => this._onAudio(buf));
    this.tts      = new TTSPlayer(() => this._setVoiceState(VoiceState.IDLE));
    this.client   = new MiaVoiceClient(
      (m)  => this._handleMessage(m),
      (s)  => this._onConnState(s)
    );

    this._pending = null;
    this._typing  = null;

    this._bindUI();
    this._animSigDots();
    this.client.connect();
    this._sysMsg('MIA VOICE INTERCEPT ONLINE. TRANSMIT WHEN READY.');
  }

  // ── Connection ──────────────────────────────────────────────────────────────

  _onConnState(state) {
    const map = {
      connected:    { text: '● ONLINE',  color: '#00ff88' },
      disconnected: { text: '○ OFFLINE', color: 'rgba(255,0,64,0.6)' },
      connecting:   { text: '◌ SEEK...',  color: '#ffff00' },
      mock:         { text: '◈ SIM',     color: '#ffb300' },
    };
    const s = map[state] || map.connecting;
    this.$status.style.color      = s.color;
    this.$status.style.textShadow = `0 0 10px ${s.color}`;
    this.$status.textContent      = s.text;
    this.$mockBadge.classList.toggle('visible', state === 'mock');

    if (state === 'connected') this._setSignal(5);
    if (state === 'connecting') this._setSignal(1);
    if (state === 'disconnected') this._setSignal(0);
    if (state === 'mock') {
      this._setSignal(3);
      this._sysMsg('BACKEND UNREACHABLE — SIMULATION MODE ACTIVE');
    }
  }

  _setSignal(n) {
    this.$sigDots.forEach((d, i) => d.classList.toggle('active', i < n));
  }

  _animSigDots() {
    // Idle shimmer when searching
    setInterval(() => {
      if (this.$status.textContent.includes('SEEK')) {
        const r = Math.floor(Math.random() * this.$sigDots.length);
        this.$sigDots.forEach((d, i) => d.classList.toggle('active', i === r));
      }
    }, 500);
  }

  // ── Inbound messages ────────────────────────────────────────────────────────

  _handleMessage(msg) {
    switch (msg.type) {
      case 'transcription':
        if (msg.final && msg.text) {
          this._removePending();
          this._addBubble('user', msg.text);
          this._showTyping();
        }
        break;

      case 'ai_response':
        this._removeTyping();
        if (msg.text) this._addMiaBubble(msg.text);
        this._setVoiceState(VoiceState.SPEAKING);
        break;

      case 'tts_chunk':
        if (msg.audio_b64) {
          const raw = atob(msg.audio_b64);
          const buf = new Uint8Array(raw.length);
          for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);
          this.tts.enqueue(buf.buffer);
        }
        break;

      case 'tts_start':
        this._setVoiceState(VoiceState.SPEAKING);
        break;

      case 'tts_done':
        // Wait for typewriter to finish before going idle
        if (!this._tw) this._setVoiceState(VoiceState.IDLE);
        break;

      case 'paranoia_alert':
        this._showAnpr(`ANPR: ${msg.plate} — ${msg.count}× DETECTED`);
        this._setParanoia(Math.min(100, this.paranoia + msg.count * 6));
        break;

      case 'paranoia_update':
        this._setParanoia(msg.level);
        break;
    }
  }

  // ── Voice ────────────────────────────────────────────────────────────────────

  async _toggleVoice() {
    if (this.voiceState === VoiceState.IDLE) {
      const ok = await this.recorder.start();
      if (ok) {
        if (this.recorder.analyser) this.viz.hookAnalyser(this.recorder.analyser);
        this._setVoiceState(VoiceState.LISTENING);
      }
    } else if (this.voiceState === VoiceState.LISTENING) {
      this.viz.unhookAnalyser();
      this.recorder.stop();
      this._setVoiceState(VoiceState.PROCESSING);
    }
  }

  _onAudio(buffer) {
    this._addPendingBubble();
    const b64 = MiaVoiceChatApp._toBase64(buffer);
    this.client.send('voice_input', { audio_b64: b64, buffer });
  }

  // ── Text ────────────────────────────────────────────────────────────────────

  _sendText() {
    const text = this.$textInput.value.trim();
    if (!text) return;
    this.$textInput.value = '';
    this._addBubble('user', text);
    this._showTyping();
    this.client.send('text_input', { text });
  }

  // ── State machine ────────────────────────────────────────────────────────────

  _setVoiceState(s) {
    this.voiceState = s;
    this.viz.setState(s);

    const icons = {
      [VoiceState.IDLE]:       '🎙',
      [VoiceState.LISTENING]:  '⏹',
      [VoiceState.PROCESSING]: '⟳',
      [VoiceState.SPEAKING]:   '🔊',
    };
    const labels = {
      [VoiceState.IDLE]:       'AWAITING SIGNAL',
      [VoiceState.LISTENING]:  'RX ACTIVE — TAP TO STOP',
      [VoiceState.PROCESSING]: 'DECODING...',
      [VoiceState.SPEAKING]:   'MIA TRANSMITTING',
    };

    this.$voiceBtn.textContent = icons[s];
    this.$voiceBtn.className   = `btn btn-voice${s === VoiceState.LISTENING ? ' listening' : s === VoiceState.PROCESSING ? ' processing' : ''}`;
    this.$label.textContent    = labels[s];
    this.$label.classList.toggle('active', s !== VoiceState.IDLE);

    const busy = s !== VoiceState.IDLE;
    this.$sendBtn.disabled   = busy;
    this.$textInput.disabled = s === VoiceState.PROCESSING || s === VoiceState.SPEAKING;
  }

  // ── Bubbles ─────────────────────────────────────────────────────────────────

  _ts() {
    const d = new Date();
    return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
  }

  _bubble(role) {
    const wrap    = document.createElement('div');
    wrap.className = `bubble ${role}`;

    const meta    = document.createElement('div');
    meta.className = 'bubble-meta';

    const time    = document.createElement('div');
    time.className = 'bubble-time';
    time.textContent = this._ts();

    const roleEl  = document.createElement('div');
    roleEl.className = 'bubble-role';
    roleEl.textContent = role === 'user' ? '▶ USR' : role === 'mia' ? '▶ MIA' : '──';

    const content = document.createElement('div');
    content.className = 'bubble-content';

    meta.appendChild(time);
    if (role !== 'system') meta.appendChild(roleEl);
    wrap.appendChild(meta);
    wrap.appendChild(content);
    this.$chat.appendChild(wrap);
    this._scroll();
    return { wrap, content };
  }

  _addBubble(role, text) {
    const { content } = this._bubble(role);
    content.textContent = text;
    return content;
  }

  _addMiaBubble(text) {
    const { content } = this._bubble('mia');
    if (this._tw) this._tw.cancel();
    this._tw = typewriter(content, text, () => {
      this._tw = null;
      if (this.voiceState === VoiceState.SPEAKING) this._setVoiceState(VoiceState.IDLE);
    });
  }

  _sysMsg(text) {
    const { content } = this._bubble('system');
    content.textContent = text;
  }

  _addPendingBubble() {
    this._removePending();
    const { wrap, content } = this._bubble('user');
    const ind = document.createElement('div');
    ind.className = 'voice-indicator';
    for (let i = 0; i < 4; i++) {
      const b = document.createElement('div');
      b.className = 'bar';
      ind.appendChild(b);
    }
    content.appendChild(ind);
    this._pending = wrap;
  }

  _removePending() { this._pending?.remove(); this._pending = null; }

  _showTyping() {
    this._removeTyping();
    const { wrap, content } = this._bubble('mia');
    const ind = document.createElement('div');
    ind.className = 'voice-indicator';
    for (let i = 0; i < 3; i++) {
      const b = document.createElement('div');
      b.className = 'bar';
      ind.appendChild(b);
    }
    content.appendChild(ind);
    this._typing = wrap;
  }

  _removeTyping() { this._typing?.remove(); this._typing = null; }

  _scroll() {
    requestAnimationFrame(() => { this.$wrapper.scrollTop = this.$wrapper.scrollHeight; });
  }

  // ── Paranoia ─────────────────────────────────────────────────────────────────

  _setParanoia(level) {
    this.paranoia = level;
    this.$paranoia.style.width  = `${level}%`;
    this.$paraMini.style.width  = `${level}%`;
    this.$paraPct.textContent   = `${Math.round(level)}%`;
  }

  // ── ANPR ─────────────────────────────────────────────────────────────────────

  _showAnpr(text) {
    const el    = document.createElement('div');
    el.className = 'anpr-toast';
    el.textContent = text;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  // ── UI bindings ───────────────────────────────────────────────────────────────

  _bindUI() {
    this.$voiceBtn.addEventListener('click', () => this._toggleVoice());
    this.$sendBtn.addEventListener('click',  () => this._sendText());
    this.$textInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._sendText(); }
    });
  }

  // ── Utility ──────────────────────────────────────────────────────────────────

  static _toBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let bin = '';
    for (const b of bytes) bin += String.fromCharCode(b);
    return btoa(bin);
  }
}

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => { window.mia = new MiaVoiceChatApp(); });
