#!/usr/bin/env bash
set -euo pipefail

# Install Local Leet on the Ubuntu judge host.
# Judging uses this machine's system python3, gcc, and g++.

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This setup script is for the Ubuntu server, not the development PC."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
HOME_DIR="$(getent passwd "$USER_NAME" | cut -d: -f6)"
SERVICE_SRC="$ROOT/scripts/local-leet.service"
UNIT="/etc/systemd/system/local-leet.service"

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip g++ gcc nodejs npm

cd "$ROOT"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r backend/requirements.txt

if command -v npm >/dev/null; then
  (cd frontend && npm install && npm run build)
else
  echo "npm not found; install Node.js and run: cd frontend && npm install && npm run build"
  exit 1
fi

sed \
  -e "s|@ROOT@|$ROOT|g" \
  -e "s|@USER@|$USER_NAME|g" \
  "$SERVICE_SRC" | sudo tee "$UNIT" >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now local-leet.service

echo
echo "Local Leet is running on this Ubuntu host."
echo "On other computers, open: http://$(hostname -I | awk '{print $1}'):8080"
echo "If ufw is enabled: sudo ufw allow 8080/tcp"
echo "First registered user becomes admin."
echo "Later, to fetch new problems from GitHub: ./scripts/update-from-github.sh"
