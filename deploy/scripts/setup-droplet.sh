#!/usr/bin/env bash
set -euo pipefail

SERVER="root@162.243.231.61"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== APIgame droplet setup ==="
echo "Target: $SERVER"
echo ""

# --- Step 1: scp requirements files to /tmp on the droplet ---
echo "[1/5] Copying requirements files to droplet..."
scp "$REPO_ROOT/server/agent/requirements.txt" "$SERVER:/tmp/apigame-agent-requirements.txt"
scp "$REPO_ROOT/server/web/requirements.txt"   "$SERVER:/tmp/apigame-web-requirements.txt"
echo "      Done."

# --- Steps 2–5: run setup on the droplet via a single SSH session ---
echo "[2/5] Creating directory tree..."
echo "[3/5] Creating Python venv..."
echo "[4/5] Installing pip packages..."
echo "[5/5] Writing .env template..."

ssh "$SERVER" bash -s <<'REMOTE'
set -euo pipefail

# --- Directories (idempotent: mkdir -p) ---
echo "  -> mkdir -p /opt/apigame/{agent,web,config,data,logs}"
mkdir -p /opt/apigame/{agent,web,config,data,logs}

# --- Python venv (skip if already exists) ---
if [ ! -f /opt/apigame/venv/bin/python ]; then
    echo "  -> Creating Python venv..."
    python3 -m venv /opt/apigame/venv
else
    echo "  -> Venv already exists, skipping creation."
fi

# --- Upgrade pip, then install packages ---
echo "  -> Upgrading pip..."
/opt/apigame/venv/bin/pip install --quiet --upgrade pip

echo "  -> Installing agent requirements..."
/opt/apigame/venv/bin/pip install --quiet -r /tmp/apigame-agent-requirements.txt

echo "  -> Installing web requirements..."
/opt/apigame/venv/bin/pip install --quiet -r /tmp/apigame-web-requirements.txt

# Clean up temp files
rm -f /tmp/apigame-agent-requirements.txt /tmp/apigame-web-requirements.txt

# --- .env template (only write if file doesn't already exist) ---
if [ ! -f /opt/apigame/config/.env ]; then
    echo "  -> Writing .env template..."
    cat > /opt/apigame/config/.env <<'ENV'
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_USER=esp32
MQTT_PASS=
CALENDAR_ID=primary
TZ=America/New_York
ENV
    chmod 600 /opt/apigame/config/.env
else
    echo "  -> .env already exists, skipping (won't overwrite credentials)."
fi

echo ""
echo "  Verify:"
echo "    ls /opt/apigame/"
ls /opt/apigame/
echo ""
echo "    pip packages:"
/opt/apigame/venv/bin/pip list --format=columns | grep -iE 'google|paho|fastapi|uvicorn|websockets|aiofiles|dotenv'
REMOTE

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Fill in credentials:  ssh $SERVER \"nano /opt/apigame/config/.env\""
echo "  2. Verify tinydrop untouched:  ssh $SERVER \"ls /opt/tinydrop/\""
