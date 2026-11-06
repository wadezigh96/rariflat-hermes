# Rariflat — Hermes Agent Plugin

**Visual Agent Status + Multi-Agent Router**

Characters come alive on every tool call. Skills are routed by **rarity + restraint**.

Built for the [Hermes Agent Plugin Hackathon](https://x.com/NousResearch/status/2118094256438936062).

## What it does

### 1. Visual Agent Status
Every tool call wakes a character:

| Tool type     | Character    | Reaction                  |
|---------------|--------------|---------------------------|
| web / search  | Owl 🦉      | scans the horizon         |
| terminal / code | Hephaestus ⚒️ | forges the command      |
| memory        | Mnemosyne 🧠 | recalls the past          |
| error         | Cerberus 🐾  | guards against failure    |
| default       | Hermes 🚀    | moves swiftly             |

Reactions appear in the terminal and in a **Desktop pane** (right side).

### 2. Multi-Agent Router
`rariflat_route` tool scores available skills by:
- **Rarity** — how specialized / high-performing
- **Restraint** — how often it declines risky actions

It recommends the best skill for the task.

## Install (local)

```bash
# Clone or copy this folder into your plugins directory
cp -r . ~/.hermes/plugins/rariflat
# or
hermes plugins install /path/to/rariflat-hermes

hermes plugins enable rariflat
```

Desktop pane (optional):
```bash
mkdir -p $HERMES_HOME/desktop-plugins/rariflat
cp desktop/plugin.js $HERMES_HOME/desktop-plugins/rariflat/
```

## Usage

- Make any tool call → character wakes up in the log / Desktop pane
- `/rariflat` → show current skill rankings
- Ask Hermes to call `rariflat_route` with a task

## Hackathon submission

1. This repo is the plugin source
2. Open a PR to `NousResearch/hermes-agent` adding `plugin-catalog/rariflat.yaml`
3. Post a <90s demo video on X tagging `@NousResearch`
4. Submit both links via the form

## Demo script idea (under 90s)

1. Show Desktop pane empty
2. Ask Hermes to search the web → Owl appears
3. Ask it to run a terminal command → Hephaestus appears
4. Call `/rariflat` or `rariflat_route` → show ranking
5. End with the character reacting to success

---

*Rariflat — characters that live with your agent.*
