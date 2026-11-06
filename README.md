# Rariflat — Hermes Agent Plugin

**Visual Agent Status + Multi-Agent Router**

Characters come alive on every tool call. Skills are routed by **rarity + restraint**.

Built for the [Hermes Agent Plugin Hackathon](https://x.com/NousResearch/status/2118094256438936062).

## What it does

### Visual Agent Status
Every tool call wakes a character with unique reactions:

| Tool type       | Character     | Example                          |
|-----------------|---------------|----------------------------------|
| web / search    | Owl 🦉       | scans the horizon / hoots softly |
| terminal / code | Hephaestus ⚒️  | stokes the forge / strikes true  |
| memory          | Mnemosyne 🧠  | stirs the waters of memory       |
| error / block   | Cerberus 🐾    | all three heads rise             |
| default         | Hermes 🚀      | laces the winged sandals         |

Reactions appear in the terminal and in a **Desktop pane**.

### Multi-Agent Router
`rariflat_route` ranks skills by rarity and restraint. Scores update on every call and persist between sessions.

## Install

```bash
cp -r . ~/.hermes/plugins/rariflat
hermes plugins enable rariflat

# Optional Desktop pane
mkdir -p $HERMES_HOME/desktop-plugins/rariflat
cp desktop/plugin.js $HERMES_HOME/desktop-plugins/rariflat/
```

## Usage

- Any tool call → character awakens and reacts
- `/rariflat` → show current skill rankings
- Ask Hermes to call `rariflat_route` with a task

## Submission

- Catalog entry template: `plugin-catalog/rariflat.yaml`
- PR description: `docs/PR.md`
- Demo script: `docs/DEMO.md`
- Full checklist: `docs/SUBMISSION.md`

---

*Rariflat — characters that live with your agent.*
