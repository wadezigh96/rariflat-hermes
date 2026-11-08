# Submission checklist

- [ ] `python -m pytest -q tests` passes
- [ ] `hermes plugins validate .` and `hermes plugins doctor` (run after install)
- [ ] Confirm `plugin.yaml` declares the tools and hooks you register
- [ ] Push, then `git rev-parse HEAD` and paste the 40-char SHA into `plugin-catalog/rariflat.yaml` (currently a placeholder — the PR will fail without it)
- [ ] Verify the Desktop pane receives `plugin.rariflat.tool` events (requires Hermes Desktop + the Python side enabled)

## Suggested demo flow (< 90s)
See docs/DEMO.md.

## Scoring notes
Rariflat scores on live visual feedback, measured reliability, task-aware routing, and an opt-in guard that cannot lock the agent out.
