#!/usr/bin/env bash
# Capture la fenetre Cortex en PNG. Usage : gui_shot.sh <sortie.png> [titre]
#
# LINUX / X11 UNIQUEMENT : outil de developpement, pas de la chaine de
# production. Depend de xdotool et xwd, absents sous macOS et Windows.
# Equivalents natifs : macOS `screencapture -l<id>`, Windows Win+Maj+S.
set -euo pipefail
OUT="${1:?usage: gui_shot.sh <sortie.png> [titre]}"
TITLE="${2:-3D STL Viewer}"

command -v xdotool >/dev/null || { echo "xdotool absent (Linux/X11 requis)"; exit 1; }
command -v xwd >/dev/null || { echo "xwd absent (paquet x11-apps)"; exit 1; }

RACINE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PY_BIN="$RACINE/cortex/.venv/bin/python3"
[ -x "$PY_BIN" ] || PY_BIN=$(command -v python3)

WID=$(xdotool search --name "$TITLE" 2>/dev/null | head -1)
[ -n "$WID" ] || { echo "fenetre '$TITLE' introuvable"; exit 1; }

read -r W H < <(xdotool getwindowgeometry --shell "$WID" \
  | awk -F= '/^WIDTH/{w=$2} /^HEIGHT/{h=$2} END{print w, h}')

BRUT=$(mktemp -t gui_shot.XXXXXX.xwd)
trap 'rm -f "$BRUT"' EXIT
xwd -id "$WID" -out "$BRUT"
"$PY_BIN" - "$OUT" "$W" "$H" "$BRUT" <<'PY'
import sys
from PIL import Image
out, W, H, brut = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
d = open(brut, 'rb').read()
off = len(d) - W*H*4
Image.frombytes('RGBA', (W, H), d[off:], 'raw', 'BGRA').convert('RGB').save(out)
print(f"  {out}  {W}x{H}")
PY
