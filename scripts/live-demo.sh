#!/usr/bin/env bash
set -euo pipefail

REPO="wadezigh96/rariflat-hermes"
DEFAULT_REF="c3434bb632707f1bef6b5a95883913bd2aac9595"
REF="${RARIFLAT_REF:-$DEFAULT_REF}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PLUGIN_DIR="$HERMES_HOME/plugins/rariflat"

if ! command -v hermes >/dev/null 2>&1; then
  echo "ERROR: Hermes CLI is not on PATH. Install Hermes first: https://hermes-agent.nousresearch.com/"
  exit 1
fi

if [[ ! "$REF" =~ ^[0-9a-f]{40}$ ]]; then
  echo "ERROR: RARIFLAT_REF must be a full 40-character commit SHA."
  exit 1
fi

echo "== Rariflat live demo preflight =="
hermes --version
echo "Hermes home: $HERMES_HOME"
echo "Source: $REPO@$REF"

if [[ -d "$PLUGIN_DIR" ]]; then
  BACKUP="$HERMES_HOME/backups/rariflat-before-demo-$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$(dirname "$BACKUP")"
  cp -a "$PLUGIN_DIR" "$BACKUP"
  echo "Existing plugin backed up to: $BACKUP"
  hermes plugins install "$REPO" --force --ref "$REF" --enable
else
  hermes plugins install "$REPO" --ref "$REF" --enable
fi

hermes plugins list
hermes plugins doctor "$PLUGIN_DIR"

echo
echo "== Starting the real Hermes agent demo =="
echo "This step requires a configured Hermes model/provider and any tool permissions it requests."
echo "The agent will be asked to use real available tools, then call Rariflat's real tools."
echo

PROMPT='Run a real Rariflat demonstration in this Hermes session.
1. Call rariflat_status and report the current tracked tool count and guard state.
2. Use only tools that are actually available in this session. Make one harmless real search call and one harmless local terminal call if those tools are available. Do not invent tool names or fabricate tool results. If a tool is unavailable, say so.
3. Call rariflat_status again and report the observed tools and counts.
4. Call rariflat_route for two distinct tasks: (a) research official Python asyncio documentation; (b) inspect the local runtime environment. Show the returned rankings, all four factor scores, and explanations exactly as returned.
5. Clearly state whether the history is sufficient for meaningful recommendations. Do not claim the router dispatches tasks or executes recommendations; it is advisory only.
Do not modify files, install packages, access secrets, or perform network actions beyond the harmless search call.'

hermes chat -q "$PROMPT" --max-turns 12
