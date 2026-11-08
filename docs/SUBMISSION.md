# Submission checklist

This checklist separates the plugin-repository PR from the upstream Hermes catalog PR. Nothing here submits or publishes automatically.

## 1. Local checks
Run from the plugin repository:
```bash
python -m pip install pytest pyyaml
python -m pytest tests -v -rs
git diff --check
bash -n install.sh
hermes plugins validate .
```

Latest recorded local result for commit `e713984`: **50 passed, 0 skipped**; `hermes plugins validate .`, `git diff --check`, and `bash -n install.sh` passed on Android/Termux. Run the checks again after any code change. `hermes plugins doctor .` was not confirmed in that run.

## 2. Plugin repository PR
The development branch is `feat/rariflat-1.2.0-submission`. Open a PR from that branch into `main`; do not push this work directly to `main`. Review the changed files and CI results before merging.

## 3. Pin the final SHA for the upstream catalog
After the plugin code is final and committed, get its full SHA:
```bash
git rev-parse HEAD
```
Put that exact 40-character SHA in the `sha:` field of the copy of `plugin-catalog/rariflat.yaml` submitted to `NousResearch/hermes-agent`. The in-repo catalog file may keep the placeholder until then. Any later code change requires a new commit, a new test run, and a new SHA.

## 4. Separate upstream PR to `NousResearch/hermes-agent`
- Add exactly one file: `plugin-catalog/rariflat.yaml` (with the real SHA).
- Use `docs/PR.md` as the upstream catalog PR description.
- Upstream CI is responsible for checking the catalog schema and pinned commit.
- If CI reports an unmapped commit-author email, follow the upstream contributor instructions; do not assume this is required unless CI reports it.

## 5. Demo and external submission
Record a demo following `docs/DEMO.md` (under 90 seconds), publish it as required by the official announcement, and submit the repository, upstream PR, and video links through the official form. Verify the current rules and deadline from the announcement before submitting; they are not asserted by this checklist.
