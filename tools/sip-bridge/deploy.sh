#!/usr/bin/env bash
# deploy.sh — push SIP bridge to studio node via Tailscale (100.109.34.98)
set -euo pipefail

STUDIO="sparrow@100.109.34.98"
REMOTE_DIR="/opt/mia/sip-bridge"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "▶ Deploying MIA SIP bridge to $STUDIO:$REMOTE_DIR"

# 1. Create remote dir
ssh "$STUDIO" "sudo mkdir -p $REMOTE_DIR && sudo chown sparrow:sparrow $REMOTE_DIR"

# 2. Copy files
rsync -av --delete \
    "$SCRIPT_DIR/" \
    "$STUDIO:$REMOTE_DIR/" \
    --exclude __pycache__ \
    --exclude "*.pyc"

# 3. Copy .env if it exists locally
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    scp "$SCRIPT_DIR/.env" "$STUDIO:$REMOTE_DIR/.env"
    echo "  ✓ .env deployed"
fi

# 4. Pull Docker image and start
ssh "$STUDIO" "
    cd $REMOTE_DIR
    docker compose pull
    docker compose up -d
    echo '  ✓ Asterisk container started'
    docker compose ps
"

# 5. Show SIP status
echo ""
echo "▶ Checking Asterisk SIP status..."
ssh "$STUDIO" "docker exec mia-asterisk asterisk -rx 'pjsip show endpoints' 2>/dev/null || echo '  (asterisk still starting)'"

echo ""
echo "Done. Next steps:"
echo "  1. Set ELEVENLABS_SIP_DOMAIN in $REMOTE_DIR/.env  (get from ElevenLabs dashboard)"
echo "  2. Run: python elevenlabs_sip_configure.py lock   (restrict SIP to studio IP)"
echo "  3. Run: python elevenlabs_sip_configure.py status (verify)"
