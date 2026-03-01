#!/usr/bin/env bash
set -euo pipefail

BASE="https://02Zona.github.io/arxiv-audio"
DATE="$(date +%F)"
FEED="${BASE}/feed.xml"
AUDIO="${BASE}/episodes/${DATE}.m4a"

echo "[1/4] Check feed reachable: $FEED"
curl -fsSI "$FEED" | head -n 5

echo "[2/4] Check today's audio reachable: $AUDIO"
curl -fsSI "$AUDIO" | head -n 10

echo "[3/4] Check feed contains today's enclosure URL"
curl -fsS "$FEED" | rg -q "$AUDIO" && echo "OK: enclosure found" || (echo "FAIL: enclosure not found" && exit 2)

echo "[4/4] Local quick play (optional)"
if [[ -f "episodes/${DATE}.m4a" ]]; then
  echo "Local file exists: episodes/${DATE}.m4a"
else
  echo "Local file missing: episodes/${DATE}.m4a (skip)"
fi

echo "ALL CHECKS PASSED"
