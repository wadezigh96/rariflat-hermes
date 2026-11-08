# Submission checklist

Do these in order. Nothing here is automatic.

## 1. Local checks
```bash
pip install pytest pyyaml
python -m pytest tests -v
hermes plugins validate .
hermes plugins doctor .
```

## 2. Commit, then pin the SHA
```bash
git add -A && git commit -m "Rariflat 1.2.0: opt-in guard, task-aware routing, safe persistence, working desktop events"
git push origin main
git rev-parse HEAD        # copy the full 40-character SHA
```
Put that SHA in the copy of `plugin-catalog/rariflat.yaml` that goes into your PR to hermes-agent (`sha:`).
The in-repo copy may keep the placeholder; do not make another commit just to store the SHA, because the SHA must point at the
code you tested. Any later code change needs a new commit, a new test run and a new SHA.

## 3. Pull request to `NousResearch/hermes-agent`
- Add exactly one file: `plugin-catalog/rariflat.yaml` (copy of this repo's file with the real `sha`).
- Use `docs/PR.md` as the PR description.
- Upstream CI (`plugin-catalog-ci`) checks the schema and that the pinned SHA is reachable and passes `hermes plugins validate`.
- If CI reports an unmapped commit-author email, add `contributors/emails/<email>` as described in upstream `contributors/README.md` (not verified whether it applies to you).

## 4. Demo video and form
Record following `docs/DEMO.md` (< 90 s), post on X tagging @NousResearch, and submit the repo, PR and video links through the official form from the announcement. The hackathon rules and deadline come from that announcement; they are not verified here.
