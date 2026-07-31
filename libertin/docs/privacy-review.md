# Privacy review UI — „diskrétnost jako feature“

> Task **E14-T4** (`docs/backlog.yaml`), role `reviewer`. Datum: 2026-07-30.
> Předmět: `apps/web`, `apps/mobile`, `packages/ui`, `packages/api`,
> `packages/i18n`, `contracts/openapi.snapshot.yaml`.
>
> Jediná otázka, kterou si tento dokument klade: **může nepřátelská strana
> dokázat, že konkrétní pojmenovaný člověk používá tuto platformu, nebo zjistit,
> co tu dělal?**
>
> Review je čtecí. Nic v kódu nebylo změněno — nálezy opravují vlastnící role.

## Model hrozby, proti kterému se měřilo

Tři útočníci, všichni realistickí pro tuto komunitu:

1. **Sdílené zařízení** — partner, rodina, spolubydlící nebo firemní IT má
   fyzický přístup k prohlížeči či telefonu. Nehledá cíleně, ale otevře historii,
   uvidí titulek panelu, notifikaci na zamčené obrazovce nebo přehled aplikací.
2. **Nepřátelský člen** — má legitimní účet a chce deanonymizovat ostatní.
   Nástroje: devtools, Network panel, vlastní profilová data, která server rozešle
   dalším uživatelům.
3. **Třetí strana v síťové cestě** — analytika, CDN, mapové dlaždice, hostitel
   obrázků. Nikdy nedostane obsah, ale dostane IP + čas + kontext požadavku, což
   pro spojení „tato osoba byla na tomto webu“ stačí.

## Co bylo ověřeno spuštěním, ne přečtením

Tvrzení níže se opírají o skutečný výstup, ne o dojem z kódu.

**1. Hlavičky, které web opravdu posílá** — načtení `next.config.mjs` a zavolání
`headers()`:

```
$ cd apps/web && node --input-type=module -e "const c=(await import('./next.config.mjs')).default; console.log(JSON.stringify(await c.headers(),null,2))"
[{ "source": "/:path*", "headers": [
    { "key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains; preload" },
    { "key": "Referrer-Policy",           "value": "same-origin" },
    { "key": "X-Content-Type-Options",    "value": "nosniff" },
    { "key": "X-Frame-Options",           "value": "DENY" },
    { "key": "Permissions-Policy",        "value": "camera=(), microphone=(), geolocation=()" } ]}]
```

**2. Titulky ve skutečně vygenerovaném HTML** (`apps/web/.next/server/app/`):

```
$ grep -o "<title>[^<]*</title>" .next/server/app/index.html
<title>Libertin — Diskrétní sociální síť pro dospělé</title>
$ grep -o "<title>[^<]*</title>" .next/server/app/login.html
<title>Přihlášení | Libertin</title>
```

**3. Age gate v serverovém HTML** — probe s `renderToStaticMarkup` (React 18,
mimo repo, ve scratchpadu):

```
=== SERVER HTML START ===
<main>SECRET-ADULT-CONTENT</main>
=== SERVER HTML END ===
contains adult content: true
contains age gate:      false
```

Totéž potvrzuje reálný build: `<body>` v `index.html` obsahuje celý landing
(`Vaše komunita, vaše pravidla`, `Naše komunity`, …) a **žádný** overlay; řetězec
`Je vám 18 nebo více let?` se v souboru vyskytuje jen jednou, a to uvnitř RSC
flight payloadu (`<script>`), tedy jako props komponenty, která se připojí až po
hydrataci.

**4. Existující testy age gate** — `npx vitest run src/AgeGate` v `packages/ui`:
`9 passed`. Chování `localStorage` a `leaveHref` je tedy zafixované testy, ne
domněnka.

**5. Nulová třetí strana v produktovém kódu** — grepy přes `apps` + `packages`
(bez `node_modules`, bez `.next`) nenašly žádné `analytics`, `gtag`, `sentry`,
webový font, `@import` externí CSS ani vzdálený obrázek v produktovém kódu (jediný výskyt je ve Storybook story — viz P10). Jediné externí URL v
produktovém kódu jsou vlastní domény (`libertin.cz`, `api.libertin.cz`) a
`https://www.google.com` jako cíl odchodu z age gate.

**6. Nulová persistence v mobilu** — grep na `AsyncStorage`, `SecureStore`,
`document.cookie`: **žádný výskyt**. Token žije jen v React state
(`apps/mobile/src/AuthFlow.tsx:21`) a zaniká s procesem.

## Souhrn

| # | Nález | Kde | Závažnost | Stav |
|---|---|---|---|---|
| P1 | `User.email` se rozesílá ve feedu a v seznamu konverzací | `contracts/openapi.snapshot.yaml:164`, `packages/api/src/client.ts:5,9,11` | **Vysoká** | reálný |
| P2 | Titulek landingu prozradí povahu webu v historii, panelu a náhledu odkazu | `apps/web/src/app/layout.tsx:11` | **Vysoká** | reálný |
| P3 | Age gate není v serverovém HTML — obsah se vykreslí před ním | `packages/ui/src/AgeGate/index.tsx:27,38`, `apps/web/src/app/layout.tsx:22–23` | Střední | reálný |
| P4 | Odkaz „Opustit web“ nechává záznam v historii a nemá `rel="noreferrer"` | `packages/ui/src/AgeGate/index.tsx:108–117` | Střední | reálný |
| P5 | `fetch()` bez `cache: 'no-store'` na autentizovaných GET požadavcích | `packages/api/src/client.ts:22` | Střední | reálný |
| P6 | `Avatar` renderuje libovolné vzdálené `src` bez `referrerPolicy` | `packages/ui/src/Avatar/index.tsx:20` | Střední (dnes) / **Vysoká** (po napojení) | reálný + budoucí |
| P7 | Souhlas s 18+ v `localStorage` bez expirace | `packages/ui/src/AgeGate/index.tsx:16,42` | Nízká–střední | reálný |
| P8 | Chybí `Cache-Control` a CSP v hlavičkách | `apps/web/next.config.mjs:5–11` | Nízká (dnes) | budoucí |
| P9 | `robots.txt` povoluje vše bez výjimek | `apps/web/src/app/robots.ts:7` | Nízká (dnes) / **Vysoká** (po profilech) | budoucí |
| P10 | Placeholder z třetí strany ve Storybooku | `packages/ui/src/Avatar/Avatar.stories.tsx:11` | Nízká | reálný |
| P11 | `.gitignore` nechytá `.env.production` a spol. | `.gitignore:7–8` | Nízká–střední | reálný |

Chybějící kontroly pro dosud nepostavené funkce jsou samostatně v části
[Budoucí rizika](#budoucí-rizika-a-chybějící-kontroly) jako **F1–F6**. Nejsou to
nálezy — je to seznam, který musí být hotový, **než** se ta funkce označí za
dodanou.

---

## Reálné nálezy v současném kódu

### P1 — E-maily ostatních členů putují klientovi (Vysoká)

`contracts/openapi.snapshot.yaml:162–170` definuje `User` s **povinným**
`email`:

```yaml
User:
  required: [id, email, verified]
```

a tento `User` je zároveň typem `FeedItem.author` (řádek 194) a
`Conversation.participant` (řádek 211). Totéž v generovaném klientovi:
`packages/api/src/client.ts:5,9,11`. Mock to potvrzuje —
`packages/api/src/mocks/handlers.ts:30–31,38` vrací `user@example.com` jako
autora položek feedu.

**Scénář.** Nepřátelský člen si vytvoří účet, otevře feed, v devtools → Network
si stáhne odpověď `/feed` a `/messages` a vytáhne e-mailové adresy všech autorů.
E-mail je přímý identifikační údaj: `jmeno.prijmeni@zamestnavatel.cz` deanonymizuje
okamžitě, u ostatních stačí protočit adresu přes Gravatar nebo veřejné databáze
uniklých hesel. UI ta adresa přitom nikde nepotřebuje —
`apps/mobile/src/AuthFlow.tsx:58` z autora bere jen `displayName`.

Toto je nejvážnější nález v celém review a jediný, který funguje **bez** fyzického
přístupu k zařízení oběti.

**Minimální oprava.** Rozdělit schéma: `PublicUser { id, displayName, avatar }`
pro `FeedItem.author` a `Conversation.participant`; `email` ponechat výhradně na
`AuthResponse.user` a `Profile`, tedy na vlastním záznamu volajícího. Snapshot je
zmrazený kontrakt — změnu vlastní `architect` + `backend`, ne tato role.

### P2 — Titulek stránky prozradí povahu webu (Vysoká)

`apps/web/src/app/layout.tsx:11`:

```ts
default: `${dict.meta.title} — ${dict.meta.tagline}`,
```

`dict.meta.tagline` je `packages/i18n/locales.json:13` = „Diskrétní sociální síť
pro dospělé“. Ověřeno v buildu: `<title>Libertin — Diskrétní sociální síť pro
dospělé</title>`.

**Scénář.** Titulek stránky se objeví na pěti místech, která uživatel neovládá:
v historii prohlížeče a v našeptávači adresního řádku, v názvu panelu (čitelné
přes rameno v kanceláři), v titulku okna operačního systému (a tedy ve
screensharingu i v přepínači oken), jako výchozí název záložky a — protože web
nemá žádná `openGraph` metadata (`grep openGraph apps` = nic) — jako text
náhledu odkazu, když člen pošle URL do WhatsAppu, Signalu nebo firemního Slacku.
Jediné napsání „lib“ do adresního řádku na sdíleném notebooku vypíše celou větu.

Podstránka `/login` je v pořádku (`Přihlášení | Libertin`) — problém je jen
`default`, tedy landing a všechny stránky bez vlastního titulku.

**Minimální oprava.** `title.default` nastavit na `dict.meta.title`, tedy
jen `Libertin`. Popisná věta ať zůstane v `description` (SEO o nic nepřijde,
Google si klíčová slova vezme odtud) a doplnit explicitní `openGraph.title` +
`twitter.title` se stejně neutrálním textem, aby náhledy odkazů v chatu byly
záměrně nudné. **Autentizovaná část nesmí v `<title>` mít nic než `Libertin`** —
žádné „Zprávy“, „Profil Evy“, „BDSM skupina“.

### P3 — Age gate se vykreslí až po hydrataci (Střední)

`packages/ui/src/AgeGate/index.tsx:27` inicializuje stav na `null` a řádek 38
vrací `null`, dokud stav není `false`. `apps/web/src/app/layout.tsx:22–23` vykresluje
gate **za** `{children}`. Serverové HTML tedy obsahuje celý obsah stránky a gate
v něm není — viz probe i `.next/server/app/index.html` výše.

**Scénář.** Na pomalém spojení, na slabém telefonu nebo s vypnutým JavaScriptem
je celý landing včetně slova „swingeři“ vidět, dokud se nepřipojí overlay. Přesně
ten okamžik, kdy někdo jde kolem. Zároveň gate nezamyká scroll (`body` nemá
`overflow: hidden`) ani nedrží fokus, takže i po připojení se obsah za ním dá
vyčíst klávesnicí a odečítačem — `aria-modal="true"` na řádku 52 je tvrzení, které
implementace nedrží.

Pozitivní zjištění k témuž místu: pozadí overlaye je `--color-surface-dark`,
tedy `#222222` (`packages/theme/tokens.css:9`) — plně neprůhledné. Až se gate
připojí, obsah opravdu zakryje.

**Minimální oprava.** Souhlas držet v cookie a čtení přenést na server
(middleware nebo `cookies()` v layoutu), aby se rozhodnutí „gate, nebo obsah“
dělalo před odesláním HTML. Doplnit `overflow: hidden` na `body` a focus trap,
dokud je gate otevřený. Přechod na cookie zároveň řeší P7 — je to jedna změna.

### P4 — „Opustit web“ nechává stopu (Střední)

`packages/ui/src/AgeGate/index.tsx:108–117` je obyčejný `<a href={leaveHref}>`,
výchozí cíl `https://www.google.com` (řádek 24).

**Scénář a.** Navigace v témže panelu **přidá** záznam do session historie.
Tlačítko „Opustit web“ je u tohoto typu webu panikové tlačítko — kdo ho stiskne,
předpokládá, že po sobě zametl. Tlačítko Zpět ho ale vrátí na adult web a záznam
zůstane v historii i v našeptávači. Tlačítko dělá pravý opak toho, co slibuje.

**Scénář b.** Element nemá `rel="noreferrer noopener"`. Dnes referrer neuteče,
protože `next.config.mjs:7` posílá `Referrer-Policy: same-origin` (ověřeno
výstupem výše) — **to je zásluha, ne chyba**. Ale `packages/ui` je sdílený balík,
který o té hlavičce neví: stejná komponenta se renderuje ve Storybooku a bude se
renderovat v každém dalším hostiteli (statický export, webview, marketingový
microsite), kde ta hlavička nemusí být. Ochrana proti prozrazení nemá viset na
konfiguraci jiného balíku.

**Minimální oprava.** Na anchor doplnit `rel="noreferrer noopener"` a `onClick`,
který zavolá `e.preventDefault()` + `window.location.replace(leaveHref)` —
`replace` nahradí aktuální záznam historie místo přidání nového. `href` ponechat
jako fallback pro běh bez JS.

Cíl `https://www.google.com` sám o sobě nálezem není: referrer se neposílá a
Google je věrohodná „nevinná“ destinace. Za zmínku ale stojí, že je to
nekonfigurovatelná třetí strana v panikovém scénáři — patří to do props (což už
`leaveHref` umožňuje) a do dokumentace jako vědomé rozhodnutí.

### P5 — Autentizované GET požadavky mohou skončit v diskové cache (Střední)

`packages/api/src/client.ts:22`:

```ts
const res = await fetch(`${baseURL}${path}`, { ...init, headers });
```

Bez `cache` a bez `referrerPolicy`. `/feed`, `/messages` i `/profile` jsou GET s
`Authorization` hlavičkou.

**Scénář.** Jestli JSON s feedem a seznamem konverzací přistane v diskové cache
prohlížeče, závisí čistě na hlavičkách serveru — a `CLAUDE.md` říká, že API se
bere jako **zmrazený, nedůvěryhodný externí vstup**. Na sdíleném notebooku
cachovaný JSON přežije zavření panelu i odhlášení a přečte se z profilu
prohlížeče bez jakékoli session. Obsahuje `displayName` protistran a (viz P1)
jejich e-maily.

**Minimální oprava.** Do sdílené funkce `request()` přidat
`cache: 'no-store', referrerPolicy: 'no-referrer'`. Je to jeden řádek v souboru,
který vlastníme, a nezávisí na tom, jestli backend spolupracuje.

### P6 — `Avatar` renderuje libovolné vzdálené URL (Střední dnes, Vysoká po napojení)

`packages/ui/src/Avatar/index.tsx:20`:

```tsx
if (src) return <img src={src} alt={alt} style={{ ...baseStyle, objectFit: 'cover' }} />;
```

Žádné `referrerPolicy`, žádná validace originu. Zároveň
`contracts/openapi.snapshot.yaml:185` má `UpdateProfileRequest.avatar` jako
`{ type: string, format: uri }` — tedy **URL, které si nastaví sám uživatel**.

**Scénář.** Až se avatary napojí na reálná data, nepřátelský člen si nastaví
avatar na `https://jeho-server/pixel.png`. Od té chvíle mu do logu padá IP adresa
a časová značka každého, kdo otevře jeho profil nebo uvidí jeho příspěvek ve
feedu. To je plnohodnotný deanonymizační nástroj vestavěný do produktu, dostupný
komukoli s účtem, a v tomto modelu hrozby zdaleka nejnebezpečnější věc, kterou
lze klientovi dovolit. Dnes nic neuniká, protože produktový kód žádné vzdálené
`src` nepředává (jediné je ve story, viz P10).

**Minimální oprava.** Kontrakt musí `avatar` řešit jako upload, ne jako URL:
médium se ukládá a servíruje z vlastního originu, klient vzdálené URL nikdy
nerenderuje. Do té doby jako záplata `referrerPolicy="no-referrer"` na `<img>` a
odmítnutí `src`, které nemíří na vlastní origin. Kontrakt vlastní `architect`.

### P7 — Souhlas s 18+ vydrží navždy (Nízká–střední)

`packages/ui/src/AgeGate/index.tsx:16,42` ukládá `libertin.ageConfirmed = '1'`
do `localStorage`, bez expirace.

**Scénář.** Na sdíleném nebo rodinném počítači se gate nikdy znovu neobjeví.
Kdokoli další, kdo prohlížeč otevře a doklikne se na doménu, projde přímo do
obsahu bez jakéhokoli mezikroku. Gate tím přestává být gate a zbývá z něj záznam,
že někdo v domácnosti souhlas dal.

Vědomě **nenadsazuji** druhou polovinu tohoto tématu: samotný název klíče
`libertin.ageConfirmed` prakticky nic nepřidává, protože devtools řadí storage
podle originu — kdo se do Application → Local Storage dostane, vidí především tu
doménu, a ta prozradí víc než klíč.

**Minimální oprava.** `sessionStorage`, nebo session cookie
(`Secure; SameSite=Lax`, bez `Max-Age`), aby souhlas zanikl se zavřením
prohlížeče. Cookie je potřeba i pro P3 — stejná změna vyřeší obojí.

### P8 — Chybí `Cache-Control` a CSP (Nízká dnes, budoucí riziko)

`apps/web/next.config.mjs:5–11` nedefinuje ani `Cache-Control`, ani
`Content-Security-Policy`. Autentizovaná část dnes neexistuje, takže dnes nic
neuniká — ale je to místo, kde ta kontrola musí být, a `/:path*` teď žádnou cache
politiku nenastavuje.

**Minimální oprava.** Až přijde autentizovaný prefix, doplnit pro něj
`Cache-Control: no-store, no-cache, must-revalidate` a `Pragma: no-cache`
(back/forward cache a proxy). Nezávisle na tom doplnit CSP s
`default-src 'self'` — je to pojistka, která zachytí omylem přidaný pixel,
CDN skript nebo webový font, tedy přesně to, co je dnes chvályhodně nulové (a
`report-only` varianta dá tripwire bez rizika rozbití).

### P9 — `robots.txt` povoluje vše (Nízká dnes, Vysoká po profilech)

`apps/web/src/app/robots.ts:7`: `rules: { userAgent: '*', allow: '/' }`, žádné
`disallow`. Sitemap (`apps/web/src/app/sitemap.ts`) uvádí jen `/` a `/login` —
to je správně.

**Scénář.** Dnes jsou veřejné dvě stránky, takže se nic neindexuje. Jakmile ale
pod tímto appem vzniknou profily nebo stránky akcí, jsou ve výchozím stavu
crawlovatelné — a takhle skončí profil pojmenovaného člověka ve výsledcích
Google, kde ho najde kdokoli, kdo si jeho jméno vygoogluje. To je nejběžnější
způsob, jak se lidé z takových platforem prozradí.

**Minimální oprava.** Přepnout na explicitní allow-list veřejných cest a na
autentizovaných prefixech posílat `X-Robots-Tag: noindex, nofollow, noarchive`
(hlavička je spolehlivější než `robots.txt`, který indexaci nezakazuje, jen
odrazuje).

### P10 — Externí placeholder ve Storybooku (Nízká)

`packages/ui/src/Avatar/Avatar.stories.tsx:11`:

```tsx
export const WithImage: Story = { args: { src: 'https://placehold.co/80', ... } };
```

Do produktu se to nedostane. Ale Storybook je předávací artefakt (smluvní
požadavek **C8**) — kdo ho otevře, včetně objednatele na firemní síti, pošle
požadavek na `placehold.co`. Hlavní důvod to opravit je jiný: je to jediný
vzorový vzdálený `src` v repu, a přesně takové řádky se kopírují do produktového
kódu (viz P6).

**Minimální oprava.** Nahradit inline `data:` SVG nebo lokálním souborem.

### P11 — `.gitignore` nechytá všechny env soubory (Nízká–střední)

`.gitignore:7–8` ignoruje `*.env.local` a `.env`, ale ne `.env.production`,
`.env.development` ani `.env.staging`. Repo je **veřejné**. Stačí, aby někdo
založil `.env.production` s přístupem k databázi, a commitne se to bez varování.

**Minimální oprava.** Nahradit vzorem `.env*` s výjimkou `!.env.example`.
Vlastní `devops`.

---

## Budoucí rizika a chybějící kontroly

Tyto funkce **v repu nejsou** — ověřeno grepy, které v `apps` a `packages`
nevrátily nic (všechny zásahy byly jen v `.next` artefaktech). Nejsou to tedy
nálezy. Je to seznam, který musí být splněný, než se daná funkce označí za
hotovou; akceptační kritérium E14-T4 je jmenovitě zmiňuje.

**F1 — Odstranění EXIF z fotek (kritické, hned jak vznikne upload).**
Žádný upload neexistuje (grep `multipart|FormData|ImagePicker|upload` = nic).
Až vznikne: strip **na serveru** a re-encode celého obrázku, nikdy jen
klientsky. Nejde pouze o GPS — EXIF/XMP/IPTC nese i jméno vlastníka fotoaparátu,
sériové číslo těla (spojí zdánlivě nesouvisející účty), přesný čas a někdy
miniaturu původního, neupraveného snímku. Pro tuto komunitu je to
nejcennější chybějící kontrola.

**F2 — Text notifikací na zamčené obrazovce.** Žádný push kód ani závislost
(`apps/mobile/package.json` neobsahuje `expo-notifications`). Výchozí stav musí
být notifikace bez obsahu: „Nová zpráva“, bez jména odesílatele, bez náhledu
textu, bez avataru. Android `visibility: secret`, iOS skrytý náhled; jméno
odesílatele se dopočítá až po odemčení. Notifikace na zamčené obrazovce je
nejpravděpodobnější způsob, jak členovi prozradí platformu partner, který mu jen
vezme telefon ze stolu.

**F3 — Maskování v přepínači aplikací a ochrana proti screenshotu.**
`apps/mobile/app.json` nemá žádnou nativní konfiguraci (10 řádků, jen `name`,
`slug`, `splash`). Android ukládá náhled poslední obrazovky do „recents“, iOS
dělá snapshot při odchodu do pozadí — na sdíleném nebo zabaveném telefonu je
tam vidět feed. Potřeba `FLAG_SECURE` (Android) a blur overlay na
`willResignActive` (iOS), plus `android.allowBackup: false`, aby se data
aplikace nedostala do cloudové zálohy.

**F4 — Identita aplikace na domovské obrazovce (rozhodnutí pro objednatele).**
Aplikace se jmenuje `Libertin` a má splash `#F20B49`. Ikona se jménem na domovské
obrazovce je sama o sobě prozrazení — je vidět, kdykoli si někdo půjčí telefon.
Smlouva o tom nic neříká, takže si to tato role **nevymýšlí**: patří to jako
otázka objednateli (neutrální jméno/ikona, případně „disguise“ varianta), ne jako
domněnka do kódu.

**F5 — Mapy a lokace akcí.** Žádný mapový kód (grep `mapbox|leaflet|geoloc` =
nic), a `Permissions-Policy` dnes geolokaci v prohlížeči blokuje úplně. Až budou
mít akce lokaci: **žádný poskytovatel dlaždic třetí strany na autentizované
stránce** — každý požadavek na dlaždici prozradí poskytovateli prohlížené
souřadnice, IP a čas, takže i bez obsahu ví, kdo si kde plánuje jít na akci.
Dlaždice self-hostovat a adresu do potvrzené registrace zobrazovat jen na úrovni
obce.

**F6 — Úložiště session a 2FA.** Dnes se nepersistuje nic (ověřeno grepem) — to
je pro sdílené zařízení nejlepší možný stav. Až přijde „zůstat přihlášen“ a 2FA
(**B4.2**): na mobilu výhradně `expo-secure-store` (Keychain/Keystore), nikdy
`AsyncStorage`, který je na disku v plaintextu a vyčte se z každé zálohy.

---

## Co je už teď v pořádku

Tohle není zdvořilost — jsou to vlastnosti, které se při dalších změnách nesmí
ztratit, takže je potřeba je mít napsané.

- **`Referrer-Policy: same-origin`** je opravdu odesílán (ověřeno výstupem
  `headers()`). Žádný externí web se nedozví, že návštěvník přišel odsud. To je
  přesně ten správný instinkt a řeší celou kategorii úniků.
- **`Permissions-Policy: camera=(), microphone=(), geolocation=()`** — geolokace
  je zakázaná na úrovni prohlížeče, ne jen nepoužitá.
- **`X-Frame-Options: DENY`** — web nelze vložit do rámu, takže age gate ani
  přihlášení nejde obalit cizí stránkou.
- **Nula třetích stran za běhu.** Žádná analytika, žádný Sentry, žádný tag
  manager, žádné CDN, **žádné webové fonty** (`apps/web/src/app/globals.css:11`
  používá `system-ui`), žádný vzdálený obrázek v produktovém kódu. Toto je
  nejsilnější vlastnost současného kódu z hlediska soukromí — celý strom
  závislostí `apps/web` je `next`, `react`, `react-dom`, `i18next`,
  `react-i18next` a vlastní balíky. Držet to takhle.
- **Žádné údaje v URL.** `login`, `register` i `verify` jsou POST s JSON tělem;
  token jde v `Authorization` hlavičce (`packages/api/src/client.ts:20`), ne
  v query stringu. Nic z toho tedy nekončí v logu serveru, v `Referer` ani
  v historii.
- **Na mobilu se nepersistuje nic.** Token žije jen v React state; po zabití
  aplikace nezůstane na zařízení nic.
- **E-maily se interpolují, nehardcodují.**
  `packages/ui/src/native/screens/VerifyEmailScreen.tsx:23` používá
  `translate('verify.body', { email })`, mock data jsou na `example.com`. Stará
  chyba z legacy verify screen se nevrátila.
- **`<title>` na `/login` je neutrální** — `Přihlášení | Libertin` (ověřeno
  v buildu). Šablona `%s | Libertin` je správný vzor; problém je jen `default`
  (P2).
- **Overlay age gate je neprůhledný** (`--color-surface-dark: #222222`), takže
  po připojení obsah skutečně zakryje — není to průhledný scrim.
- **`.next/` je v `.gitignore`**, takže `previewModeSigningKey` a
  `previewModeEncryptionKey` z `prerender-manifest.json` se do veřejného repa
  nedostanou.

---

## Nálezy mimo vlastnictví této role

Tato role vlastní pouze tento dokument. Nic v kódu nebylo změněno. Opravy patří:

| Nález | Vlastník opravy |
|---|---|
| P1, P6 (kontrakt) | `architect` + `backend` — `contracts/openapi.snapshot.yaml` je zmrazený kontrakt |
| P2, P3 (server-side gate), P8, P9 | `frontend-web` |
| P3 (focus trap, scroll lock), P4, P6 (`referrerPolicy`), P7, P10 | `frontend-web` (balík `packages/ui`) |
| P5 | vlastník `packages/api` |
| P11 | `devops` |
| F1, F2, F3, F5, F6 | `security` (návrh kontroly) + příslušná implementační role |
| F4 | **objednatel** — patří do `decisions` v `docs/backlog.yaml` |

Nad rámec privacy review, ale nalezeno při čtení: `apps/mobile/src/AuthFlow.tsx:35`
obsahuje hardcodovanou českou copy („Přihlášení se nezdařilo. Zkontrolujte
údaje.“) místo i18n klíče, což je porušení konvence z `CLAUDE.md`. Vlastní
`frontend-mobile`.
