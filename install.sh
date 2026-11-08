#!/usr/bin/env bash
# Installs only what the plugin needs (no .git, docs or tests) into $HERMES_HOME/plugins/rariflat.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${HERMES_HOME:-$HOME/.hermes}/plugins/rariflat"
mkdir -p "$DEST/desktop"
cp "$SRC/__init__.py" "$SRC/plugin.yaml" "$SRC/LICENSE" "$DEST/"
cp "$SRC/desktop/plugin.js" "$DEST/desktop/"
echo "Installed to $DEST"
echo "Next:  hermes plugins enable rariflat"
echo "Desktop pane (optional): toggle 'rariflat' on in the app's Settings -> Plugins."
