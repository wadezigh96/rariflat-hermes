# Rariflat — Hermes Agent plugin

Watches your agent's tool calls, shows who is "working" (Owl, Hephaestus, …), keeps a reliability score per tool,
suggests which observed tool fits a task, and — only if you ask for it — can block tools you list.

## What it does (and does not)

| Feature | Behaviour |
|---|---|
| Character reactions | Every tool call emits a short reaction. Shown in the Desktop pane; optional log lines (`RARIFLAT_CONSOLE=1`). |
| Reliability | Per tool: `uses`, `successes`, and a smoothed success rate `(successes+1)/(uses+2)`. Stored locally. |
| `rariflat_route` | Takes a `task`, matches its words against observed tool names and a small keyword map, ranks matches by reliability. Says so when nothing matches. It ranks **tool names** it has seen, not Hermes skills. |
| `rariflat_status`, `/rariflat` | Rankings plus current settings. |
| `rariflat_guard` | Reports exactly what the pre-hook would do for a tool right now. |
| Guard (opt-in) | **Off by default.** Blocks only tools on your deny list (or not on your allow list). Never blocks `rariflat_*` tools. |

Success is judged from structured signals first (`exit_code`/`returncode` ≠ 0, an `error` field, `success: false`,
hook `error_type`/`status`), otherwise from the first ~300 characters of plain text (e.g. `command not found`,
`No such file or directory`). Empty or whitespace-only output is not scored because it carries no reliable outcome signal.
This is a heuristic that feeds the statistics only.

## Install

```bash
git clone https://github.com/wadezigh96/rariflat-hermes && cd rariflat-hermes
./install.sh                      # copies only __init__.py, plugin.yaml, LICENSE, desktop/plugin.js
hermes plugins enable rariflat
```

Desktop pane (optional): the desktop half is opt-in — toggle **rariflat** on in the app's Settings → Plugins.
Events are delivered when the Python hooks run inside `hermes serve` (the Desktop backend). In `hermes chat`
there is no Desktop client, so no events are sent.

## Configuration

`$HERMES_HOME/plugin-data/rariflat/config.json` (default `~/.hermes/plugin-data/rariflat/config.json`), all keys optional:

```json
{
  "console": false,
  "desktop_events": true,
  "guard": { "enabled": false, "deny": ["terminal"], "allow": null }
}
```

- `guard.enabled` must be `true` for anything to be blocked. `deny` blocks listed tool names; `allow` (a list) blocks everything not listed. Names are matched exactly, case-insensitive.
- Environment overrides: `RARIFLAT_GUARD=1|0`, `RARIFLAT_DENY=a,b`, `RARIFLAT_ALLOW=a,b`, `RARIFLAT_CONSOLE=1|0`, `RARIFLAT_DESKTOP_EVENTS=1|0`.
- Blocking uses Hermes' documented `pre_tool_call` directive `{"action": "block", "message": ...}`; the model sees the message as the tool result.

## Data and privacy

- One local file: `$HERMES_HOME/plugin-data/rariflat/scores.json` (tool name → uses, successes), plus the optional `config.json`.
- No network calls, no credentials, no subprocesses. Tool arguments and results are never stored or logged — only success/failure counts and tool names.
- A corrupt `scores.json` is renamed to `scores.json.corrupt-<timestamp>`, never silently wiped. Writes are atomic and merged with what is already on disk, so two Hermes processes add up instead of overwriting each other.
- Old `scores.json` files from 1.0/1.1 (rarity/restraint) are read; only `uses`/`successes` are kept.

## Development

```bash
pip install pytest pyyaml
python -m pytest tests -v
hermes plugins validate .
hermes plugins doctor .
```

MIT licensed.
