#!/usr/bin/env bash
# Install Rariflat into ~/.hermes/plugins/rariflat (copies only needed files).
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${HERMES_HOME:-$HOME/.hermes}/plugins/rariflat"
mkdir -p "$DEST"
rsync -a --exclude '.git' --exclude 'docs' --exclude 'plugin-catalog' --exclude 'tests' --exclude '.github' --exclude '*.md' --exclude 'install.sh' "$SRC/" "$DEST/"
# Always keep README and LICENSE
cp "$SRC/README.md" "$SRC/LICENSE" "$DEST/" 2>/dev/null || true
echo "Installed to $DEST"
echo "Now run: hermes plugins enable rariflat"
echo "Desktop pane (optional):"
echo "  mkdir -p \"\$HERMES_HOME/desktop-plugins/rariflat\" && cp \"$DEST/desktop/plugin.js\" \"\$HERMES_HOME/desktop-plugins/rariflat/\""
