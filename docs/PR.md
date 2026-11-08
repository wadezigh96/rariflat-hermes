## Rariflat — live tool status, local reliability learning, advisory routing, opt-in loop guard
The catalog YAML in this repository is a draft entry only. Hackathon admission requires a separate PR adding the entry to `NousResearch/hermes-agent`.

### What it does
- `pre_tool_call` / `post_tool_call` hooks show a character reaction per tool call and learn local observed success rates.
- `rariflat_route(task)` ranks previously-used tools by keyword match × reliability and explains why.
- Opt-in guard (`/rariflat guard on` or `RARIFLAT_GUARD=1`): blocks identical-call loops and repeated-failure tools for a cooldown only; never blocks its own tools. Returns the upstream shape `{"action": "block", "message": "..."}`.
- Optional Desktop activity pane (events via `broadcast_plugin_event`).

Rariflat recommends tools but does not dispatch tasks to agents. Recommendations are advisory and reflect only locally observed history.

### Disclosure
- Local persistence only: `~/.hermes/plugin-data/rariflat/scores.json` (atomic writes, corrupt files renamed).
- The plugin makes no network requests, reads no external credential stores, and starts no shell commands or background services.
- Tool arguments are processed in memory. Recognized credential-like fields and inline secret patterns are filtered before token learning and fingerprinting; `RARIFLAT_LEARN_ARGS=0` disables argument-token learning.
- Failure output details are withheld from Desktop events to avoid exposing sensitive tool results.
- Guard is OFF by default.

### Tests
Run `python -m pytest -q tests`, `node --test tests/desktop_event_contract.test.mjs`, and `hermes plugins validate . --install-deps`. See `docs/SUBMISSION.md` for the hackathon checklist.

Repo: https://github.com/wadezigh96/rariflat-hermes
