# Rariflat — Hermes Agent Plugin

Makes tool calls **visible, measurable and safer**. Every call gets a character reaction, every tool gets a reliability score learned from real use, and an **opt-in guard** stops runaway loops and repeatedly failing tools — then lets them back in automatically.

## What it does
| Feature | How it works |
|---|---|
| **Living characters** | Owl, Hephaestus, Archivist, … react to each tool call (pre + post hook). Matching is by tool-name token, so `profile_lookup` is not mistaken for a file tool. |
| **Honest scores** | *Reliability* = Wilson lower bound of success rate (a 1/1 tool doesn't outrank a 95/100 tool). *Rarity* = how under-used a tool is vs. the rest. *Restraint* = 100 minus penalties for repeat-loops and failure streaks. |
| **Task-aware routing** | `rariflat_route(task)` ranks tools you've already used by keyword match with the task (tool name + vocabulary learned from past arguments) × reliability. Explains *why* in its result. |
| **Loop & circuit-breaker guard** | Opt-in (off by default). Blocks identical calls repeated N× in a window, and tools that failed N× in a row — for a cooldown only. Never blocks `rariflat_*` tools. Uses the upstream block shape `{"action": "block", "message": "..."}`. |
| **Failure detection that works** | Structured signals first (`error`, `success:false`, `exit_code`/`returncode` ≠ 0); plain text only if it *starts* with Error/Traceback/command not found/etc. Empty output is success. |
| **Desktop pane** | Shows the current character, guard warnings/blocks, and recent history. Events are emitted via the official `broadcast_plugin_event` so the pane receives `plugin.rariflat.tool`. |

## Install
```bash
# Clone only the plugin files (no .git, no docs)
git clone --depth 1 https://github.com/wadezigh96/rariflat-hermes /tmp/rariflat-src
mkdir -p ~/.hermes/plugins/rariflat
rsync -a --exclude '.git' --exclude 'docs' --exclude 'plugin-catalog' --exclude 'tests' --exclude '.github' /tmp/rariflat-src/ ~/.hermes/plugins/rariflat/
hermes plugins enable rariflat

# optional Desktop pane (upstream expects this path)
mkdir -p "$HERMES_HOME/desktop-plugins/rariflat"
cp ~/.hermes/plugins/rariflat/desktop/plugin.js "$HERMES_HOME/desktop-plugins/rariflat/"
```

Or use the included `install.sh`.

## Use
- Just use Hermes — characters react (opt-in verbose via `RARIFLAT_VERBOSE=1`) and scores build up.
- `/rariflat` rankings · `/rariflat guard on|off` · `/rariflat explain <tool>` · `/rariflat reset`
- Ask Hermes to call `rariflat_route`, `rariflat_status` or `rariflat_guard`.

## Configuration (environment variables)
| Variable | Default | Meaning |
|---|---|---|
| `RARIFLAT_GUARD` | `0` | `1` = enforce blocks (can also be toggled with `/rariflat guard`) |
| `RARIFLAT_FAIL_STREAK` | `3` | consecutive failures that open the breaker |
| `RARIFLAT_COOLDOWN` | `60` | seconds a tripped tool stays blocked |
| `RARIFLAT_LOOP_REPEAT` / `RARIFLAT_LOOP_WINDOW` | `4` / `120` | identical calls within seconds that count as a loop |
| `RARIFLAT_LEARN_ARGS` | `1` | `0` = don't learn keywords from tool arguments |
| `RARIFLAT_VERBOSE` | `0` | `1` = also print character lines to stderr |
| `RARIFLAT_DATA_DIR` | `~/.hermes/plugin-data/rariflat` | where `scores.json` lives |

## Privacy & disclosure
- Local only: one JSON file, **no network calls, no credentials, no shell commands**.
- Keyword learning stores only short lowercase words (max 60 per tool), skips arguments named like `password/token/key/secret/auth`, and can be switched off.
- Optional blocking exists and is **off by default**.

## Development
```bash
pip install pytest && python -m pytest -q tests
```
See `tests/README.md`.
