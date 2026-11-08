#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

HERMES_HOME="$TMP/hermes" "$ROOT/install.sh"

PLUGIN="$TMP/hermes/plugins/rariflat"
DESKTOP="$TMP/hermes/desktop-plugins/rariflat"
for file in plugin.yaml __init__.py desktop/plugin.js desktop/event-contract.mjs; do
  test -f "$PLUGIN/$file"
done
for file in plugin.js event-contract.mjs; do
  test -f "$DESKTOP/$file"
done

cmp "$PLUGIN/desktop/event-contract.mjs" "$DESKTOP/event-contract.mjs"
echo "Installer smoke test passed."
