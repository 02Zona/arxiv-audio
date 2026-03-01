#!/usr/bin/env bash
set -euo pipefail

BASE="https://02Zona.github.io/arxiv-audio"
DATE="${1:-$(date +%F)}"
FEED="${BASE}/feed.xml"
PATTERN="${BASE}/episodes/${DATE}-[0-9][0-9].m4a"

echo "[1/4] Check feed reachable: $FEED"
curl -fsSI "$FEED" | head -n 5

echo "[2/4] Check today's audio reachable for date: $DATE"
URLS=$(curl -fsS "$FEED" | grep -o "$PATTERN" | sort -u || true)
if [[ -z "$URLS" ]]; then
  echo "FAIL: no enclosures found for date $DATE"
  exit 2
fi
for url in $URLS; do
  curl -fsSI "$url" | head -n 5
done

echo "[3/4] Check feed contains today's enclosure URL(s)"
curl -fsS "$FEED" | grep -q "$PATTERN" && echo "OK: enclosure found" || (echo "FAIL: enclosure not found" && exit 2)

echo "[4/4] Local quick play (optional)"
if ls "episodes/${DATE}-"*.m4a >/dev/null 2>&1; then
  echo "Local files exist: episodes/${DATE}-*.m4a"
else
  echo "Local files missing: episodes/${DATE}-*.m4a (skip)"
fi

echo "ALL CHECKS PASSED"
