#!/bin/bash
# Uruchamiany przez cron co 2 minuty: */2 * * * * /home/smgraphic4u/ikzocr-health-check.sh >> /home/smgraphic4u/ikzocr-health.log 2>&1
# Lokalizacja na VM: ~/ikzocr-health-check.sh

API_URL="http://localhost:8000/health"
PANEL_URL="http://localhost:3000"
LOCK_DIR=/tmp

check() {
  local name=$1 url=$2
  local lock="$LOCK_DIR/ikzocr_down_$name"
  if ! curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
    if [ ! -f "$lock" ]; then
      touch "$lock"
      echo "$(date): DOWN $name ($url)" >> ~/ikzocr-health.log
      # TODO: alert email/webhook
      # curl -s -X POST https://n8n.../webhook/ikzocr-alert -d "{\"service\":\"$name\"}" || true
    fi
  else
    if [ -f "$lock" ]; then
      rm -f "$lock"
      echo "$(date): RECOVERED $name" >> ~/ikzocr-health.log
    fi
  fi
}

check "API" "$API_URL"
check "Panel" "$PANEL_URL"
