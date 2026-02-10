#!/usr/bin/env bash
set -euo pipefail

# AI-SERVIS Raspberry Pi bootstrap script
# Turns a clean Raspberry Pi OS into the AI-SERVIS car computer

REPO_URL_DEFAULT="https://github.com/sparesparrow/mia.git"
REPO_URL="${MIA_REPO_URL:-$REPO_URL_DEFAULT}"
SECURE_COMPOSE="${SECURE:-0}"

# Determine target user (prefer the invoking non-root user)
TARGET_USER="${SUDO_USER:-$(id -un)}"
USER_HOME="$(eval echo "~${TARGET_USER}")"

PI_GATEWAY_DIR="${USER_HOME}/ai-servis/edge-compat/pi-gateway"

log() { echo "[bootstrap] $*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { log "Missing required command: $1"; exit 1; }
}

ensure_pkg() {
  sudo apt-get install -y --no-install-recommends "$@"
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker already installed"
    return
  fi
  log "Installing Docker via convenience script"
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$TARGET_USER" || true
  log "Docker installed. You may need to log out/in to refresh group membership."
}

clone_repo() {
  if [ -d "${USER_HOME}/ai-servis/.git" ]; then
    log "Repo exists; pulling latest"
    git -C "${USER_HOME}/ai-servis" pull --ff-only || true
  else
    log "Cloning repo: ${REPO_URL}"
    sudo -u "$TARGET_USER" git clone "$REPO_URL" "${USER_HOME}/ai-servis"
  fi
}

prepare_env() {
  cd "$PI_GATEWAY_DIR"
  if [ ! -f .env ]; then
    log "Creating .env from env.example"
    sudo -u "$TARGET_USER" cp env.example .env
  fi

  # Optionally override .env values from environment
  override_var() {
    local key="$1"; shift
    local val="$1"; shift
    [ -z "${val}" ] && return 0
    local esc
    esc=$(printf '%s' "$val" | sed 's/[\/&]/\\&/g')
    if grep -q "^${key}=" .env; then
      sudo -u "$TARGET_USER" sed -i "s|^${key}=.*|${key}=${esc}|" .env
    else
      echo "${key}=${val}" | sudo -u "$TARGET_USER" tee -a .env >/dev/null
    fi
  }

  override_var VIN "${VIN:-}"
  override_var ANPR_RTSP_URL "${ANPR_RTSP_URL:-}"
  override_var REMOTE_URL "${REMOTE_URL:-}"
  override_var FORWARD_TOPICS "${FORWARD_TOPICS:-}"
}

start_stack() {
  cd "$PI_GATEWAY_DIR"
  log "Starting AI-SERVIS stack (secure=${SECURE_COMPOSE})"
  if [ "$SECURE_COMPOSE" = "1" ]; then
    sudo -u "$TARGET_USER" docker compose -f docker-compose.yml -f docker-compose.secure.yml up -d
  else
    sudo -u "$TARGET_USER" docker compose up -d
  fi
}

create_systemd_service() {
  local svc="/etc/systemd/system/ai-servis.service"
  log "Creating systemd service: ${svc}"

  local compose_cmd
  if [ "$SECURE_COMPOSE" = "1" ]; then
    compose_cmd="/usr/bin/docker compose -f docker-compose.yml -f docker-compose.secure.yml up -d"
  else
    compose_cmd="/usr/bin/docker compose up -d"
  fi

  sudo tee "$svc" >/dev/null <<EOF
[Unit]
Description=AI-SERVIS Car Computer System
Wants=network-online.target docker.service
After=network-online.target docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=${TARGET_USER}
Group=docker
WorkingDirectory=${PI_GATEWAY_DIR}
ExecStart=${compose_cmd}
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable ai-servis.service
  sudo systemctl start ai-servis.service || true
}

smoke_test() {
  cd "$PI_GATEWAY_DIR"
  if [ -x scripts/smoke.sh ]; then
    log "Running smoke test"
    bash scripts/smoke.sh || true
  else
    log "Smoke test script not found; skipping"
  fi
}

main() {
  log "Updating system packages"
  sudo apt-get update -y
  sudo apt-get upgrade -y

  log "Installing base packages (git, curl, avahi-daemon)"
  ensure_pkg git curl avahi-daemon ca-certificates

  install_docker

  # Ensure docker compose plugin is available
  if ! docker compose version >/dev/null 2>&1; then
    log "Docker Compose plugin not found; please ensure Docker >= 20.10 with compose plugin is installed"
    exit 1
  fi

  clone_repo

  prepare_env

  start_stack

  create_systemd_service

  smoke_test

  log "Bootstrap complete. If you just added the user to docker group, log out/in to apply."
}

main "$@"




