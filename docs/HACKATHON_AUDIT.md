# Rariflat repository audit — 9 November 2026

## Current source

The current default-branch source is commit [5d00db7](https://github.com/wadezigh96/rariflat-hermes/commit/5d00db7bcc949405d035bf37dfa7b5ba51aaaa82), which merges PR #14 and contains the Rariflat 2.0.0 tool-observability and evidence-based agent-ranking work.

The immutable source pin in the README, quickstart, and local catalog draft should match this commit. Older references to `c5d6fba` and `e7a8d9b` referred to earlier source revisions and are superseded.

## Repository contents

The maintained runtime consists of:

- `__init__.py` — plugin registration, six tool handlers, and four lifecycle hooks.
- `agent_ranking.py` — local Hermes/A2A agent registry and evidence-based ranking.
- `desktop/` — optional Hermes Desktop pane and event contract.
- `plugin.yaml` and `plugin-catalog/rariflat.yaml` — plugin and catalog metadata.
- `tests/` and `.github/workflows/test.yml` — Python, Node, installer, and Hermes validation checks.
- `README.md`, `docs/`, `install.sh`, and `LICENSE` — user and maintainer documentation, installer, and license.

Two superseded notes, `docs/PR.md` and `docs/AUDIT.md`, are removed in the cleanup branch. Their current user-facing and audit information is consolidated in the README, this file, and `docs/SUBMISSION.md`.

## Confirmed local checks

- Hermes plugin Doctor on the active Termux plugin: passed; six tools and four hooks discovered.
- Isolated functional test using Hermes' bundled Python 3.14.6: all six tool handlers and four hooks passed.
- Dummy agent registration/completion and lifecycle writes were isolated in a temporary directory.
- A separate compatibility test copy with `requires_hermes >=0.22.2` passed validate and Doctor on installed Hermes 0.22.2.

## Compatibility caveat

The repository's official `plugin.yaml` and catalog metadata retain `requires_hermes: >=0.22.6`. The local Hermes installation is 0.22.2. Passing Doctor and a temporary lowered-minimum compatibility copy does not establish that the unmodified repository meets its declared minimum on this device. Do not lower the published minimum merely to make an older local installation pass.

## Desktop evidence still required

The backend emits plugin events and the Desktop source contains matching listeners. Source inspection and event-contract tests are useful evidence, but they do not prove that the pane renders in a live compatible Hermes Desktop session. A genuine runtime test and screenshot/video remain outstanding.

## Product boundary

Rariflat recommends previously observed tools and agents; it does not autonomously dispatch tasks, install agents, or execute recommendations. Guard enforcement is opt-in and disabled by default. Local ranking signals are operational evidence, not calibrated confidence or a universal quality benchmark.
