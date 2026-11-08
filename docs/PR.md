## Rariflat — status characters, reliability scoring, task-aware routing, opt-in loop guard

Adds `plugin-catalog/rariflat.yaml`.

### What it does
- `pre_tool_call` / `post_tool_call` hooks show a character reaction per tool call and learn per-tool reliability (Wilson lower bound).
- `rariflat_route(task)` ranks previously-used tools by keyword match × reliability and explains why.
- Opt-in guard (`/rariflat guard on` or `RARIFLAT_GUARD=1`): blocks identical-call loops and repeated-failure tools for a cooldown only; never blocks its own tools. Returns the upstream shape `{"action": "block", "message": "..."}`.
- Optional Desktop pane (events via `broadcast_plugin_event`) + status chip.

### Disclosure
- Local persistence only: `~/.hermes/plugin-data/rariflat/scores.json` (atomic writes, corrupt files renamed).
- No network calls, no credentials, no shell commands.
- Learns short keywords from tool arguments (skips credential-like keys); disable with `RARIFLAT_LEARN_ARGS=0`.
- Guard is OFF by default.

### Tests
`python -m pytest -q tests`

Repo: https://github.com/wadezigh96/rariflat-hermes
