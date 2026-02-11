# AI‑Servis Universal Monorepo

This repository contains the universal AI‑Servis monorepo skeleton used to organize modules, containers, CI, docs, scripts, and tests.

## Structure

```
mia-universal/
├── modules/
│   ├── core-orchestrator/
│   ├── ai-audio-assistant/
│   ├── ai-platform-controllers/
│   ├── ai-communications/
│   └── ai-security/
├── containers/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── docker-compose.pi-sim.yml
├── docs/
│   ├── architecture/
│   ├── modules/
│   └── deployment/
├── scripts/
├── tests/
└── ci/
```

## Getting Started

- Ensure pre-commit is installed: `pre-commit install`
- Explore module placeholders under `modules/`
- Compose files live under `containers/`

## Documentation

Project‑wide docs are in the top‑level `docs/` folder and built with MkDocs.

## License

This project is licensed under the terms of the LICENSE in the repository root.
