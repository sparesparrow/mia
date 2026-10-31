#!/usr/bin/env bash
# RUN ON THE PI ONLY. HARDWARE-MARKED. NEVER RUN IN CI.
#
# Skeleton of the Pi voice smoke test (REQ-VOICE-028 harness, layer L5): play a rendered utterance into the
# ALSA loopback so the audio path hears it as if it came from a microphone. It plays one file and prints where
# to look; it does not check results yet, and nothing here has been run on a Pi.
#
#   sudo modprobe snd-aloop            # creates the card "Loopback"
#   python3 tools/voice/render_fixtures.py --out /var/tmp/mia-voice-fixtures
#   scripts/pi_voice_smoke.sh [phrase_file.wav]
#
# What is written into the loopback's playback side (Loopback,0,0) comes out of its capture side (Loopback,1,0),
# which audio_capture must open as its input device. TTS replies stay on the headphone jack.
set -euo pipefail

FIXTURES="${MIA_VOICE_FIXTURES:-/var/tmp/mia-voice-fixtures}"
WAV="${1:-$FIXTURES/be_quiet.wav}"

if [[ "$(uname -m)" != aarch64 && "$(uname -m)" != armv7l ]]; then
    echo "refusing to run: this script is for the Raspberry Pi (found $(uname -m))" >&2
    exit 2
fi
if [[ -n "${CI:-}" ]]; then
    echo "refusing to run in CI: it needs the Pi's sound devices" >&2
    exit 2
fi
if [[ ! -f "$WAV" ]]; then
    echo "missing $WAV; render the fixtures first (tools/voice/render_fixtures.py)" >&2
    exit 2
fi

if ! grep -q Loopback /proc/asound/cards; then
    sudo modprobe snd-aloop
fi

# The capture-side index sounddevice reports; audio_capture needs this as its input device (AUDIO_DEVICE).
python3 - <<'PY'
import sounddevice as sd

for index, device in enumerate(sd.query_devices()):
    if "Loopback" in device["name"] and device["max_input_channels"] > 0:
        print(f"aloop capture device index {index}: {device['name']}")
PY

echo "playing $WAV into Loopback,0,0"
aplay -D plughw:Loopback,0,0 "$WAV"

# Not done yet (layer L5): start audio_capture on the capture device, press Wake over /ws/voice, and run the speech_alsa_*
# scenarios with the Pi harness once REQ-VOICE-025 and REQ-VOICE-027 exist.
