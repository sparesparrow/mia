# Provozní řád týmu agentů

Jak se na Libertinu pracuje systematicky, autonomně a bez kolizí.

## Zdroje pravdy

| Co | Kde |
|---|---|
| Rozsah a stav práce | `docs/backlog.yaml` — **jediný** zdroj pravdy |
| Mapování na smlouvu | `docs/requirements-traceability.md` (kódy A/B/C) |
| Rozhodnutí | `docs/adr/NNNN-slug.md` |
| Stav legacy platformy | `docs/live-audit.md` |
| Pracovní dohoda | `CLAUDE.md` |
| Definice rolí | `.claude/agents/*.md` |

Nic se nepovažuje za hotové, dokud to není `done` v backlogu **a** ověřené.

## Role

| Role | Vlastní |
|---|---|
| `architect` | ADR, API kontrakt, průřezová rozhodnutí, integrita backlogu |
| `frontend-web` | Next.js web, admin/dashboard UI, webové komponenty |
| `frontend-mobile` | Expo/RN aplikace, native primitiva, push, secure storage |
| `backend` | API, datový model, oprávnění, auditní log, migrace dat |
| `devops` | Docker/Compose, Ansible IaC, CI/CD, zálohy, HA, úložiště |
| `security` | 2FA, šifrování a klíče, GDPR, adversariální privacy review |
| `qa` | testy (unit/komponentové/e2e), contract-check, k6 budget 1,5 s |
| `reviewer` | adversariální review — konvence, čeština, privacy, korektnost |
| `docs` | architektura, manuály, in-app nápověda, předatelnost |

Role jsou záměrně úzké. Agent, který si sáhne mimo své pásmo, vytváří konflikty
— pokud práce přesahuje, vrátí to jako nález, ne jako commit.

## Iterační cyklus

Každá iterace (ať ji spustí loop, nebo člověk) má stejný tvar:

1. **Vyber práci** — z `backlog.yaml` vezmi tasky se `status: todo`, jejichž
   `blocked_by` jsou všechny `done`. Nikdy nesahej na `blocked`.
2. **Rozděl podle rolí** — task jde té roli, která ho v backlogu vlastní.
   Tasky v různých `scope` mohou běžet paralelně; tasky ve stejných souborech ne.
3. **Implementuj** — role pracuje samostatně v mezích svého mandátu.
4. **Ověř** — `pnpm type-check` vždy; `next build` při zásahu do webu; testy,
   pokud existují. Skutečný výstup, ne domněnka.
5. **Review** — `reviewer` projede diff adversariálně. Nálezy se opraví ještě
   před commitem.
6. **Zapiš stav** — task na `done` (nebo `blocked` s důvodem), commit + push na
   pracovní branch. Rozsah, který se během práce ukázal, se doplní do backlogu.

## Paralelismus a kolize

- Tasky se **liší v `scope`** → mohou běžet současně.
- Tasky ve **stejných souborech** → serializovat, jinak si přepíšou práci.
- Sdílené soubory s vysokým rizikem kolize: `packages/i18n/locales.json`,
  `packages/ui/src/index.ts`, `contracts/openapi.snapshot.yaml`,
  `docs/backlog.yaml`. Změny sem se dělají malé a hned commitují.

## Pravidla, která platí pro každou roli

1. **Nikdy netvrď hotovo bez ověření.** Když je něco červené, řekni to s
   výstupem. Přeskočený krok se přiznává.
2. **Diskrétnost je feature.** Členům reálně hrozí prozrazení — u každé změny se
   ptej, co může uniknout.
3. **Smlouva je zadání.** Nevymýšlej rozsah, ale ani tiše nevypouštěj požadavek.
   Když smlouva a dobré inženýrství kolidují, popiš obojí a eskaluj.
4. **Konflikt hlas, neřeš potichu.** Blokující rozhodnutí patří objednateli —
   zapiš do `decisions` v backlogu.
5. **Repo je veřejné.** Žádná čísla smluv, jména, přihlašovací údaje, interní
   hostnames ani osobní data.

## Blokující rozhodnutí

`decisions` v `backlog.yaml` drží rozhodnutí, která vlastní objednatel. Dokud je
nerozhodne, závislé tasky zůstávají `blocked` a **nikdo je neobchází domněnkou**.
Aktuálně blokuje: Figma editor access (D-001), GitLab vs GitHub (D-002), backend
stack (D-003), hosting (D-004), AI moderace mimo smlouvu (D-005).

## Výzkum

Otevřené technické otázky jsou v `research` v backlogu (RES-*). Zpracovávají se
odděleně a jejich výstupem je **ADR**, ne kód. Rozhodnutí bez podloženého
výzkumu se do ADR nezapisuje jako fakt.
