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
- Klíč HMAC: vlastní pro každou instalaci, soubor mimo zálohy; bez telefonu otisk nic neznamená (ADR-0018)
- Černá kniha: otisky SPZ a štítky, které zadal uživatel; retenci nepodléhá, maže je uživatel (REQ-AND-020)
- Upozornění na opakovaně viděné auto: počítá se z otisků za posledních 24 h, zůstává v telefonu (REQ-AND-021)

## 4) Rizika a opatření
- Technická: šifrování, klíče v Keystore/NVS (klíč SPZ je zatím soubor, Keystore až od API 23; TLS na Pi chybí, #139)
- Černá kniha a štítky jsou osobní údaje o třetích osobách: posoudit účel, výmaz a kdo k telefonu má přístup
- Organizační: přístupová práva, audit log, školení instalátorů

## 5) Práva subjektů údajů
- Informování, přístup, výmaz, nastavení retenční politiky v UI

## 6) Posouzení zbytkového rizika
- Shrnutí a přijatelná úroveň rizika

## 7) Schválení a revize
- Odpovědná osoba, datum, periodicita revize
