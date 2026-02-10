# DPIA Template (CZ/EU)

## 1) Project Overview
- Účel zpracování (ANPR, diagnostika, upozornění)
- Subjekty údajů (řidiči, posádka, třetí osoby v okolí)

## 2) Právní základ a nezbytnost
- Oprávněný zájem / souhlas (opt‑in funkce)
- Minimalizace dat, edge‑only zpracování

## 3) Popis toků dat a uchovávání
- Toky dat (kamera/OBD → telefon → MQTT)
- Retence (ANPR 24–72h, telemetrie 7 dní), hashování SPZ (HMAC‑SHA256)

## 4) Rizika a opatření
- Technická: šifrování, TLS pinning, klíče v Keystore/NVS
- Organizační: přístupová práva, audit log, školení instalátorů

## 5) Práva subjektů údajů
- Informování, přístup, výmaz, nastavení retenční politiky v UI

## 6) Posouzení zbytkového rizika
- Shrnutí a přijatelná úroveň rizika

## 7) Schválení a revize
- Odpovědná osoba, datum, periodicita revize
