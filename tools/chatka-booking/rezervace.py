#!/usr/bin/env python3
"""
chatka-booking / rezervace.py
─────────────────────────────
Vytvoří ElevenLabs Conversational AI agenta a zavolá na telefonní číslo
v ČR přes Twilio. Agent mluví česky a pokusí se rezervovat chatku.

Požadavky:
    pip install elevenlabs twilio requests

Nastavení:
    Edituj config.py — doplň API klíče a telefonní čísla.

Spuštění:
    python rezervace.py [--dry-run]   # dry-run = jen vypíše konfiguraci agenta
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

try:
    from config import (
        BOOKING_DATE, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
        GUEST_COUNT, RESULT_FILE, TARGET_PHONE, TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, WEBHOOK_BASE_URL,
    )
except ImportError:
    sys.exit("Chyba: nemohu importovat config.py — spouštěj ze složky tools/chatka-booking/")


# ── System prompt pro agenta ───────────────────────────────────────────────────

SYSTEM_PROMPT = f"""
Jsi hlasový asistent pracující pro zákazníka, který hledá ubytování v přírodě.
Zavoláš do ubytovacího zařízení v České republice a pokusíš se rezervovat chatku.

=== CÍLE HOVORU (v tomto pořadí) ===
1. Pozdrav a krátce se představ (řekni, že jsi AI asistent).
2. Zeptej se, zda mají volnou chatku (nebo chatky) na datum {BOOKING_DATE}.
3. Pokud ano, zjisti:
   - přibližnou cenu za noc nebo pobyt
   - minimální délku pobytu
   - kapacitu (kolik osob, předpokládáme {GUEST_COUNT} dospělých)
   - způsob potvrzení rezervace (e-mail, záloha, ...)
   - storno podmínky
4. Pokud lze rezervaci potvrdit po telefonu nebo e-mailem, požádej o předběžné zablokování termínu.
5. Pokud termín není volný, zeptej se na nejbližší alternativu.
6. Na konci hovoru shrň výsledek.

=== PRAVIDLA ===
- Mluv výhradně česky. Buď zdvořilý, přirozený, stručný.
- Pokud se tě zeptají, zda jsi člověk, řekni pravdu: jsi AI asistent.
- Nepotvrzuj závaznou rezervaci bez potvrzení od zákazníka.
- Pokud recepční potřebuje informace (jméno, e-mail, tel.), řekni, že zákazník zavolá zpět nebo napíše e-mail.
- Pokud linka není dostupná nebo hovor nelze dokončit, ukonči slušně.
- Limit hovoru: 5 minut. Pokud nemáš výsledek, přibliž závěr.

=== VÝSTUP PO HOVORU ===
Na konci hovoru interně shrň tato pole (nevyslovuj je, jen zaznamenej):
  status: [rezervovano|nedostupno|nutno_zavolat|bez_odpovedi]
  dostupnost: [ano|ne|neznamo]
  cena_per_night: [číslo nebo null]
  mena: [CZK|EUR|null]
  min_pobyt_noci: [číslo nebo null]
  kapacita: [číslo nebo null]
  zpusob_potvrzeni: [text nebo null]
  storno: [text nebo null]
  dalsi_kroky: [text]
  kontakt: [text nebo null]
""".strip()

FIRST_MESSAGE = (
    f"Dobrý den, volám ohledně možnosti rezervace chatky nebo ubytování "
    f"na datum {BOOKING_DATE}. Jsem AI asistent — mohl bych si ověřit dostupnost?"
)


# ── ElevenLabs API helper ──────────────────────────────────────────────────────

EL_BASE = "https://api.elevenlabs.io/v1"

def el_headers() -> dict:
    return {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}


def create_agent() -> str:
    """Vytvoří nového konverzačního agenta a vrátí jeho ID."""
    payload = {
        "name": f"ChatkaBooking-{BOOKING_DATE}",
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": SYSTEM_PROMPT,
                    "llm": "gpt-4o",
                    "temperature": 0.4,
                    "max_tokens": 1024,
                },
                "first_message": FIRST_MESSAGE,
                "language": "cs",
            },
            "tts": {
                "voice_id": ELEVENLABS_VOICE_ID,
                "model_id": "eleven_turbo_v2_5",
                "optimize_streaming_latency": 3,
            },
            "asr": {
                "quality": "high",
                "provider": "elevenlabs",
                "user_input_audio_format": "ulaw_8000",
            },
            "turn": {
                "turn_timeout": 10,
                "silence_end_call_timeout": 20,
            },
        },
        "platform_settings": {
            "auth": {"enable_auth": False},
        },
    }
    r = requests.post(f"{EL_BASE}/convai/agents/create", headers=el_headers(), json=payload, timeout=30)
    if not r.ok:
        sys.exit(f"ElevenLabs create agent chyba {r.status_code}: {r.text}")
    agent_id = r.json()["agent_id"]
    print(f"[ElevenLabs] Agent vytvořen: {agent_id}")
    return agent_id


def delete_agent(agent_id: str) -> None:
    requests.delete(f"{EL_BASE}/convai/agents/{agent_id}", headers=el_headers(), timeout=10)
    print(f"[ElevenLabs] Agent smazán: {agent_id}")


def get_or_register_phone_number() -> str:
    """Vrátí phone_number_id pro TWILIO_FROM_NUMBER — zaregistruje ho pokud neexistuje."""
    r = requests.get(f"{EL_BASE}/convai/phone-numbers", headers=el_headers(), timeout=15)
    if r.ok:
        phone_list = r.json() if isinstance(r.json(), list) else r.json().get("phone_numbers", [])
        for pn in phone_list:
            if pn.get("phone_number") == TWILIO_FROM_NUMBER:
                pid = pn["phone_number_id"]
                print(f"[ElevenLabs] Číslo již registrováno: {TWILIO_FROM_NUMBER} → {pid}")
                return pid

    # Registrace Twilio čísla v ElevenLabs
    print(f"[ElevenLabs] Registruji číslo {TWILIO_FROM_NUMBER}...")
    r = requests.post(
        f"{EL_BASE}/convai/phone-numbers",
        headers=el_headers(),
        json={
            "phone_number": TWILIO_FROM_NUMBER,
            "label": "chatka-booking",
            "twilio_account_sid": TWILIO_ACCOUNT_SID,
            "twilio_auth_token": TWILIO_AUTH_TOKEN,
        },
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"ElevenLabs registrace čísla chyba {r.status_code}: {r.text}")
    pid = r.json()["phone_number_id"]
    print(f"[ElevenLabs] Číslo zaregistrováno: {pid}")
    return pid


def initiate_outbound_call(agent_id: str, phone_number_id: str) -> dict:
    """Spustí odchozí hovor přes ElevenLabs (Twilio v pozadí)."""
    r = requests.post(
        f"{EL_BASE}/convai/twilio/outbound-call",
        headers=el_headers(),
        json={
            "agent_id": agent_id,
            "agent_phone_number_id": phone_number_id,
            "to_number": TARGET_PHONE,
        },
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"ElevenLabs outbound call chyba {r.status_code}: {r.text}")
    data = r.json()
    print(f"[Call] Zahájen: call_sid={data.get('call_sid', '?')}")
    return data


def poll_conversation(agent_id: str, call_sid: str, timeout_s: int = 360) -> dict | None:
    """Čeká na dokončení hovoru a vrátí transcript."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = requests.get(f"{EL_BASE}/convai/conversations", headers=el_headers(), timeout=10)
        if r.ok:
            for conv in r.json().get("conversations", []):
                if conv.get("call_sid") == call_sid or conv.get("agent_id") == agent_id:
                    if conv.get("status") in ("done", "failed", "error"):
                        # Získej detaily
                        conv_id = conv["conversation_id"]
                        dr = requests.get(f"{EL_BASE}/convai/conversations/{conv_id}", headers=el_headers(), timeout=10)
                        return dr.json() if dr.ok else conv
        time.sleep(10)
        print(".", end="", flush=True)
    print()
    return None


# ── Výstup výsledků ────────────────────────────────────────────────────────────

def print_result(data: dict) -> None:
    print("\n" + "═" * 60)
    print("VÝSLEDEK HOVORU")
    print("═" * 60)

    transcript = data.get("transcript", [])
    if transcript:
        print("\n── Přepis hovoru ──")
        for turn in transcript:
            role = "AGENT" if turn.get("role") == "agent" else "RECEPCE"
            print(f"  [{role}] {turn.get('message', '')}")

    metadata = data.get("metadata", {})
    if metadata:
        print("\n── Metadata ──")
        print(json.dumps(metadata, ensure_ascii=False, indent=2))

    print(f"\n── Trvání: {data.get('metadata', {}).get('call_duration_secs', '?')}s")
    print(f"   Status: {data.get('status', '?')}")

    Path(RESULT_FILE).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nÚplný výsledek uložen: {RESULT_FILE}")


# ── Dry-run ────────────────────────────────────────────────────────────────────

def dry_run() -> None:
    print("═" * 60)
    print("DRY RUN — konfigurace agenta (hovor nebude zahájen)")
    print("═" * 60)
    print(f"\nTarget:       {TARGET_PHONE}")
    print(f"Datum:        {BOOKING_DATE}")
    print(f"Voice ID:     {ELEVENLABS_VOICE_ID}")
    print(f"From number:  {TWILIO_FROM_NUMBER}")
    print(f"\n── System Prompt ──\n{SYSTEM_PROMPT}")
    print(f"\n── First Message ──\n{FIRST_MESSAGE}")


# ── Validace config ────────────────────────────────────────────────────────────

def validate_config() -> list[str]:
    errors = []
    if not ELEVENLABS_API_KEY:
        errors.append("ELEVENLABS_API_KEY není nastaven v config.py")
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        errors.append("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN nejsou nastaveny v config.py")
    if not TWILIO_FROM_NUMBER or TWILIO_FROM_NUMBER.startswith("+1XXX"):
        errors.append("TWILIO_FROM_NUMBER není platné E.164 číslo")
    if not TARGET_PHONE or TARGET_PHONE.startswith("+420XXX"):
        errors.append("TARGET_PHONE není nastaven v config.py")
    return errors


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Rezervace chatky přes ElevenLabs + Twilio")
    parser.add_argument("--dry-run", action="store_true", help="Jen vypíše konfiguraci agenta")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
        return

    errors = validate_config()
    if errors:
        print("Chyby v konfiguraci:")
        for e in errors:
            print(f"  ✗ {e}")
        print("\nEdituj config.py a spusť znovu.")
        sys.exit(1)

    print(f"Volám: {TARGET_PHONE}")
    print(f"Datum rezervace: {BOOKING_DATE}")
    print(f"Počet hostů: {GUEST_COUNT}")
    print()

    phone_number_id = get_or_register_phone_number()
    agent_id = create_agent()
    try:
        call_data = initiate_outbound_call(agent_id, phone_number_id)
        call_sid = call_data.get("call_sid", "")

        print(f"\nHovor probíhá (max 6 min čekám na dokončení)...")
        result = poll_conversation(agent_id, call_sid)

        if result:
            print_result(result)
        else:
            print("Timeout — hovor nebyl dokončen v limitu. Zkontroluj Twilio konzoli.")
            print(f"Agent ID: {agent_id}  |  Call SID: {call_sid}")
    finally:
        # Smažeme agenta po dokončení (nezanechávat dočasné agenty)
        delete_agent(agent_id)


if __name__ == "__main__":
    main()
