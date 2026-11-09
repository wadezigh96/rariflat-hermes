#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

HERMES_HOME="$TMP/hermes" "$ROOT/install.sh"

PLUGIN="$TMP/hermes/plugins/rariflat"
DESKTOP="$TMP/hermes/desktop-plugins/rariflat"
for file in plugin.yaml __init__.py agent_ranking.py desktop/plugin.js desktop/event-contract.mjs; do
  test -f "$PLUGIN/$file"
done
for file in plugin.js event-contract.mjs; do
  test -f "$DESKTOP/$file"
done

cmp "$PLUGIN/desktop/event-contract.mjs" "$DESKTOP/event-contract.mjs"
PYTHONPATH="$PLUGIN" python3 - "$TMP/registry" <<'PY'
import sys
from agent_ranking import AgentRegistry

registry = AgentRegistry(sys.argv[1])
registry.register(
    "installed-agent", "Installed agent", "hermes", ["research"],
    "https://github.com/example/research-agent",
    install_ref="example/research-agent",
)
assert registry.rank("research")[0]["id"] == "installed-agent"
PY
echo "Installer smoke test passed."
