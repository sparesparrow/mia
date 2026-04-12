#!/usr/bin/env python3
"""
webhook.py — volitelný FastAPI server pro příjem výsledků hovoru od ElevenLabs.

Spuštění:
    pip install fastapi uvicorn
    python webhook.py

Pak nastav v config.py:
    WEBHOOK_BASE_URL = "https://<tvoje-verejna-url>"   # ngrok / cloudflare tunnel

ElevenLabs pošle POST na /result po skončení hovoru s daty o přepisu a metadatech.
"""

import json
import sys
from pathlib import Path

try:
    from fastapi import FastAPI, Request
    import uvicorn
except ImportError:
    sys.exit("pip install fastapi uvicorn")

try:
    from config import RESULT_FILE, WEBHOOK_PORT
except ImportError:
    RESULT_FILE = "/tmp/chatka-booking-result.json"
    WEBHOOK_PORT = 8765

app = FastAPI(title="Chatka Booking Webhook")


@app.post("/result")
async def receive_result(request: Request):
    data = await request.json()
    Path(RESULT_FILE).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    transcript = data.get("transcript", [])
    print("\n── Hovor dokončen ──")
    for turn in transcript:
        role = "AGENT  " if turn.get("role") == "agent" else "RECEPCE"
        print(f"  [{role}] {turn.get('message', '')}")
    print(f"\nVýsledek: {data.get('status', '?')}")
    print(f"Uloženo:  {RESULT_FILE}")
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=WEBHOOK_PORT)
