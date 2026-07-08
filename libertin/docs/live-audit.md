# Audit živého webu swingerslife.cz

> Snímek stavu před modernizací na Libertin. Měřeno 2026-07-08 (curl, veřejné stránky: /, /login, /register).

## Stack (zjištěno)

- **Backend**: Laravel (XSRF-TOKEN + `swingerslife_session` cookie), Apache, HTTP/2
- **Frontend**: Bootstrap + jQuery pluginy (tooltipster, lightbox, nprogress, bootstrap-multiselect), Font Awesome **i** Material Design Icons zároveň (duplicitní ikonové sady)
- **Assets**: cache-bust `?1656049921` = červen 2022 — frontend ~4 roky bez změny

## Výkon

| Metrika | Hodnota | Poznámka |
|---|---|---|
| `js/app.js` | 2,8 MB raw / 607 kB gzip | monolit, blokuje interaktivitu |
| CSS souborů | 13 samostatných requestů | žádný bundling |
| JS souborů | 5 samostatných | dtto |
| HTML homepage | 116 kB | server-rendered, login form 3× v jedné stránce |
| TTFB | 0,45–0,97 s | `cache-control: no-cache, private` i pro nepřihlášené — nic se nekešuje |

cíl k6 ≤1,5 s z Phase 4 je proti současnému stavu reálné zlepšení, ne jen udržení.

## Bezpečnostní hlavičky

- ❌ **Žádný HSTS**
- ❌ **Žádná Content-Security-Policy**
- ❌ **Žádná Referrer-Policy** — pro adult komunitu zásadní: klik na externí odkaz leakuje `swingerslife.cz` v refereru. Přímý rozpor s „diskrétnost jako feature“.
- ❌ Žádné X-Frame-Options / X-Content-Type-Options
- ⚠️ Deprecated `Feature-Policy` místo `Permissions-Policy`
- ⚠️ Session cookie s platností **1 rok** — na sdíleném počítači soukromí selhává
- ⚠️ HTTP→HTTPS přes **307 Temporary** místo 301/308 Permanent

## SEO

- ❌ `<title>SwingersLIFE - </title>` — rozbitý/prázdný suffix na všech stránkách
- ❌ Žádná meta description
- ❌ Žádné `<h1>`–`<h3>` na homepage (116 kB HTML bez jediného nadpisu)
- ❌ `sitemap.xml` → 404
- ✅ `lang="cs"`, viewport meta, alt texty u obrázků (13/13)

## Obsah — čeština (živé překlepy na homepage)

| Živě | Správně |
|---|---|
| „V **naši** komunitě získáte…“ | V **naší** komunitě |
| „**Našim** cílem je,“ | **Naším** cílem je (+ přebytečná čárka) |
| „seznámen**i** se s jinými“ | seznámen**í** |
| „Sociální síť pro **swingers páry**“ | swingerské páry / swingery |

→ potvrzuje pravidlo z CLAUDE.md: všechny stringy přes i18n klíče, korektury v `locales.json`.

## UX / compliance

- ❌ **Žádný age gate (18+)** při vstupu — pro adult obsah právní i etický problém; v Libertin máme `footer.age`, ale potřebujeme i vstupní potvrzení
- ⚠️ 35 inline stylů na homepage
- ⚠️ Login formulář duplikovaně 3× v DOM jedné stránky

## Důležité pro API kontrakt

Reálný login POST na `/login` posílá pole **`user`** (ne `email`), `password`, `remember`, `_token` (Laravel CSRF). Náš `contracts/openapi.snapshot.yaml` zatím předpokládá `email`/`password` JSON — **až budeme snímat živé API, kontrakt se upraví** (form-encoded + CSRF vs. JSON bearer). Přesně od toho je `/contract-check`.

## Priorita oprav v Libertin klientu

1. **Referrer-Policy + krátká session + age gate** — diskrétnost je konverzní páka (CLAUDE.md), tady živý web selhává nejvíc
2. **Výkonový rozpočet** — bundle < 200 kB gzip vs. dnešních 607 kB; Next.js code-splitting to řeší z podstaty
3. **SEO základy na landing** (Phase 3) — title/description/h1/sitemap jsou quick wins proti nule
4. **i18n korektury** — už hotovo v `packages/i18n/locales.json`, nepřenášet staré texty
