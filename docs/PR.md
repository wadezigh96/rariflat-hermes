# Pull Request Description (copy into your PR)

## Rariflat — Visual Agent Status + Multi-Agent Router

Characters come alive on every tool call. Skills are ranked and routed by **rarity + restraint**.

### What it does
- Hooks `pre_tool_call` and `post_tool_call` to show a living character reaction (Owl, Hephaestus, Mnemosyne, Cerberus, etc.)
- Tracks success rate and restraint per tool/skill and persists scores
- Provides `rariflat_route` tool and `/rariflat` command for ranking and routing
- Optional Desktop pane that visualizes the active character and recent history

### Surfaces used
- Python plugin hooks and tools (`ctx.register_tool`, `ctx.register_hook`, `ctx.register_command`)
- Desktop Plugin SDK (optional pane + status chip)

### Disclosure
- Local file persistence under `~/.hermes/plugin-data/rariflat/scores.json`
- No network calls
- No credentials required
- No shell commands executed by the plugin itself

### Screenshots
(Attach a screenshot of the Desktop pane and a short terminal log of character reactions.)

Repo: https://github.com/wadezigh96/rariflat-hermes
