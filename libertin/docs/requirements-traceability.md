# Požadavky ze zadávací dokumentace — traceabilita

> Zdroj: zadávací dokumentace a technické specifikace (příloha smlouvy o dílo,
> dodána objednatelem mimo repo). Tento dokument extrahuje požadavky a mapuje
> je na stav Libertin monorepa. Číslo smlouvy a identifikace stran záměrně
> neuvádíme — repo je veřejné.

## Rozsah: rozhodnuto

Objednatel rozhodl, že se dodává **celý systém dle zadání** — ne pouze klientská
vrstva nad legacy API. `CLAUDE.md` i `docs/backlog.yaml` z toho vycházejí.

Rozsah práce je rozepsaný v `docs/backlog.yaml` (15 epiců, 77 tasků); tento
dokument drží mapování požadavek → stav. Otevřená rozhodnutí objednatele jsou
vedená tamtéž v sekci `decisions` (D-001 až D-006).

Zbývá rozpor u **GitLabu**: zadání ho vyžaduje pro hosting i CI/CD (C10, C11),
vývoj běží na GitHubu — vedeno jako D-002.

## Legenda stavů

- ✅ hotovo v repu
- 🔜 plánováno (uvedená fáze z CLAUDE.md)
- 🧩 mezera v klientském scope — přidat do backlogu klienta
- 🏗️ backend/infra scope — mimo současný klient-first záběr, čeká na rozhodnutí
- ⚠️ vyžaduje rozhodnutí objednatele

## Zadání (obecné)

| Požadavek | Stav | Poznámka |
|---|---|---|
| Vzhled a rozsah definován Figma hand-off návrhem | ⚠️ | Hand-off dodán: [Figma — Libertin](https://www.figma.com/design/BF3X0FKBKEbt5uTcrO4jkk/Libertin?node-id=3786-159470), node `3786:159470`. **Blokováno přístupem**: účet má na souboru jen seat „View" (starter tier), Figma MCP vyžaduje editor access → design-parity průchod ani extrakci tokenů/inventury obrazovek zatím nelze provést. Potřeba editor invite od vlastníka souboru, nebo export mockupů (PNG/PDF) do repa. |
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
| B4.2 | 2FA: SMS, TOTP i passkey | 🔜 | Architektura hotová — [ADR 0001](adr/0001-2fa-architecture.md) (E2-T1 done). Zbývá promítnout do kontraktu (E2-T2) a implementovat. Otevřená otázka D-006: smí být SMS jediný faktor? |
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
| C1 | UI odpovídá Figma mockupům | 🔜 | hand-off dodán (viz Zadání výše); provést design-parity průchod |
| C2 | Minimalizace externích služeb, maximum on-premise | 🏗️ | ovlivní volbu analytiky, map (self-host tiles?), push |
| C3 | Cloud-ready: kontejnery per komponenta, S3 úložiště (ne POSIX), CDN-ready statika, minimalizace requestů, Redis, datové vrstvy | 🏗️ | klient už dnes: Next.js bundluje a dělí kód (91 kB First Load vs 607 kB legacy) |
| C4 | Docker kontejnery + Docker Compose | ✅ (web) | `apps/web/Dockerfile` + `docker-compose.yml`, ověřeno reálným buildem image; viz [deployment.md](deployment.md). Backend/DB/úložiště kontejnery zbývají; mobilní pipeline E10-T7. |
| C5 | Škálování a HA (dynamické přidávání FE uzlů, load balancer, multi-node DB) | 🏗️ | |
| C6 | State-of-the-art postupy, architektura, UX, dokumentace | ✅ průběžně | monorepo, typed contract-locked client, tokens, i18n |
| C7 | Precizní dokumentace (incode, architektura, admin, manuály, in-app nápověda) | 🔜 | [architecture.md](architecture.md), [adr/](adr/), [deployment.md](deployment.md), [privacy-review.md](privacy-review.md). Manuály a in-app nápověda zbývají. |
| C8 | Předatelnost externímu subjektu | 🔜 | plyne z C7 + IaC |
| C9 | Bezvýpadkové aktualizace (rolling restarts) | 🏗️ | |
| C10 | Git; kompletní repo součástí díla; **GitLab** pro řízení i hosting | ⚠️ | dnes GitHub — rozhodnout mirror vs přesun |
| C11 | Automatizované testy pokrývající většinu funkcí; GitLab CI/CD; IaC (Ansible) | 🔜 | Harness hotový: **79 testů** (Vitest + Testing Library), `pnpm test:all`. CI pipeline (E11-T2) a Ansible zatím ne. |
| C12 | Akceptace: odezva UI ≤ 1,5 s při max. zátěži; 30denní beta | 🔜 | k6 budget v Phase 4 přesně na 1,5 s; beta = provozní milník |
| C13 | Migrace dat ze swingerslife.cz (vč. neregistrovaných přihlášek na akce) | 🏗️ | před betou; potřebuje přístup k DB legacy webu |

## Technologie uvedené v zadání vs. naše volby

Zadání jmenuje směs technologií („Flatter" [sic — Flutter], React Native,
K8s+Docker, PHP Nette/Symfony/Laravel, Java, React.js/Node.js) — jde o výčet
možností, ne závaznou architekturu. Naše volby (React Native/Expo, React/Next.js,
Node toolchain) jsou podmnožinou tohoto výčtu a jsou v souladu. Legacy backend
je Laravel (viz `docs/live-audit.md`), což zapadá do PHP větve zadání, pokud by
se backend přepisoval.

## Nejbližší práce

Pořadí drží `docs/backlog.yaml`. Aktuálně odblokované a nejcennější:

1. **2FA do kontraktu** (E2-T2, B4.2) — ADR je hotové, kontrakt ho ještě neodráží.
2. **CI pipeline** (E11-T2, C11) — testy existují, nic je neběží automaticky.
3. **Přepínač denního/nočního režimu** (B6) — tokeny existují, chybí UI toggle.
4. **Zbytek nálezů privacy review** (E14-T5/T6/T7).

**Blokované rozhodnutím**: cokoliv závislé na designu (D-001 Figma access), CI
volba (D-002), backend a migrace (D-003), infrastruktura (D-004), SMS jako
jediný faktor (D-006).
