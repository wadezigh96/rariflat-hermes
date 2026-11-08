# Rariflat 2.0.0

Rariflat adds live status characters, local reliability learning, task-aware tool recommendations, and an **opt-in** failure-streak / repeated-call guard to Hermes Agent.

## Features
- Character reactions for common tool families, with token-boundary matching.
- Local-only reliability history in `~/.hermes/plugin-data/rariflat/scores.json` (override with `RARIFLAT_DATA_DIR`).
- Task-aware tool/skill recommendations using a weighted ranking: task fit 40%, reliability 25%, rarity 20%, restraint 15%. Rarity is derived from observed tool-call frequency (fewer uses score higher); restraint is derived from repeated identical calls within a 30-second window (fewer repeats score higher). Each recommendation includes the measured values, factor scores, and a human-readable reason.
- Router scope: advisory **tool/skill recommender** only. It returns ranked Hermes tool/skill names; it does **not** dispatch tasks to agents or invoke the selected tool.
- Guard is **off by default**. Enable with `/rariflat guard on`; disable with `/rariflat guard off`.
- Optional Hermes Desktop pane using the official `broadcast_plugin_event` bridge.
- No network requests, telemetry, or shell execution. Tool arguments are inspected in memory to learn non-secret task tokens and repeated-call fingerprints; credential-like fields and recognized inline secrets are filtered before token learning. No raw arguments or credentials are intentionally persisted.

## Install
Install with the Hermes plugin manager/catalog when available, or copy this repository into `~/.hermes/plugins/rariflat/`. The desktop pane is `desktop/plugin.js`.

## Configuration
- `RARIFLAT_GUARD=1`: enable guard at startup (default off).
- `RARIFLAT_FAIL_STREAK=3`: consecutive failures before blocking.
- `RARIFLAT_COOLDOWN=30`: seconds before a failure-streak lockout automatically recovers.
- `RARIFLAT_LOOP_REPEAT=0`: identical calls needed to trigger loop protection; 0 disables it.
- `RARIFLAT_LOOP_WINDOW=30`: loop detection window in seconds.
- `RARIFLAT_DATA_DIR=/path`: override local score directory.
- `RARIFLAT_VERBOSE=1`: enable character logs.

## Safety
The guard is opt-in and fail-open when disabled. It never blocks Rariflat's own tools. Successful calls reset failure streaks. Loop detection is separately disabled unless configured. Scores remain local and can be cleared with `/rariflat reset`.

## Validation
Run `python -m pytest -q tests`. Also run `hermes plugins validate .` and `hermes doctor` in an installed Hermes environment. The GitHub CI workflow runs the Python and Desktop event-contract tests; it does not replace validation against an installed Hermes CLI/Desktop runtime.
