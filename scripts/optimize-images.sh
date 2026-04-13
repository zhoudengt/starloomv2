#!/usr/bin/env bash
# Convert all PNG images under frontend/public/ to WebP (quality 80).
# Existing .webp files are skipped. Original PNGs are kept for fallback.
# Requires: cwebp (brew install webp)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PUBLIC_DIR="$PROJECT_ROOT/frontend/public"

if ! command -v cwebp &>/dev/null; then
  echo "ERROR: cwebp not found. Install with: brew install webp" >&2
  exit 1
fi

converted=0
skipped=0

find "$PUBLIC_DIR" -type f -name '*.png' | sort | while IFS= read -r png; do
  webp="${png%.png}.webp"
  if [[ -f "$webp" ]]; then
    skipped=$((skipped + 1))
    continue
  fi
  echo "Converting: ${png#$PROJECT_ROOT/}"
  cwebp -q 80 -m 6 "$png" -o "$webp" 2>/dev/null
  converted=$((converted + 1))
done

echo ""
echo "Done. Converted new files. Existing .webp files were skipped."
echo "Tip: compare sizes with  du -sh $PUBLIC_DIR/*/"
