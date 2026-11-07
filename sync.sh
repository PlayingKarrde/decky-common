#!/usr/bin/env bash
# Copy decky-common into a plugin checkout.
#   sync.sh <plugin-dir> <python-package>      e.g. sync.sh ../romm-decky romm
#
# Writes:
#   <plugin>/py_modules/<package>/common/   from deckycommon/
#   <plugin>/src/common/                    from ts/
#   <plugin>/scripts/cdp.py                 from scripts/cdp.py
#   <plugin>/.decky-common                  the decky-common commit the copies came from
#
# The copies are committed in the plugin, so its build and release never need this repo.
# Plugin CI re-runs this at the recorded commit and fails if the copies were edited.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
[[ $# -eq 2 ]] || { sed -n '2,3p' "$0"; exit 2; }
DEST="$(cd "$1" && pwd)"
PKG="$2"
[[ -d "$DEST/py_modules/$PKG" ]] || { echo "no py_modules/$PKG in $DEST" >&2; exit 1; }

copy_dir() {  # src dst: mirror, minus caches
  rm -rf "$2"
  mkdir -p "$2"
  (cd "$1" && find . -type f ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 | sort -z |
    while IFS= read -r -d '' f; do mkdir -p "$2/$(dirname "$f")"; cp "$f" "$2/$f"; done)
}

copy_dir "$SRC/deckycommon" "$DEST/py_modules/$PKG/common"
copy_dir "$SRC/ts" "$DEST/src/common"
cp "$SRC/scripts/cdp.py" "$DEST/scripts/cdp.py"
chmod +x "$DEST/scripts/cdp.py"

rev="$(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo unknown)"
if [[ -n "$(git -C "$SRC" status --porcelain -- deckycommon ts scripts 2>/dev/null)" ]]; then
  rev="$rev-dirty"
  echo "warning: decky-common has uncommitted changes; commit them before committing the plugin" >&2
fi
echo "$rev" > "$DEST/.decky-common"
echo "synced decky-common $rev -> $DEST"
