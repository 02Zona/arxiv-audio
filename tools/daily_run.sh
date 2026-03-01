#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATE="${1:-$(date +%F)}"
VOICE="${VOICE:-Zoe}"
RATE="${RATE:-220}"
N="${N:-15}"
BASE_URL="${BASE_URL:-https://02Zona.github.io/arxiv-audio}"
TZ_OFFSET="$(date +%z)"
LOG_DIR="$REPO_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily-${DATE}.log"

exec > >(tee -a "$LOG_FILE") 2>&1

cd "$REPO_DIR"
echo "[$(date)] Start daily run for ${DATE}"
git pull --rebase --autostash origin main

python3 tools/make_episode.py --n "$N" --date "$DATE"

shopt -s nullglob
txt_files=(episodes/${DATE}-*.txt)

if (( ${#txt_files[@]} == 0 )); then
  echo "No new submissions for ${DATE}; skip publishing."
  exit 0
fi

rm -f episodes/${DATE}-*.m4a
for f in "${txt_files[@]}"; do
  stem="${f%.txt}"
  say -v "$VOICE" -r "$RATE" -o "${stem}.aiff" -f "$f"
  afconvert "${stem}.aiff" -o "${stem}.m4a" -f m4af -d alac
  rm -f "${stem}.aiff"
done

python3 tools/update_feed.py --date "$DATE" --base-url "$BASE_URL" --tz-offset "$TZ_OFFSET"
python3 tools/add_show_notes.py
rm -f episodes/${DATE}-*.txt

./tools/verify.sh "$DATE"

git add feed.xml episodes/${DATE}-*.m4a episodes/${DATE}.json
if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi

git commit -m "daily update ${DATE}"
git push origin main
echo "[$(date)] Daily run finished for ${DATE}"
