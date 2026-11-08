# Demo script (< 90 seconds) — every step below works as described

Before recording: `./install.sh`, `hermes plugins enable rariflat`, open the Desktop app, toggle **rariflat** on in Settings → Plugins,
and make sure the Rariflat pane is visible ("Waiting for tool calls…").

1. **0:00–0:10** Say what it is: "Rariflat shows who is working on each tool call and tracks which tools are reliable."
2. **0:10–0:25** Ask Hermes to search the web → the pane shows the Owl working, then ✓.
3. **0:25–0:40** Ask it to run a shell command → Hephaestus. Then run one that fails (e.g. `cat /nope`) → ✗ "encountered resistance".
4. **0:40–0:55** Type `/rariflat` → reliability ranking with uses. Ask Hermes to call `rariflat_route` with "search the web for news" → it recommends the web tool it has actually used.
5. **0:55–1:10** Open `config.json`, set `{"guard": {"enabled": true, "deny": ["terminal"]}}`, ask for a terminal command again → Cerberus ⛔ in the pane and the agent is told the tool was blocked by your Rariflat configuration.
6. **1:10–1:20** Close: "Guard is off by default, everything stays local, and it's tested." Tag @NousResearch.

Tip: the exact tool names depend on your Hermes build (e.g. the terminal tool may not be called `terminal`); check `/rariflat` after a few calls and use the real name in the deny list.
