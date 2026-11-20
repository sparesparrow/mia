# Phone USB tether and MIA voice test

This setup uses one USB data cable between the Android phone and Raspberry Pi: Android USB tethering gives the Pi
internet access, the MIA app streams the phone microphone to the Pi, and the Pi plays MIA's speech through its
speakers. Speech recognition and synthesis remain on the Pi.

## 1. Connect the USB network

1. Connect the phone to one of the Pi 4's USB 3 ports with a data-capable USB cable.
2. On Android, enable **USB tethering** in the system's Hotspot/Tethering settings. The phone may need to be
   unlocked before this option is available.
3. On the Pi, find the tether interface:

   ```bash
   ip -br link
   ```

   It is commonly named `usb0` or `enx...`. Configure DHCP and prefer the phone route with the setup script, using
   the interface name from the previous command:

   ```bash
   sudo bash /opt/mia/infra/deploy/rpi/setup-usb-tether.sh usb0
   ip -br addr
   ip route
   ```

   The script supports active NetworkManager and `dhcpcd` services. It fails with instructions if neither is active.

4. Copy the Pi's IPv4 address on that USB interface. In the MIA app's Settings, enter that address and the Pi's API
   key. Include port `8000` if it is not already in the address. Use a key with `write` scope for microphone streaming.

## 2. Enable the Pi voice path

In `/etc/mia/environment`, set:

```ini
VOICE_PHONE_MIC=1
VOICE_CONSOLE=1
VOICE_CONSOLE_BACKEND=router
VOICE_FSM=1
AUDIO_SOURCE=auto
```

Restart the relevant services so they read the settings:

```bash
sudo systemctl restart mia-audio-capture mia-voice-router mia-stt mia-tts mia-api
```

The Pi must have the MIA TTS voice installed and its speakers connected. Check available ALSA outputs with
`aplay -l`; set `AUDIO_OUTPUT_DEVICE` in `/etc/mia/environment` when the default output is not the connected speaker.
Confirm that `ip route` selects the phone interface as the Pi's default route while tethering is enabled.

## 3. Speak a test command

1. Open the Voice tab and wait for the console to connect.
2. Tap **Start microphone** and grant microphone permission. Android shows a persistent notification with a Stop
   action while the stream is active.
3. Tap **Wake**, speak an English command, and listen for the response on the Pi speaker. The app should show the
   recognized transcript and MIA's spoken phrase.
4. Tap **Stop microphone** in the app or its notification when finished.

If the Voice tab connects but the transcript does not change, confirm `VOICE_PHONE_MIC=1`, the write-scope key, and
that `mia-audio-capture` is running. If the transcript and spoken phrase appear but no sound is heard, select the Pi
speaker's ALSA output. If the phone does not reach the Pi, check that the app's configured address is the Pi's USB
interface address and that the Pi received a DHCP lease from the phone.

## Privacy and transport

The app sends microphone frames only while its foreground microphone service is running. The Pi does not store raw
frames; the API and capture service log counts and drops. The prototype uses the API's existing plain HTTP/WebSocket
transport, so the API key and audio are not encrypted on the tether link (ADR-0016).
