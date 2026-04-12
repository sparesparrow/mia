#!/usr/bin/env python3
"""
server.py — FastAPI WebSocket backend pro web UI simulace
Spuštění: python server.py  →  http://localhost:8432
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent))
from rezervace_dual import (
    AudioBus, run_espeak_mode, run_hybrid_mode,
    _cleanup_all_agents, _agents_to_cleanup,
)

app = FastAPI()
_sim_task: asyncio.Task | None = None
_clients: list[WebSocket] = []


async def broadcast(msg: dict):
    dead = []
    for ws in _clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.remove(ws)


class BroadcastBus(AudioBus):
    """AudioBus that emits events to WS clients."""
    async def play(self, pcm48, who: str):
        await broadcast({"type": "speaking", "who": who})
        await super().play(pcm48, who)
        await broadcast({"type": "silent"})


# Patch print to also broadcast transcript lines
_orig_print = print

def _ws_print(*args, **kwargs):
    line = " ".join(str(a) for a in args)
    _orig_print(*args, **kwargs)
    # Strip ANSI
    import re
    clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
    if "[CALLER]" in clean or "[RECEPCE]" in clean:
        role = "caller" if "[CALLER]" in clean else "target"
        text = clean.split("]", 1)[-1].strip()
        asyncio.create_task(broadcast({"type": "line", "role": role, "text": text}))

import builtins
builtins.print = _ws_print


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.append(ws)
    try:
        while True:
            data = await ws.receive_json()
            cmd = data.get("cmd")

            if cmd == "start":
                global _sim_task
                if _sim_task and not _sim_task.done():
                    await ws.send_json({"type": "error", "text": "Simulace již běží"})
                    continue
                mode = data.get("mode", "espeak")
                bus = BroadcastBus()

                async def _run():
                    await broadcast({"type": "status", "status": "running", "mode": mode})
                    try:
                        if mode == "hybrid":
                            await run_hybrid_mode(bus)
                        else:
                            await run_espeak_mode(bus)
                    except Exception as e:
                        await broadcast({"type": "error", "text": str(e)})
                    finally:
                        _cleanup_all_agents()
                        await broadcast({"type": "status", "status": "stopped"})

                _sim_task = asyncio.create_task(_run())

            elif cmd == "stop":
                if _sim_task and not _sim_task.done():
                    _sim_task.cancel()
                _cleanup_all_agents()
                await broadcast({"type": "status", "status": "stopped"})

    except WebSocketDisconnect:
        _clients.remove(ws)


HTML = """<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>Chatka Booking Simulation</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0a0a0f; color: #e0e0e0; font-family: 'Courier New', monospace;
         display: flex; flex-direction: column; height: 100vh; }

  header { padding: 14px 20px; border-bottom: 1px solid #1e2a3a;
           display: flex; align-items: center; gap: 16px; background: #080810; }
  .logo { font-size: 1.1rem; color: #00e5ff; letter-spacing: 2px; font-weight: bold; }
  .status-dot { width: 10px; height: 10px; border-radius: 50%; background: #444; }
  .status-dot.running { background: #00e5ff; box-shadow: 0 0 8px #00e5ff; animation: pulse 1.5s infinite; }
  .status-dot.stopped { background: #ff1744; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

  .controls { padding: 12px 20px; display: flex; gap: 10px; align-items: center;
              border-bottom: 1px solid #1e2a3a; background: #0c0c18; flex-shrink: 0; }
  select { background: #131320; color: #aaa; border: 1px solid #2a3a4a; padding: 6px 10px;
           border-radius: 4px; font-family: inherit; font-size: 0.85rem; }
  button { padding: 7px 18px; border: none; border-radius: 4px; cursor: pointer;
           font-family: inherit; font-size: 0.85rem; font-weight: bold; letter-spacing: 1px; }
  #btnStart { background: #00e5ff; color: #000; }
  #btnStop  { background: #ff1744; color: #fff; }
  #btnClear { background: #222; color: #888; border: 1px solid #333; }
  .status-text { font-size: 0.8rem; color: #555; margin-left: auto; }

  .transcript { flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 8px; }
  .line { display: grid; grid-template-columns: 80px 1fr; gap: 10px; font-size: 0.88rem;
          padding: 6px 0; border-bottom: 1px solid #111; animation: fadein .2s; }
  @keyframes fadein { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:none} }
  .role { font-size: 0.75rem; font-weight: bold; letter-spacing: 1px; padding-top: 2px; }
  .role.caller { color: #00e5ff; }
  .role.target { color: #69ff47; }
  .text.caller { color: #c8f0ff; }
  .text.target { color: #d0ffcc; }

  .speaking-bar { height: 3px; background: transparent; flex-shrink: 0; transition: background .1s; }
  .speaking-bar.caller { background: linear-gradient(90deg,#00e5ff,transparent); }
  .speaking-bar.target { background: linear-gradient(90deg,#69ff47,transparent); }

  footer { padding: 8px 20px; border-top: 1px solid #1e2a3a; font-size: 0.75rem; color: #333;
           background: #080810; display: flex; gap: 20px; flex-shrink: 0; }
</style>
</head>
<body>
<header>
  <span class="logo">CHATKA//SIM</span>
  <div class="status-dot" id="dot"></div>
  <span id="statusLabel" style="font-size:.8rem;color:#555">OFFLINE</span>
</header>

<div class="controls">
  <select id="modeSelect">
    <option value="espeak">ESPEAK — nulové náklady</option>
    <option value="hybrid" selected>HYBRID — 1× ElevenLabs</option>
  </select>
  <button id="btnStart" onclick="start()">▶ START</button>
  <button id="btnStop"  onclick="stop()">■ STOP</button>
  <button id="btnClear" onclick="clearLog()">✕ CLEAR</button>
  <span class="status-text" id="turnInfo"></span>
</div>

<div class="speaking-bar" id="speakingBar"></div>

<div class="transcript" id="transcript">
  <div class="line" style="opacity:.4">
    <span class="role" style="color:#333">SYS</span>
    <span class="text" style="color:#333">Připojen. Stiskni START pro spuštění simulace.</span>
  </div>
</div>

<footer>
  <span>CALLER: <span id="callerCount">0</span></span>
  <span>RECEPCE: <span id="targetCount">0</span></span>
  <span id="modeLabel">—</span>
</footer>

<script>
let ws, callerN = 0, targetN = 0;

function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = e => handle(JSON.parse(e.data));
  ws.onclose = () => { setStatus('stopped'); setTimeout(connect, 2000); };
}

function handle(msg) {
  if (msg.type === 'status') {
    setStatus(msg.status);
    if (msg.mode) document.getElementById('modeLabel').textContent = msg.mode.toUpperCase();
  } else if (msg.type === 'line') {
    addLine(msg.role, msg.text);
  } else if (msg.type === 'speaking') {
    document.getElementById('speakingBar').className = 'speaking-bar ' + msg.who;
    document.getElementById('turnInfo').textContent = msg.who === 'caller' ? '▶ CALLER mluví' : '▶ RECEPCE mluví';
  } else if (msg.type === 'silent') {
    document.getElementById('speakingBar').className = 'speaking-bar';
    document.getElementById('turnInfo').textContent = '';
  } else if (msg.type === 'error') {
    addLine('sys', '⚠ ' + msg.text);
  }
}

function addLine(role, text) {
  const t = document.getElementById('transcript');
  const div = document.createElement('div');
  div.className = 'line';
  const label = role === 'caller' ? 'CALLER' : role === 'target' ? 'RECEPCE' : 'SYS';
  div.innerHTML = `<span class="role ${role}">${label}</span><span class="text ${role}">${text}</span>`;
  t.appendChild(div);
  t.scrollTop = t.scrollHeight;
  if (role === 'caller') document.getElementById('callerCount').textContent = ++callerN;
  if (role === 'target') document.getElementById('targetCount').textContent = ++targetN;
}

function setStatus(s) {
  const dot = document.getElementById('dot');
  dot.className = 'status-dot ' + s;
  document.getElementById('statusLabel').textContent = s.toUpperCase();
}

function start() {
  ws.send(JSON.stringify({ cmd: 'start', mode: document.getElementById('modeSelect').value }));
  callerN = targetN = 0;
  document.getElementById('callerCount').textContent = '0';
  document.getElementById('targetCount').textContent = '0';
}

function stop() { ws.send(JSON.stringify({ cmd: 'stop' })); }
function clearLog() {
  document.getElementById('transcript').innerHTML = '';
  callerN = targetN = 0;
  document.getElementById('callerCount').textContent = '0';
  document.getElementById('targetCount').textContent = '0';
}

connect();
</script>
</body>
</html>"""


@app.get("/")
async def index():
    return HTMLResponse(HTML)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8432, log_level="warning")
