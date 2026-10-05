#!/usr/bin/env bash
# Download CHARGED dataset (standard version, hourly) for 6 cities.
# Source: https://github.com/IntelligentSystemsLab/CHARGED
set -u

BASE="https://raw.githubusercontent.com/IntelligentSystemsLab/CHARGED/main/data"
DEST="E:/agent-project/DSC6004-project/data"
LOG="E:/agent-project/DSC6004-project/data/_download.log"

# City -> space-separated list of files (AMS keeps duration/distance inside the .rar)
declare -A FILES
FILES[AMS]="chargers.csv e_price.csv info.csv poi.csv s_price.csv sites.csv volume.csv weather.csv csv-larger-than-100MB.rar"
FILES[JHB]="chargers.csv distance.csv duration.csv e_price.csv info.csv poi.csv s_price.csv sites.csv volume.csv weather.csv"
FILES[LOA]="chargers.csv distance.csv duration.csv e_price.csv info.csv poi.csv s_price.csv sites.csv volume.csv weather.csv"
FILES[MEL]="chargers.csv distance.csv duration.csv e_price.csv info.csv poi.csv s_price.csv sites.csv volume.csv weather.csv"
FILES[SPO]="chargers.csv distance.csv duration.csv e_price.csv info.csv poi.csv s_price.csv sites.csv volume.csv weather.csv"
FILES[SZH]="chargers.csv distance.csv duration.csv e_price.csv info.csv poi.csv s_price.csv sites.csv volume.csv weather.csv"

: > "$LOG"
FAILED=0

for CITY in AMS JHB LOA MEL SPO SZH; do
  for F in ${FILES[$CITY]}; do
    URL="$BASE/$CITY/$F"
    OUT="$DEST/$CITY/$F"
    if [ -s "$OUT" ]; then
      echo "SKIP (exists)  $CITY/$F" >> "$LOG"
      continue
    fi
    CODE=$(curl -sL -f --retry 3 --retry-delay 2 -o "$OUT" -w "%{http_code}" "$URL" 2>/dev/null)
    SIZE=$(stat -c %s "$OUT" 2>/dev/null || echo 0)
    if [ "$CODE" = "200" ] && [ "$SIZE" -gt 0 ]; then
      echo "OK    $CITY/$F  ($SIZE bytes)" >> "$LOG"
    else
      echo "FAIL  $CITY/$F  (code=$CODE size=$SIZE)" >> "$LOG"
      rm -f "$OUT"
      FAILED=1
    fi
  done
done

echo "=== DONE failed=$FAILED ===" >> "$LOG"
