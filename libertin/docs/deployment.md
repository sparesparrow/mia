# Nasazení — web (kontejner)

> Stav: **E10-T1 hotovo** — produkční image webu + Compose skelet.
> Požadavky smlouvy: **C4** (Docker image), **C3.1** (oddělené kontejnery),
> **C3.3/C3.4** (minimální image, CDN), **C9** (rolling updates).
> Co ještě chybí, je vypsané na konci — nic z toho si nevymýšlíme jako hotové.

Soubory, které tento dokument popisuje:

| Soubor | Účel |
|---|---|
| `apps/web/Dockerfile` | produkční image Next.js frontendu (multi-stage) |
| `apps/web/.dockerignore` | specifikace ignore setu pro build context (viz [Ignore set](#ignore-set)) |
| `docker-compose.yml` | topologie kontejnerů — dnes jen `web`, s vyznačenými rozšiřovacími body |

## Rychlý start

```bash
# build (vždy z korene repozitáře — pnpm potřebuje root lockfile)
docker compose build web

# běh
docker compose up -d web
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/robots.txt   # -> 200

# validace samotného Compose souboru
docker compose config
```

Bez Compose:

```bash
docker build -f apps/web/Dockerfile -t libertin/web:local .
docker run --rm -p 3000:3000 libertin/web:local
```

## Proměnné prostředí

Compose čte gitignorovaný `./.env` v korenu repozitáře. **Žádné tajemství
nepatří do `docker-compose.yml` ani do image — repozitář je veřejný.**

### Build-time (zapékají se do image)

| Proměnná | Default | Význam |
|---|---|---|
| `NEXT_PUBLIC_SITE_URL` | prázdné → fallback v kódu | Absolutní URL webu. `NEXT_PUBLIC_*` Next inlinuje do klientského bundlu **při buildu**, takže image je závislý na prostředí — pro každé prostředí se buildí vlastní tag. Používá se v `robots.txt` a `sitemap.xml`. |
| `NODE_IMAGE` | `node:22-alpine` | Base image. V produkci se pinuje digestem: `node:22-alpine@sha256:…` (reprodukovatelnost pro C11.2 a předání C8). |
| `PNPM_VERSION` | `10.33.0` | Musí odpovídat pnpm, které vygenerovalo `pnpm-lock.yaml` (lockfileVersion 9.0). |

### Runtime

| Proměnná | Default | Význam |
|---|---|---|
| `PORT` | `3000` | Port uvnitř kontejneru. Používá ho i `HEALTHCHECK`. |
| `HOSTNAME` | `0.0.0.0` | Bind adresa Node serveru. |
| `NODE_ENV` | `production` | Nepřepisovat. |
| `TZ` | `Europe/Prague` | Časová zóna kontejneru. |
| `WEB_PORT` | `3000` | Port na hostu, který Compose publikuje. |
| `WEB_IMAGE` / `WEB_TAG` | `libertin/web` / `local` | Jméno a tag image (pro registry a rolling deploy). |

Šablonu `.env` zatím repozitář neobsahuje (`.env.example` není v ownershipu
tohoto tasku — viz [Nálezy k předání](#nálezy-k-předání)). Minimum pro produkci:

```dotenv
NEXT_PUBLIC_SITE_URL=https://<verejny-host>
NODE_IMAGE=node:22-alpine@sha256:<digest>
WEB_IMAGE=<registry>/libertin/web
WEB_TAG=<git-sha>
WEB_PORT=3000
TZ=Europe/Prague
```

## Jak je image postavený

Čtyři stage, každá s jediným úkolem:

| Stage | Co dělá |
|---|---|
| `base` | Node + pnpm přes corepack. Žádný kód aplikace → cachuje se napříč buildy. |
| `deps` | `pnpm install --frozen-lockfile --filter=@libertin/web...`. Kopírují se jen manifesty, takže změna kódu neinvaliduje install. Ne `--prod` — `next build` potřebuje TypeScript. |
| `build` | Zkompiluje app do **Next standalone** výstupu (traced server). |
| `runtime` | Jen Node + výstup buildu. Bez pnpm, bez corepacku, bez dev toolchainu, bez zdrojáků. Běží jako neprivilegovaný uživatel `node` (uid/gid 1000). |

### Proč standalone (a proč se kvůli tomu ohýbá next.config)

Měřeno v tomto repozitáři:

| Varianta runtime | Velikost `/app` | Velikost image |
|---|---|---|
| `pnpm install --prod` tree + `next start` | 537 MB (z toho 533 MB `node_modules`) | **954 MB** |
| Next standalone (traced server) | 24,8 MB | **264 MB** (z toho 232 MB je base `node:22-alpine`) |

Ten rozdíl není Next, ale `auto-install-peers=true` v `.npmrc`: `react-i18next` a
`@libertin/ui` mají `react-native` jako *optional peer*, takže se do pnpm store
nainstaluje `react-native` (83 MB), `jsc-android` (32 MB), `react-devtools-core`
(18 MB) a `typescript` (23 MB) — i v produkční instalaci. Standalone build tohle
obchází, protože do image jde jen to, co server skutečně `require`-uje.

`apps/web/next.config.mjs` **nemá** `output: 'standalone'` a není v ownershipu
tasku E10-T1. Build stage proto zabalí konfiguraci aplikace a přidá jen tuhle
jedinou volbu:

```dockerfile
RUN cd apps/web \
 && mv next.config.mjs next.config.source.mjs \
 && printf '%s\n' \
      "import base from './next.config.source.mjs';" \
      "export default { ...base, output: 'standalone' };" \
      > next.config.mjs
```

Zdrojová konfigurace zůstává jediným zdrojem pravdy pro všechno ostatní
(security headers, `transpilePackages`). **Jakmile `frontend-web` doplní
`output: 'standalone'` do `next.config.mjs`, tento krok z Dockerfile zmizí.**

### Co se do image záměrně nedostane

- `mockServiceWorker.js` — MSW je vývojový mock. Service worker v produkci by
  potichu odchytával provoz členů; build ho maže.
- `.next/cache` (build scratch), dev dependencies, testy, Storybook, zdrojáky.
- Cokoli z `apps/mobile` (kromě `package.json`, který potřebuje
  `--frozen-lockfile` k validaci lockfilu).

## CDN a statické assety (C3.3, C3.4)

- Next servíruje klientské assety z `/_next/static/**` s obsahovým hashem v
  názvu a odpovědí `Cache-Control: public, max-age=31536000, immutable`
  (ověřeno níže). Tuhle cestu má reverzní proxy / CDN cachovat bez revalidace.
- HTML odpovědi cachovat **ne** — obsahují stav přihlášení a jsou to data členů.
- Assety lze při deployi nahrát na CDN a nastavit `assetPrefix`; to je změna
  `next.config.mjs`, kterou tento task nevlastní.
- Diskrétnost: CDN logy obsahují IP členů. Externí CDN je v konfliktu s C2
  (on-premise maximum) — rozhodnutí patří do D-004, dokud není, počítá se
  s vlastní reverzní proxou.

## Healthcheck a rolling update (C9)

- `HEALTHCHECK` v image tahá `GET /robots.txt` — veřejná, levná route bez age
  gate a bez databáze. Je v image (ne jen v Compose), takže platí i pro Swarm,
  Ansible `docker run` a k8s probes.
- Aplikace **nemá** dedikovaný `/api/health` endpoint. `robots.txt` je náhrada,
  ne ekvivalent — neříká nic o dostupnosti backendu. Nález k předání.
- `STOPSIGNAL SIGTERM`, PID 1 je `next-server` (žádný wrapper package manageru),
  takže `docker stop` ukončí server graceful — měřeno **88 ms, exit code 0**.
- **Compose sám o sobě zero-downtime neumí.** Publikovaný port je jeden a
  `docker compose up --scale web=2` selže na `Bind for 0.0.0.0:3200 failed: port
  is already allocated` (ověřeno). Rolling restart potřebuje load balancer před
  webem a víc replik — to je E10-T4. `deploy:` blok pro Swarm
  (`order: start-first`) je v `docker-compose.yml` připravený zakomentovaný.
- Do té doby je nejbližší varianta krátký výpadek:
  `docker compose up -d --no-deps --pull always web`.

## Hardening kontejneru

V `docker-compose.yml`:

- `read_only: true` (ověřeno: `touch /app/x` → `Read-only file system`),
- `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`,
- žádné volumy — web je stateless, není co zálohovat,
- `tmpfs` pro `/tmp` a `/app/apps/web/.next/cache`. **Pozor:** Docker vytváří
  tmpfs jako root/0755, takže bez `uid=1000,gid=1000` dostane server při zápisu
  do ISR cache `EACCES`. Tenhle problém se v prvním běhu skutečně projevil a je
  proto v Compose explicitně řešený.
- `logging: json-file` s rotací (10 MB × 5). Access logy identifikují členy —
  zůstávají lokální, rotované a **nikdy se neposílají do cizí SaaS** (C2).

## Ignore set

Build musí běžet s **korenem repozitáře** jako contextem. BuildKit hledá ignore
soubor v tomhle pořadí:

1. `apps/web/Dockerfile.dockerignore`
2. `./.dockerignore` (koren repozitáře)

Ani jednu z těch cest task E10-T1 nevlastní, takže `apps/web/.dockerignore` je
dnes **specifikace** ignore setu, ne automaticky aplikovaný soubor. Buildy jsou
i tak korektní — `apps/web/Dockerfile` kopíruje zdrojáky cestu po cestě, ne
`COPY . .` — jen se do daemona přenáší nesmyslně velký context.

Aktivace lokálně, bez zásahu do souborů jiných rolí:

```bash
ln -s .dockerignore apps/web/Dockerfile.dockerignore
```

Trvale: obsah `apps/web/.dockerignore` překopírovat do `./.dockerignore`
(nález k předání, E10-T2).

## Mobilní build (Expo)

Task E10-T1 nese v názvu i mobilní pipeline. Realita, kterou je potřeba říct
narovinu: **mobilní build se nekontejnerizuje stejně jako web.**

- Android build lze v Dockeru dělat (JDK + Android SDK image), iOS build
  vyžaduje macOS runner — v kontejneru legálně ani technicky ne.
- `apps/mobile` je Expo (`expo ~52`) bez `eas.json`; není rozhodnuté, jestli
  se buildí přes EAS (cloud, mimo C2) nebo lokálně přes `expo prebuild` +
  Gradle/Xcode. To je vstup pro rozhodnutí o hostingu/CI (D-002, D-004).
- CI definice (`.gitlab-ci.yml`) tento task nevlastní — je to E11/C10.

Doporučený tvar, až se rozhodne: `pnpm --filter=@libertin/mobile` build v
Dockeru pro Android (reprodukovatelný, on-premise runner), macOS runner pro iOS,
artefakty do stejné registry/artefakt storage jako webový image.

## Ověřeno (skutečný výstup)

Prostředí: Docker 29.3.1, Compose v5.1.1, `node:22-alpine`.
Egress tohoto sandboxu jde přes TLS-terminující proxy, takže build běžel
s `--build-arg NODE_IMAGE=<base s CA proxy>` a `--network host`; **žádná jiná
odchylka od souborů v repozitáři**.

```
$ docker compose config
name: libertin
services:
  web:
    build: {context: /home/user/mia/libertin, dockerfile: apps/web/Dockerfile, …}
    …
compose config OK

$ docker compose up -d --build
 Image libertin/web:local Built
 Container libertin-web-1 Started

$ docker compose ps
libertin-web-1  Up 8 seconds (healthy)  0.0.0.0:3200->3000/tcp

$ docker images libertin/web:local --format '{{.Size}}'
264MB

$ docker image inspect libertin/web:local -f 'User={{.Config.User}} Cmd={{.Config.Cmd}}'
User=node Cmd=[node apps/web/server.js]

$ docker exec libertin-web-1 sh -c 'id -un; ps -o pid,user,args'
node
PID   USER     COMMAND
    1 node     next-server (v14.2.35)

$ curl -o /dev/null -w '%{http_code} time=%{time_total}s\n' http://127.0.0.1:3200/
200 time=0.065939s
$ curl -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3200/robots.txt
200
$ curl -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3200/login
200

$ curl -D - -o /dev/null http://127.0.0.1:3200/ | grep -iE 'referrer|strict-transport|x-frame'
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Referrer-Policy: same-origin
X-Frame-Options: DENY

$ curl -D - -o /dev/null http://127.0.0.1:3200/_next/static/css/14486c8123372251.css | grep -i cache-control
Cache-Control: public, max-age=31536000, immutable

$ docker exec libertin-web-1 sh -c 'touch /app/x; touch /app/apps/web/.next/cache/probe && echo OK'
touch: /app/x: Read-only file system
ISR cache writable OK

$ docker exec libertin-web-1 ls /app/apps/web/public/mockServiceWorker.js
ls: … No such file or directory

$ docker inspect libertin-web-1 -f '{{.State.Health.Status}}'
healthy

$ docker stop libertin-web-1     # graceful
stop took 88 ms, ExitCode=0
```

## Co ještě chybí do produkce

Nic z následujícího tento task neřeší a **nepředstírá, že je hotové**:

| Chybí | Kde se to dělá |
|---|---|
| Backend, DB, Redis, S3 storage, mail — propojení kontejnerů | E10-T2 (blokováno D-003) |
| Ansible IaC — celý systém ze zdrojového textu (C11.2) | E10-T3 (blokováno D-004) |
| HA, load balancer, multi-node DB, skutečné rolling restarty (C5, C9) | E10-T4 |
| Zálohy, verzování obsahu, selektivní i PITR obnova (B5) | E10-T5 |
| TLS terminace, reverzní proxy, certifikáty (A4) | E10-T4 |
| Šifrování at-rest a správa klíčů (B4.3, B4.4) | epika bezpečnosti |
| CI/CD, registry, podepisování a skenování image (C10) | E11 |
| Secret management (dnes jen gitignorovaný `.env`) | E10-T3 |
| Rozpočet odezvy ≤ 1,5 s pod zátěží (C12.1) — k6 měření | QA |

## Nálezy k předání

Věci mimo ownership tasku E10-T1, které by měly vzniknout jako samostatná práce:

1. **`output: 'standalone'` do `apps/web/next.config.mjs`** (frontend-web) —
   zruší obcházení konfigurace v Dockerfile.
2. **`./.dockerignore` v korenu repozitáře** — obsah je připravený v
   `apps/web/.dockerignore`. Zmenší build context.
3. **`/api/health` route** (frontend-web/backend) — healthcheck, který opravdu
   vypovídá o připravenosti (dnes se testuje `robots.txt`).
4. **`.npmrc`: `auto-install-peers`** a `react-native` jako optional peer v
   `packages/ui` — kvůli tomu má produkční pnpm strom 533 MB místo ~25 MB.
   Standalone build to obchází, ale CI a lokální instalace tím trpí dál.
5. **`packageManager` v root `package.json`** — corepack by si pnpm pinoval sám
   a `PNPM_VERSION` v Dockerfile by nebyl potřeba.
6. **`.env.example`** se seznamem proměnných z tohoto dokumentu.
7. **MSW v produkčním bundlu** — import je dynamický (dobře), ale chunk se
   emituje; stálo by za to ho v produkci úplně vyřadit (C3.4, méně requestů).
