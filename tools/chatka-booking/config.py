"""
Booking configuration — edit before running rezervace.py
"""

import os

# ── Target call ────────────────────────────────────────────────────────────────
TARGET_PHONE = "+420776168749"   # číslo penzionu / chatky (E.164 format)
BOOKING_DATE = "30. dubna 2026"  # datum rezervace (lidsky čitelný formát)
GUEST_COUNT  = 4                 # počet hostů (přibližný odhad)

# ── Twilio credentials (z env nebo přímé hodnoty) ──────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "+17722799583")   # Twilio číslo s hlasem

# ── ElevenLabs credentials (z env nebo přímé hodnoty) ─────────────────────────
ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "2qbJHyAaz7tHCfVZS6z3")
# Hana [CZ] — nativní český hlas; alternativy: Jan (KIDKfqJyZ6ASuyzsKfh5), Jiří (6FxLnDbRUt4y6CGhqpkl)

# ── Webhook (výsledky hovoru) ─────────────────────────────────────────────────
# Pokud chceš přijímat výsledky hovoru, nastav veřejnou URL na /result
# (ngrok, cloudflare tunnel, nebo tvoje doménové jméno)
WEBHOOK_BASE_URL = ""            # např. "https://abc123.ngrok.io"  (nebo nechat prázdné)
WEBHOOK_PORT     = 8765          # lokální port pro webhook server

# ── Výstupní soubor ───────────────────────────────────────────────────────────
RESULT_FILE = "/tmp/chatka-booking-result.json"

# ── Agent prompts (sdílené mezi rezervace.py a rezervace_local.py) ─────────────
SYSTEM_PROMPT = f"""Voláš za kamaráda, který chce rezervovat chatku na {BOOKING_DATE} pro {GUEST_COUNT} lidi.
Zjisti: volno? cena za noc? min. délka? jak potvrdit? storno?
Pokud jde zablokovat termín, požádej o to.
Mluv přirozeně česky — krátké věty, hovorově, žádné formality. Max 1-2 věty na odpověď.
Pokud se zeptají jestli jsi člověk — řekni že jsi AI asistent volající za kamaráda.""".strip()

FIRST_MESSAGE = f"Ahoj, volám kvůli chatce — máte volno na {BOOKING_DATE}?"
