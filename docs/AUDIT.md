# Rariflat 2.0.0 — audit remediation

Remediates the defects identified in commit 85bd690.

- Implements the fixture/test API: `_reset_for_tests`, `Store`, `judge_result`, and `_get_store`.
- Uses Hermes' documented pre-tool veto directive: `{"action": "block", "message": "..."}`.
- Emits desktop updates through the official `hermes_cli.plugin_events.broadcast_plugin_event("rariflat", "tool", payload)` API; the wire event is `plugin.rariflat.tool`.
- Guard enforcement defaults OFF; own tools are never blocked or scored.
- Adds task-token routing, structured result detection, failure streak recovery, opt-in repeated-call detection, and atomic local persistence with corrupt-file quarantine.
- Desktop hooks are inside a React component and subscribe with `host.onEvent`.

The GitHub Actions test run is the acceptance gate. Hermes CLI validation must also be run in a Hermes installation; it cannot be claimed from pytest alone.
