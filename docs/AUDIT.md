# Audit notes (v2.0.0)

## Fixed from original / previous patch
1. **Guard never blocked** — return shape was `{"blocked": True, "reason": ...}`. Upstream only honors `{"action": "block", "message": "<non-empty string>"}`. Fixed.
2. **Restraint lockout** — old heuristic dropped 2 per call from 50. Replaced with opt-in failure-streak + loop detector that auto-recovers. Own tools never scored or blocked.
3. **`rariflat_route` ignored task** — now does deterministic keyword/token matching against tool names and learned argument tokens, ranked by reliability.
4. **Success detection** — structured signals preferred; plain text only checked at the start for known failure phrases; empty = success.
5. **Persistence** — threading.Lock, atomic replace, throttle, atexit flush, corrupt files renamed to `scores.json.corrupt-<ts>`, logging (no bare except/pass).
6. **Desktop pane** — React imported correctly, hooks used in a proper component, events emitted via verified `hermes_cli.plugin_events.broadcast_plugin_event` (wire name `plugin.rariflat.tool`).
7. **Character matching** — token/prefix, not substring.
8. **Console** — logging module, opt-in via `RARIFLAT_VERBOSE`.
9. Manifests aligned, LICENSE added, install path documented, tests added.

## Unverified
- Could not run `hermes plugins validate` / `doctor` (Hermes CLI not present in the audit environment).
- Exact minimum `requires_hermes` ">=0.21" is reasonable given the block feature landed around that era, but not bit-for-bit verified against a specific tag.
- Desktop pane requires a running Hermes Desktop client to see events; the emission path is documented upstream and used.
