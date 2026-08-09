# CI pipeline

> Stav: **E11-T2 hotovo** — čtyřstupňová pipeline `install → type-check → test → build`.
> Požadavky smlouvy: **C11.1** (CI pipeline), částečně **C10** (CI/CD na GitLabu).
> Rozhodnutí **D-002** (GitLab vs. GitHub) je stále otevřené — jak to řešíme,
> je popsáno níže v [GitLab vs. GitHub](#gitlab-vs-github).

Soubory, které tento dokument popisuje:

| Soubor | Účel |
|---|---|
| `../../.github/workflows/libertin-ci.yml` | běžící pipeline (GitHub Actions). Leží v **kořeni gitu**, tj. o úroveň výš než `libertin/`. |
| `.gitlab-ci.yml` | překlad téže pipeline do GitLabu — **zatím nespuštěný**, viz [GitLab vs. GitHub](#gitlab-vs-github) |

## Kdy se pipeline spouští

Repozitář je sdílený s nesouvisejícím projektem MIA. Pipeline je proto úzce
ohraničená a **nesmí** se rozšiřovat:

```yaml
on:
  pull_request:
    paths: ['libertin/**', '.github/workflows/libertin-ci.yml']
  push:
    branches: ['claude/libertin-monorepo-setup-VxRLF']
    paths: ['libertin/**', '.github/workflows/libertin-ci.yml']
  workflow_dispatch:
```

- Změna kdekoliv mimo `libertin/**` pipeline nespustí.
- Workflow projektu MIA (`ci.yml`, `android-test.yml`, `security.yml`) mají vlastní
  `paths` filtry, které `libertin/**` neobsahují — nekolidujeme s nimi.
  `main.yml` je jen `workflow_dispatch`.
  **Výjimka, kterou nevlastníme:** `deploy.yml` se spouští na `push` do `main`
  a na tagy `v*` **bez `paths` filtru** — merge Libertinu do `main` ho tedy
  zbytečně nastartuje. Oprava patří majiteli MIA workflow (doplnit `paths-ignore:
  ['libertin/**']`), my do cizích souborů nesaháme.
- `push` je zatím napojený na jednu pracovní branch. **Až se práce sloučí do
  hlavní branche, doplň sem `main` (nebo příslušný název).** Pipeline běží
  i tak na každém pull requestu.
- `concurrency` s `cancel-in-progress: true` ruší předchozí běh téhož ref —
  rychlá zpětná vazba, žádné utrácení runner minut za neaktuální commity.

Pracovní adresář je nastavený globálně:

```yaml
defaults:
  run:
    working-directory: libertin
```

**Kořen pnpm workspace je `libertin/`, ne kořen gitu** (v kořeni gitu žádné
`package.json` není). Proto má i `pnpm/action-setup` explicitní
`package_json_file: libertin/package.json` — odtud si bere připnutou verzi
z pole `packageManager` (`pnpm@10.33.0`).

## Stupně

Každý stupeň je **jeden dokumentovaný příkaz**, ne skript rozházený v YAMLu.
To je záměr: přenos na GitLab (C10) je pak překlad, ne přepis.

| Stupeň | Příkaz v CI | Co dělá |
|---|---|---|
| `install` | `pnpm install --frozen-lockfile` | ověří, že `pnpm-lock.yaml` sedí na `package.json`, a nahřeje cache pnpm store |
| `type-check` | `pnpm type-check` | `turbo run type-check` — `tsc --noEmit` ve všech 6 workspace balíčcích |
| `test` | `pnpm test:all` | root `vitest run` — projede všechny workspace projekty naráz |
| `build` | `pnpm build` | `turbo run build` — dnes produkční `next build` v `apps/web` |

Stupně jsou zřetězené přes `needs:`, takže `test` neběží nad kódem, který
neprošel `type-check`. Každá job si `install` zopakuje; je to levné, protože
pnpm store se drží v cache klíčované hashem `pnpm-lock.yaml`
(`actions/setup-node` s `cache: pnpm`, `cache-dependency-path: libertin/pnpm-lock.yaml`).

Node je připnutý na **22**, `engines` v `package.json` říká `>=20`.

Telemetrie je vypnutá (`NEXT_TELEMETRY_DISABLED`, `TURBO_TELEMETRY_DISABLED`,
`DO_NOT_TRACK`) — build ani test nesmí nic posílat ven. `permissions: contents: read`,
pipeline nemá zápisová práva a nesahá na žádné secrets.

## Jak to zopakovat lokálně

Všechno se pouští z adresáře `libertin/`:

```bash
cd libertin

pnpm install --frozen-lockfile   # stupeň install
pnpm type-check                  # stupeň type-check
pnpm test:all                    # stupeň test
pnpm build                       # stupeň build
```

Když CI spadne, spadne i tohle — jiný příkaz se v pipeline nepouští.

Užitečné varianty:

```bash
pnpm --filter=@libertin/web exec next build   # jen web, bez turba
pnpm --filter=@libertin/ui test               # jen testy UI balíčku
pnpm type-check --force                       # obejde turbo cache
```

### Ověřený výstup (lokálně, 2026-08-09)

```
$ pnpm type-check
 Tasks:    6 successful, 6 total
Cached:    6 cached, 6 total
  Time:    21ms >>> FULL TURBO

$ pnpm test:all
 Test Files  8 passed (8)
      Tests  79 passed (79)
   Duration  3.96s

$ pnpm build
@libertin/web:build: ✓ Generating static pages (7/7)
 Tasks:    1 successful, 1 total
  Time:    17.512s
```

Workflow prošel i `actionlint` v1.7.7 bez nálezu a oba YAML soubory se parsují
(`yaml.safe_load`).

**Co ověřené není:** samotný běh GitHub Actions. Z vývojového prostředí nejde
runner spustit — první skutečný běh uvidíme až na pull requestu. Stejně tak
`pnpm install --frozen-lockfile` nebyl v této iteraci spuštěn (instalace závislostí
je v pracovním stromu zakázaná); lockfile je v repu, verze `9.0`, ale že projde
`--frozen-lockfile`, potvrdí až CI.

## GitLab vs. GitHub

Smlouva (**C10**, **C11.1**) předepisuje GitLab. Repozitář je dnes na GitHubu a
volba je otevřené rozhodnutí objednatele — **D-002** v `backlog.yaml`. Nechceme
ani obcházet smlouvu, ani nechat branch bez kontroly, takže:

1. **Běží GitHub Actions** — `.github/workflows/libertin-ci.yml`. Reálně kontroluje
   každý PR už dnes.
2. **`.gitlab-ci.yml` existuje jako věrný překlad** týchž čtyř stupňů
   (`stages: install, type-check, test, build`, cache pnpm store klíčovaná
   `pnpm-lock.yaml`, `image: node:22-bookworm-slim`, `corepack enable`).
   **Nikdy nespuštěný** — GitLab runner tu nemáme. Dokud nedoběhne zeleně na
   skutečném runneru, ber ho jako revidovaný, ne ověřený.
3. Otevřený předpoklad v `.gitlab-ci.yml`: je psaný pro repozitář, jehož kořen
   **je** kořen pnpm workspace. Pokud se na GitLab přenese i dnešní vnoření
   (`libertin/` jako podadresář), musí se doplnit `cd libertin` do
   `default.before_script` a `changes:` klauzule do pravidel. Je to popsané
   v komentáři přímo v souboru.

Protože každý stupeň je jeden příkaz, migrace znamená přepsat obal, ne pipeline.

## Co pipeline záměrně nepokrývá

Nic z toho není opomenutí — každá položka má vlastní task a nechceme tvrdit
pokrytí, které neexistuje.

| Chybí | Proč / kde to je |
|---|---|
| **E2E testy hlavních toků** (Playwright) | **E11-T5**, `blocked_by: E11-T2`. Až budou, přidají se jako pátý stupeň za `build`. |
| **Výkonnostní brána ≤ 1,5 s** (k6, C12.1) | **E11-T4**, `blocked_by: E9-T3`. Tvrdá akceptační podmínka smlouvy, dnes ji **nic neměří**. |
| **Contract drift proti živému API** | **E11-T3**. `packages/api` je ručně psaný proti `contracts/openapi.snapshot.yaml`, žádný codegen. Shodu dnes drží jen disciplína — CI ji nekontroluje. |
| **Lint jako samostatná brána** | `pnpm lint` má dnes obsah jen pro `apps/web` (`next lint`) a ten se stejně pouští uvnitř `next build`. Samostatný stupeň se přidá, až bude lint nakonfigurovaný napříč balíčky. |
| **Build mobilní aplikace** (Expo) | `apps/mobile` má jen `type-check` — ten v CI běží. EAS build je věc E10. |
| **Storybook build** | `pnpm --filter=@libertin/ui build-storybook` se v CI nepouští. |
| **Měření pokrytí** | **E11-T6**, `blocked_by: E11-T5`. |
| **Bezpečnostní scan závislostí, SBOM** | Není zatím zadaný task; `pnpm audit` v pipeline není. |
| **Deploy / CD** | Pipeline je čistě CI. Nic nenasazuje, nemá zápisová oprávnění ani secrets. Nasazení řeší `docs/deployment.md` a Ansible (**C11.2**). |

## Diskrétnost

Logy běhů CI jsou u veřejného repozitáře veřejné. Do výstupu pipeline proto
nesmí protéct nic o členech — dnes je to bezpečné, protože testy běží proti MSW
mockům a build nepotřebuje žádné přihlašovací údaje. **Až se do CI dostane
cokoliv, co se dotýká reálných dat nebo živého API (E11-T3), musí to jít přes
secrets a výstup se musí maskovat.**
