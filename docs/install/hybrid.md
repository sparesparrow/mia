# Install – Hybrid Edition (Phone + mikro DVR)

## Požadavky
- Vše z Phone Edition
- Pi gateway (RTSP DVR, LPR offload, MQTT bridge)
- 12V→5V buck (5A), SSD/SD pro DVR

## Kroky
1) Zapojte Pi (napájení, síť, kamery), ověřte RTSP
2) Spusťte `mqtt-bridge` pro mirroring témat (phone ↔ gateway)
3) Zapněte Android app; detekce leadera přepne ANPR na Pi
4) Ověřte DVR timeline a event‑clipy

## Ověření
- Při přítomnosti gateway se ANPR a DVR offloadují
- MQTT témata kontinuálně aktivní při odchodu telefonu
