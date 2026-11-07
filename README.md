# Rariflat — Hermes Agent Plugin

**Visual Agent Status + Intelligent Skill Router + Restraint Guard**

Characters come alive on every tool call. Skills are ranked by rarity + restraint. Low-restraint tools can be blocked.

## Features
- Living characters on every tool call (Owl, Hephaestus, Cerberus, etc.)
- Persistent rarity + restraint scores
- `rariflat_route` — recommend the best skill for a task
- `rariflat_guard` — check if a tool should be blocked
- Pre-hook can block low-restraint tools
- `/rariflat` command for rankings
- Desktop pane support

## Install
```bash
cp -r . ~/.hermes/plugins/rariflat
hermes plugins enable rariflat
```

## Usage
- Any tool call → character reacts
- `/rariflat` → rankings
- Ask Hermes to call `rariflat_route` or `rariflat_guard`

Built for the Hermes Agent Plugin Hackathon.
