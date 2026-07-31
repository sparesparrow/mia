# Libertin — production image for the Next.js web front-end (apps/web).
#
# Contract traceability
#   C4    each component ships as a Docker image, wired by Docker Compose
#   C3.1  the front-end is its own container — no backend, DB or storage here
#   C3.3  minimal image (~264 MB measured, 232 MB of it the node:22-alpine
#         base; no dev toolchain, no source tree) and
#         fingerprinted static assets a CDN can cache immutably
#   C9    one Node process as PID 1 that honours SIGTERM, so a rolling restart
#         drains connections instead of dropping them
#
# Build from the REPOSITORY ROOT — the pnpm workspace needs the root lockfile:
#   docker build -f apps/web/Dockerfile -t libertin/web:local .
#   docker compose build web
#
# See docs/deployment.md for build arguments, runtime variables and what is
# still missing before this is production infrastructure.

# Base image is an ARG so an operator can pin a digest per environment
# (reproducibility for C11.2, handover C8), e.g.
#   --build-arg NODE_IMAGE=node:22-alpine@sha256:<digest>
ARG NODE_IMAGE=node:22-alpine

# ---------------------------------------------------------------------------
# base — toolchain only, no application code, so it caches across builds
# ---------------------------------------------------------------------------
FROM ${NODE_IMAGE} AS base

# Must stay equal to "packageManager" in the root package.json — corepack
# enforces that field over an activated version, so a mismatch fails the build.
ARG PNPM_VERSION=10.33.0

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH \
    NEXT_TELEMETRY_DISABLED=1 \
    CI=1
RUN corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate
WORKDIR /app

# ---------------------------------------------------------------------------
# deps — install for the web app and the workspace packages it depends on.
# Only manifests are copied here, so touching source code does not re-run the
# install. Not --prod: `next build` needs typescript and @types/*.
# ---------------------------------------------------------------------------
FROM base AS deps

COPY pnpm-lock.yaml pnpm-workspace.yaml package.json .npmrc turbo.json ./
# Every workspace manifest must be present or --frozen-lockfile rejects the
# lockfile as outdated, even for a filtered install.
COPY apps/web/package.json       apps/web/
COPY apps/mobile/package.json    apps/mobile/
COPY packages/api/package.json   packages/api/
COPY packages/i18n/package.json  packages/i18n/
COPY packages/theme/package.json packages/theme/
COPY packages/ui/package.json    packages/ui/

RUN --mount=type=cache,id=libertin-pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter=@libertin/web...

# ---------------------------------------------------------------------------
# build — compile the app and trace exactly the files the server needs.
#
# Sources are copied path by path on purpose: the repository root has no
# .dockerignore (that file is not owned by task E10-T1), so a wholesale
# `COPY . .` would drag every workspace's node_modules and .next into the
# build. See apps/web/.dockerignore for the ignore set that should live at the
# root, and docs/deployment.md.
# ---------------------------------------------------------------------------
FROM deps AS build

# NEXT_PUBLIC_* values are inlined into the client bundle at build time, so the
# resulting image is environment-specific. Pass it per environment:
#   --build-arg NEXT_PUBLIC_SITE_URL=https://<host>
# The default must be a real URL, NOT empty: `ENV X=${ARG}` with an unset ARG
# defines X as an empty string, and `process.env.X ?? default` in
# src/app/{robots,sitemap}.ts only falls back on undefined — an empty value
# would ship a broken sitemap/robots host.
ARG NEXT_PUBLIC_SITE_URL=https://libertin.cz
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL} \
    NODE_ENV=production

COPY tsconfig.json ./
COPY packages/theme/index.ts packages/theme/native.ts packages/theme/theme.ts \
     packages/theme/tokens.css packages/theme/tsconfig.json packages/theme/
COPY packages/i18n/index.ts packages/i18n/dict.ts packages/i18n/locales.json \
     packages/i18n/tsconfig.json packages/i18n/
COPY packages/api/tsconfig.json packages/api/
COPY packages/api/src packages/api/src
COPY packages/ui/tsconfig.json packages/ui/
COPY packages/ui/src packages/ui/src
COPY packages/ui/icons packages/ui/icons
COPY apps/web/next.config.mjs apps/web/tsconfig.json apps/web/next-env.d.ts apps/web/
COPY apps/web/public apps/web/public
COPY apps/web/src apps/web/src

# Next's standalone output is what keeps this image small: it emits a traced
# server plus only the node_modules files actually reached (23 MB here) instead
# of the whole pnpm production tree (533 MB — `auto-install-peers=true` in
# .npmrc drags react-native, jsc-android and typescript into the store as
# optional peers of react-i18next and @libertin/ui).
#
# apps/web/next.config.mjs is NOT owned by task E10-T1 and does not set
# `output: 'standalone'`, so the build wraps the app's own config and adds only
# that one option — the repo file stays the source of truth for everything else.
# FOLLOW-UP: move `output: 'standalone'` into apps/web/next.config.mjs (owner:
# frontend-web) and delete this step.
RUN cd apps/web \
 && mv next.config.mjs next.config.source.mjs \
 && printf '%s\n' \
      "import base from './next.config.source.mjs';" \
      "export default { ...base, output: 'standalone' };" \
      > next.config.mjs

# The MSW service worker is a development mock. A stray service worker in
# production would silently intercept member traffic — it must never ship.
RUN rm -f apps/web/public/mockServiceWorker.js

RUN pnpm --filter=@libertin/web build

# ---------------------------------------------------------------------------
# runtime — Node plus the traced server output. No pnpm and no source tree.
# Note: the base image still provides npm/npx/corepack/yarn; we do not claim
# otherwise. Strip them here if the threat model requires it. Runs as the unprivileged `node` user (uid/gid
# 1000) that the official image already provides.
# ---------------------------------------------------------------------------
FROM ${NODE_IMAGE} AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app

# Traced server + the minimal node_modules Next resolved for it.
COPY --from=build --chown=node:node /app/apps/web/.next/standalone/ ./
# Client assets: content-hashed under /_next/static/** -> safe to hand to a CDN
# with `Cache-Control: public, max-age=31536000, immutable` (C3.3, C3.4).
COPY --from=build --chown=node:node /app/apps/web/.next/static/ ./apps/web/.next/static/
COPY --from=build --chown=node:node /app/apps/web/public/ ./apps/web/public/

# ISR / image-optimisation cache. Pre-created and owned by `node` so the
# container can run with a read-only root filesystem plus a tmpfs mounted here
# (docker-compose.yml does exactly that).
RUN mkdir -p /app/apps/web/.next/cache && chown -R node:node /app/apps/web/.next

USER node
EXPOSE 3000

# /robots.txt is a cheap always-public route (no age gate, no DB, no member
# data) — it proves the Node server answers.
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD wget -q --spider "http://127.0.0.1:${PORT}/robots.txt" || exit 1

STOPSIGNAL SIGTERM

# The traced server is started directly: node stays PID 1, so SIGTERM from a
# rolling restart reaches the HTTP server instead of a package-manager wrapper.
CMD ["node", "apps/web/server.js"]
