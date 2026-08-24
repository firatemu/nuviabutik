#!/bin/bash
# NuviaButik production deploy — /srv/apps/nuviabutik
set -euo pipefail

APP_DIR="/srv/apps/nuviabutik"
VENV="${APP_DIR}/venv"
LOG="/var/log/nuviabutik-deploy.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "Deploy started"
cd "$APP_DIR"

# root SSH deploy on www-data-owned repo
git config --global --add safe.directory "$APP_DIR" 2>/dev/null || true

log "Git pull"
git fetch origin main
git merge --ff-only origin/main

log "Python dependencies"
"${VENV}/bin/pip" install -r requirements.txt python-barcode==0.16.1 hiredis==3.3.0 -q

log "collectstatic"
sudo -u www-data bash -c "set -a && source ${APP_DIR}/.env && set +a && ${VENV}/bin/python ${APP_DIR}/manage.py collectstatic --noinput"

log "Django check"
sudo -u www-data bash -c "set -a && source ${APP_DIR}/.env && set +a && ${VENV}/bin/python ${APP_DIR}/manage.py check"

log "Restart nuviabutik"
systemctl restart nuviabutik
sleep 2

if systemctl is-active --quiet nuviabutik; then
  log "Deploy OK — nuviabutik active"
else
  log "Deploy FAILED — service not active"
  exit 1
fi
