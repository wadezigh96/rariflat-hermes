# Demo Video Script (< 90 seconds)

**0:00–0:08** "Agent tools are invisible, and when they loop or fail you only find out later. Rariflat fixes that."
**0:08–0:25** Ask Hermes to search the web, then run a terminal command. Owl and Hephaestus appear in the Desktop pane (and as log lines if RARIFLAT_VERBOSE=1).
**0:25–0:45** `/rariflat guard on`. Trigger a failing tool 3 times. Cerberus appears: "cooling down for ~60s". Show it recover on its own.
**0:45–0:60** Make the agent repeat the same call. Cerberus flags the loop.
**0:60–0:80** Ask: "which tool is best for finding an asyncio tutorial?" → `rariflat_route` answers with *why* (matched keywords, reliability).
**0:80–0:88** `/rariflat explain web_search` → reliability, rarity, restraint. "Local-only, opt-in guard, tests included. Rariflat." Tag @NousResearch.
