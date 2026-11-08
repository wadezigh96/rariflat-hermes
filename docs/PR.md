# Upstream catalog PR description — add `plugin-catalog/rariflat.yaml`

Adds **Rariflat** to the Hermes plugin catalog. The upstream catalog PR should add exactly one file: `plugin-catalog/rariflat.yaml`, with `sha:` set to the full 40-character SHA of the final, tested plugin commit.

## What it is
A Python plugin with an optional Desktop half. It observes `pre_tool_call` / `post_tool_call`, keeps per-tool reliability statistics, shows a character reaction per tool call in the Desktop pane, and exposes three tools:
`rariflat_route` (task-aware suggestion among observed tools), `rariflat_status`, `rariflat_guard`, plus a `/rariflat` command.

## Disclosure
- **Storage:** one local JSON file (`$HERMES_HOME/plugin-data/rariflat/scores.json`: tool name → counts) and an optional `config.json`. Tool arguments/results are not stored or logged.
- **Network:** none. **Credentials:** none. **Subprocesses / shell:** none.
- **Blocking:** the plugin can veto tool calls through `pre_tool_call` (`{"action": "block", "message": ...}`), but only when the user has set `guard.enabled: true` and configured a deny/allow list. Default is observe-only. It never blocks its own `rariflat_*` tools, and tool-result text cannot change blocking decisions.
- **Approvals:** the plugin does not approve, auto-approve or bypass anything; it can only make Hermes more restrictive, at the user's explicit request.
- **Desktop:** `desktop/plugin.js` imports only `@hermes/plugin-sdk`, `react`, and `react/jsx-runtime`; it listens for `plugin.rariflat.tool`, emitted by the Python half through `hermes_cli.plugin_events.broadcast_plugin_event`. The Desktop pane is opt-in (`defaultEnabled: false`).

## Validation
- `python -m pytest tests -v -rs` — **50 passed, 0 skipped** (Android/Termux, Python 3.13.13).
- `hermes plugins validate .` — passed (manifest, declared tools/hooks match registrations, security scan, Desktop surface).
- `git diff --check` — passed.
- `bash -n install.sh` — passed.
- `hermes plugins doctor .` has not been run in the current verification session.

## Known limits
- `rariflat_route` ranks tool names it has observed; it does not know Hermes skills it has never seen used.
- Success detection is heuristic and only feeds statistics.
- The Desktop pane receives events only when hooks run inside `hermes serve`.
