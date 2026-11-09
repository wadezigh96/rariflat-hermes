#!/usr/bin/env bash
# Install Rariflat and its optional Desktop pane from this checkout.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
DEST="$HERMES_HOME/plugins/rariflat"
DESKTOP_DEST="$HERMES_HOME/desktop-plugins/rariflat"

mkdir -p "$DEST/desktop" "$DESKTOP_DEST"
cp "$SRC/plugin.yaml" "$SRC/__init__.py" "$SRC/agent_ranking.py" "$SRC/README.md" "$SRC/LICENSE" "$DEST/"
cp "$SRC/desktop/plugin.js" "$SRC/desktop/event-contract.mjs" "$DEST/desktop/"
cp "$SRC/desktop/plugin.js" "$SRC/desktop/event-contract.mjs" "$DESKTOP_DEST/"

echo "Installed plugin to $DEST"
echo "Installed optional Desktop pane to $DESKTOP_DEST"
echo "Now run: hermes plugins enable rariflat"
