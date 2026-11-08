# Rariflat 2.0.0

Rariflat adds live status characters, local reliability learning, task-aware tool recommendations, and an **opt-in** failure-streak / repeated-call guard to Hermes Agent.

It is designed to make tool activity easier to understand, help operators compare tools using observed outcomes, and surface repeated-call or failure patterns without silently taking over agent execution.

## Problems Rariflat helps address

| Operational problem | How Rariflat helps | Important limitation |
|---|---|---|
| Tool calls are hard to follow in a busy agent session | Character reactions and an optional Desktop pane show tool activity and outcomes | The pane depends on Hermes Desktop and the supported plugin event bridge |
| Operators do not know which previously used tool may fit a task | `rariflat_route` ranks observed tools using task fit, reliability, rarity, and restraint, with measured values and an explanation | It recommends only; it does not dispatch work to agents, call the recommended tool, or guarantee the best result |
| Reliability is difficult to compare from memory | Local success/use counts and failure streaks provide a lightweight evidence trail | Scores reflect only activity observed since Rariflat was installed and can be reset |
| Repeated identical calls can waste time or tokens | Optional loop detection can block a configured repeated-call pattern | Disabled unless explicitly enabled and configured; tune thresholds for the workflow |
| Repeated failures may cause an agent to retry without noticing a pattern | Optional failure-streak guard can block after a configured number of consecutive failures | Disabled by default; it is a simple guard, not a replacement for application-level retries, budgets, or human review |

## How ranking works

The advisory router uses a weighted score:

- **Task fit — 40%:** overlap between task tokens and tokens learned from observed tool names and arguments.
- **Reliability — 25%:** observed successful calls divided by observed calls, with a neutral 50% starting value for an unseen tool.
- **Rarity — 20%:** less frequently used tools receive a higher rarity score.
- **Restraint — 15%:** fewer repeated identical calls receive a higher restraint score.

Each recommendation includes the measured factor values, use/repeat counts, and a human-readable reason. New installations have little or no history, so recommendations become more informative as the user works.

**Router boundary:** `rariflat_route` returns ranked tool/skill names and `dispatches_to_agent: false`. It does not route a task to another agent, invoke tools, or execute a plan.

## Quick start

### 1. Requirements

- A working Hermes Agent installation with plugin support.
- Python available in the Hermes environment.
- For the optional Desktop pane: a Hermes Desktop build that supports the official plugin SDK and event bridge.

### 2. Install Rariflat

Until the official catalog PR is accepted and published, install the reviewed source revision directly:

```bash
hermes plugins install wadezigh96/rariflat-hermes --ref 950796253faa2d9b69c3c2d1256924d18ae03e9c --enable
```

The `--ref` value is a full immutable 40-character commit SHA. The command uses Hermes' documented Git installation flow; `--enable` skips the enable prompt. Review and accept any dependency-consent prompt shown by Hermes. After the catalog listing is accepted, users can install by catalog name with `hermes plugins install rariflat --enable`.

### 3. Validate the plugin

From the Rariflat plugin directory, run:

```bash
python -m pytest -q tests
hermes plugins validate . --install-deps
hermes plugins doctor .
```

The test suite checks ranking, measured rarity/restraint behavior, safe fingerprinting, guard behavior, and other plugin logic. Validation against an installed Hermes CLI checks compatibility with that installation. A passing unit test suite alone does not prove that a particular Desktop runtime is connected.

### 4. Start using it

After Hermes loads the plugin:

- Use the Hermes plugin/tool interface to call `rariflat_status` and inspect tracked tools and guard status.
- Call `rariflat_route` with a task description to receive advisory recommendations.
- Use the `/rariflat` command to view local reliability status.
- Make ordinary tool calls. Rariflat learns from observed `pre_tool_call` and `post_tool_call` events; it does not have historical data from before installation.

Example task for the recommendation tool:

```json
{
  "task": "Find the official documentation for Python asyncio and summarize the key usage examples"
}
```

Example response fields include:

```json
{
  "router_type": "tool_skill_recommender",
  "dispatches_to_agent": false,
  "best": "web_search",
  "recommended": [
    {
      "skill": "web_search",
      "score": 74.2,
      "task_match_score": 80.0,
      "reliability": 90.0,
      "rarity": 35.0,
      "restraint": 100.0,
      "reason": "..."
    }
  ]
}
```

The values above are illustrative only; actual results depend on locally observed history.

### 5. Enable the optional guard only when ready

The guard is **off by default**. Enable or disable it from the command:

```text
/rariflat guard on
/rariflat guard off
```

Or configure it before starting Hermes:

```bash
export RARIFLAT_GUARD=1
export RARIFLAT_FAIL_STREAK=3
export RARIFLAT_COOLDOWN=30
export RARIFLAT_LOOP_REPEAT=3
export RARIFLAT_LOOP_WINDOW=30
```

- `RARIFLAT_FAIL_STREAK`: consecutive failures before the failure-streak guard blocks (default: 3).
- `RARIFLAT_COOLDOWN`: seconds before a failure-streak lockout can recover (default: 30).
- `RARIFLAT_LOOP_REPEAT`: repeated identical calls required for loop protection; `0` disables loop detection (default: 0).
- `RARIFLAT_LOOP_WINDOW`: repeated-call observation window in seconds (default: 30).
- `RARIFLAT_DATA_DIR`: optional directory override for local score storage.
- `RARIFLAT_VERBOSE=1`: enable character logs.

Start with conservative thresholds and test in a non-critical workflow. The guard is a lightweight safeguard, not a substitute for tool-level permissions, rate limits, idempotency, or operator approval.

### 6. Optional Desktop pane

The Desktop UI is provided in `desktop/plugin.js` and listens for the plugin event bridge. It displays the latest tool activity and a short recent history. It requires a compatible Hermes Desktop runtime; command-line tests of the event contract do not by themselves prove live Desktop integration.

## Data handling and reset

- Scores are stored locally at `~/.hermes/plugin-data/rariflat/scores.json`, unless `RARIFLAT_DATA_DIR` is set.
- Tool arguments are inspected in memory to learn non-secret task tokens and build repeated-call fingerprints.
- Credential-like fields and recognized inline secret patterns are filtered before token learning and fingerprinting. No raw arguments or credentials are intentionally persisted.
- Rariflat itself does not initiate network requests, telemetry, or subprocess execution.
- Review your own tool payloads and environment before enabling plugins; pattern-based redaction cannot guarantee detection of every possible secret format.
- Clear learned scores with:

```text
/rariflat reset
```

Resetting removes the local learned history, so recommendations start learning again.

## Troubleshooting

- **No recommendations:** make some ordinary tool calls first; Rariflat needs observed history.
- **Recommendations seem weak:** provide a more specific task description and allow more representative calls to accumulate.
- **Guard blocks too often:** turn it off with `/rariflat guard off`, then raise `RARIFLAT_FAIL_STREAK` or `RARIFLAT_LOOP_REPEAT` before re-enabling.
- **Desktop pane is empty:** confirm your Desktop version supports the plugin SDK/event bridge and that the plugin is loaded. The pane is optional; core CLI/plugin tools can work without it.
- **Validation fails:** check the Hermes version, run `hermes plugins validate . --install-deps`, and inspect the full error output before changing the manifest.

## Development and tests

```bash
python -m pytest -q tests
node --test tests/desktop_event_contract.test.mjs
git diff --check
hermes plugins validate . --install-deps
hermes plugins doctor .
```

Run `hermes plugins doctor .` in the plugin directory for Hermes runtime-contract diagnostics. CI tests and manifest validation are useful checks, but do not replace a manual end-to-end test on the target Hermes Desktop version.

## Project scope

Rariflat is an observability, local scoring, recommendation, and optional guard plugin. It is not an autonomous multi-agent dispatcher, does not guarantee performance improvements, and does not replace human oversight.
