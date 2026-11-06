# Rariflat — Hermes Agent Plugin

**Visual Agent Status + Multi-Agent Router**

Characters come alive on every tool call. Skills are routed by **rarity + restraint**.

Built for the [Hermes Agent Plugin Hackathon](https://x.com/NousResearch/status/2118094256438936062).

## What it does

### 1. Visual Agent Status
Every tool call wakes a character with unique reactions:

| Tool type       | Character     | Example reaction                     |
|-----------------|---------------|--------------------------------------|
| web / search    | Owl 🦉       | “scans the horizon” / “hoots softly”      |
| terminal / code | Hephaestus ⚒️  | “stokes the forge” / “strikes true”      |
| memory          | Mnemosyne 🧠  | “stirs the waters of memory”         |
| file            | Archivist 📜   | “unrolls an ancient scroll”          |
| error / block   | Cerberus 🐾    | “all three heads rise”               |
| default         | Hermes 🚀      | “laces the winged sandals”           |

Reactions appear in the terminal and in a **Desktop pane**.

### 2. Multi-Agent Router
`rariflat_route` scores skills by:
- **Rarity** — performance and specialization
- **Restraint** — how often risky actions are declined

It recommends the best skill for the task. Scores update automatically on every tool call.

## Install

```bash
# Agent plugin
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

See `docs/SUBMISSION.md` for the full checklist (catalog PR + demo video + form).

---

*Rariflat — characters that live with your agent.*
