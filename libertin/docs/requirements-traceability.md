# Požadavky ze zadávací dokumentace — traceabilita

> Zdroj: zadávací dokumentace a technické specifikace (příloha smlouvy o dílo,
> dodána objednatelem mimo repo). Tento dokument extrahuje požadavky a mapuje
> je na stav Libertin monorepa. Číslo smlouvy a identifikace stran záměrně
> neuvádíme — repo je veřejné.

## ⚠️ Zásadní rozpor se současným working agreement

**Zadání definuje vývoj celého systému od nuly** („systém bude vyvíjen od nuly
jako dílo na zakázku s modulární strukturou") — včetně backendu, infrastruktury,
provozu, záloh, mailserveru a migrace dat.

**CLAUDE.md tohoto repa říká opak**: „We are NOT rewriting the backend. We build
a new client layer that talks to the existing API."

Obě věci mohou platit zároveň jen jako **fázovaná strategie** (klient-first nad
mocky → backend jako další velký blok). Dokud objednatel nerozhodne jinak,
pokračujeme klient-first; tabulka níže ale mapuje **celé** zadání, aby nic
nezapadlo.

Druhý rozpor: zadání vyžaduje **GitLab** (hosting repozitářů, řízení požadavků,
CI/CD) — aktuálně jsme na GitHubu. `docs/dev-orchestration.md` s GitLab CI už
počítá (Phase 4); přesun/mirror je třeba naplánovat.

## Legenda stavů

- ✅ hotovo v repu
- 🔜 plánováno (uvedená fáze z CLAUDE.md)
- 🧩 mezera v klientském scope — přidat do backlogu klienta
- 🏗️ backend/infra scope — mimo současný klient-first záběr, čeká na rozhodnutí
- ⚠️ vyžaduje rozhodnutí objednatele

## Zadání (obecné)

| Požadavek | Stav | Poznámka |
|---|---|---|
| Vzhled a rozsah definován Figma hand-off návrhem | ⚠️ | Figma export zatím nemáme v repu; obrazovky Phase 2/3 stavěny dle CLAUDE.md popisu. Jakmile bude Figma k dispozici, srovnat. |
| Průběžné konzultace, písemné dotazy na nejasnosti | — | procesní; nejasnosti evidovat v PR/issues |

## A. Hardware / prostředí

| # | Požadavek | Stav | Poznámka |
|---|---|---|---|
| A1 | Návrh optimálního HW (server/cloud) | 🏗️ | |
| A2 | Instalace a zprovoznění OS | 🏗️ | |
| A3 | Implementace všech funkcí z Figma mockupů + nasazení do produkce a záložního serveru | ⚠️🏗️ | funkčně = celý projekt; nasazení je infra scope |
| A4 | Mailserver (instantní maily, certifikáty) | 🏗️ | |

## B. Funkční požadavky

| # | Požadavek | Stav | Poznámka |
|---|---|---|---|
| B1 | Role a oprávnění (admin, editor, registrovaný, host) | 🧩 | klient: role-aware UI; backend: enforcement. Do API kontraktu přidat role. |
| B2 | Auditní log všech událostí (konfigurovatelná podrobnost, retence) | 🏗️ | |
| B3 | Dashboard stavu systému (zálohy, anomálie, logy) | 🧩🏗️ | klient: dashboard UI (Phase 5+); backend: zdroje dat |
| B4.1 | Výhradně šifrovaný přístup (HTTPS, SSH) | ✅ (klient) | HSTS + security headers v `apps/web/next.config.mjs`; zbytek infra |
| B4.2 | 2FA: SMS, TOTP i passkey | 🧩 | zásadní rozšíření auth flow (Phase 2 má jen login+verify). Přidat do API snapshotu a naplánovat obrazovky. |
| B4.3 | Šifrování dat at-rest (disky, DB, S3, zálohy) | 🏗️ | |
| B4.4 | Management a zálohování šifrovacích klíčů + UI | 🏗️🧩 | |
| B5 | Zálohy + verzování obsahu (náhled historie, selektivní i plná obnova, plán, retence) | 🏗️ | klient později: UI náhledu historie obsahu |
| B6 | Denní a noční režim UI | ✅ (základ) | `[data-theme="private"]` v `tokens.css`; zbývá přepínač v UI 🧩 |
| B7 | Geolokace obsahu a uživatelů v embedded mapě | 🧩 | pozor na střet s „diskrétnost jako feature" — návrh musí být opt-in |
| B8 | Geo-omezení přístupu k modulům (dle IP) | 🏗️ | |
| B9 | Push notifikace | 🧩 | mobile: Expo notifications; web: Web Push |
| B10 | Hromadné nahrávání dat (uživatelé, stránky, jazyky) | 🏗️🧩 | admin UI + backend |
| B11 | SEO + pro-marketing UX (XML/HTML sitemap, indexace, CTA) | ✅ (základ) | Phase 3: metadata, h1/h2, robots.ts, sitemap.ts, CTA. HTML sitemap a submission 🔜 |
| B12 | On-premise analytika (návštěvnost, unikáti, trendy, per-objekt) + dashboard s grafy | 🏗️🧩 | on-prem (např. Matomo/Plausible self-host) + dashboard UI |
| B13 | Vícejazyčnost celého UI; plná CS+EN součástí dodávky | ✅ (základ) | `packages/i18n` cs+en, vše přes klíče; hlídá `/audit-czech` |
| B14 | SMS brána (komunikace + ověření přihlášení) | 🏗️ | jediná povolená externí služba vedle platební brány |

## C. Nefunkční požadavky

| # | Požadavek | Stav | Poznámka |
|---|---|---|---|
| C1 | UI odpovídá Figma mockupům | ⚠️ | viz výše — potřebujeme Figma export |
| C2 | Minimalizace externích služeb, maximum on-premise | 🏗️ | ovlivní volbu analytiky, map (self-host tiles?), push |
| C3 | Cloud-ready: kontejnery per komponenta, S3 úložiště (ne POSIX), CDN-ready statika, minimalizace requestů, Redis, datové vrstvy | 🏗️ | klient už dnes: Next.js bundluje a dělí kód (91 kB First Load vs 607 kB legacy) |
| C4 | Docker kontejnery + Docker Compose | 🏗️ | přidat Dockerfile pro web už teď je levné 🔜 |
| C5 | Škálování a HA (dynamické přidávání FE uzlů, load balancer, multi-node DB) | 🏗️ | |
| C6 | State-of-the-art postupy, architektura, UX, dokumentace | ✅ průběžně | monorepo, typed contract-locked client, tokens, i18n |
| C7 | Precizní dokumentace (incode, architektura, admin, manuály, in-app nápověda) | 🔜 | README + docs/ založeny; in-app nápověda 🧩 |
| C8 | Předatelnost externímu subjektu | 🔜 | plyne z C7 + IaC |
| C9 | Bezvýpadkové aktualizace (rolling restarts) | 🏗️ | |
| C10 | Git; kompletní repo součástí díla; **GitLab** pro řízení i hosting | ⚠️ | dnes GitHub — rozhodnout mirror vs přesun |
| C11 | Automatizované testy pokrývající většinu funkcí; GitLab CI/CD; IaC (Ansible) | 🔜/🏗️ | Phase 4: contract→lint→test→build→perf→e2e. Testy klienta zatím chybí 🧩 |
| C12 | Akceptace: odezva UI ≤ 1,5 s při max. zátěži; 30denní beta | 🔜 | k6 budget v Phase 4 přesně na 1,5 s; beta = provozní milník |
| C13 | Migrace dat ze swingerslife.cz (vč. neregistrovaných přihlášek na akce) | 🏗️ | před betou; potřebuje přístup k DB legacy webu |

## Technologie uvedené v zadání vs. naše volby

Zadání jmenuje směs technologií („Flatter" [sic — Flutter], React Native,
K8s+Docker, PHP Nette/Symfony/Laravel, Java, React.js/Node.js) — jde o výčet
možností, ne závaznou architekturu. Naše volby (React Native/Expo, React/Next.js,
Node toolchain) jsou podmnožinou tohoto výčtu a jsou v souladu. Legacy backend
je Laravel (viz `docs/live-audit.md`), což zapadá do PHP větve zadání, pokud by
se backend přepisoval.

## Dopady na nejbližší práci (klient-first)

1. **2FA obrazovky a API kontrakt** (B4.2) — největší funkční mezera v auth
   flow; přidat do `openapi.snapshot.yaml` a za Phase 4 zařadit.
2. **Přepínač denního/nočního režimu** (B6) — tokeny existují, chybí UI toggle.
3. **Testy klienta** (C11) — unit/component testy k Phase 4 CI.
4. **Dockerfile pro web** (C4) — levný krok směrem k infra požadavkům.
5. **Figma hand-off** (C1) — vyžádat od objednatele, srovnat hotové obrazovky.
6. **GitLab** (C10) — rozhodnutí o mirroru/přesunu.
