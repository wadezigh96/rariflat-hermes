# Rariflat Quickstart and Practical Use Cases

Rariflat is a Hermes Agent plugin that makes tool activity visible, learns from observed tool outcomes, and recommends previously observed tools for a task. It does not index installed skills. This guide covers installation, first run, everyday workflows, and the problems it is designed to help with.

> **Important scope:** Rariflat is an advisory tool recommender. It ranks tool names observed by its hooks; it does not assign work to agents, dispatch tasks, or execute the recommended tool on your behalf.

## 1. Requirements

- A working Hermes Agent installation.
- Python support provided by the Hermes plugin runtime.
- Internet access for the initial Git installation.
- Hermes Desktop is optional. The core hooks and tools can be used without the Desktop pane.

## 2. Install Rariflat

Until the Rariflat entry is accepted into the official Hermes plugin catalog, install the public repository at the validated immutable source commit:

```bash
hermes plugins install wadezigh96/rariflat-hermes --ref 911a10bac40ff536115f7485d4bba42186f36e83 --enable
```

The full 40-character SHA pins the install to the latest public source revision checked during this audit. Do not replace it with `main`, a branch name, or a shortened SHA when you need a reproducible install. After publishing the local audit fixes, update this command and the official catalog PR to the exact pushed commit.

If the catalog listing is approved and published later, the shorter catalog-based flow will be:

```bash
hermes plugins install rariflat --enable
```

## 3. Verify the installation

Check that Hermes sees the plugin:

```bash
hermes plugins list
```

Validate the installed plugin and run the isolated plugin diagnostic:

```bash
hermes plugins validate ~/.hermes/plugins/rariflat --install-deps
hermes plugins doctor rariflat
```

If your Hermes installation uses a custom home directory, replace `~/.hermes/plugins/rariflat` with the actual plugin path.

Start a new Hermes session after installation or enabling. Make a few ordinary tool calls so Rariflat can observe outcomes and build its local history. A fresh installation has little or no history, so recommendations become more useful as relevant tools are used.

## 4. Try the first workflow

Ask Hermes to inspect the available Rariflat recommendations for a concrete task. For example:

```text
Use rariflat_route to recommend the best previously observed tool for:
"Find the official documentation for Python asyncio and summarize the key usage patterns."
Explain task fit, reliability, rarity, and restraint. Do not execute the recommendation yet.
```

Rariflat returns up to five ranked candidates from tool names observed by its hooks, including:
- **Task fit** — overlap between task terms and the candidate's learned tokens.
- **Reliability** — observed successful calls divided by observed calls, with a neutral starting value before history exists.
- **Rarity** — a usage-frequency score; less frequently used tools receive a higher rarity score.
- **Restraint** — a score reduced by repeated identical calls observed within the 30-second window.
- **Reason** — a readable explanation with measured values and the weighting used.

The ranking weights are 40% task fit, 25% reliability, 20% rarity, and 15% restraint. The result is a recommendation, not an automatic tool invocation.

## 5. Useful commands

Show the current local reliability and guard summary:

```text
/rariflat
```

Enable the optional guard:

```text
/rariflat guard on
```

Disable the guard (the default state):

```text
/rariflat guard off
```

Clear the learned local scores and start fresh:

```text
/rariflat reset
```

The guard can block a tool call after the configured consecutive-failure threshold or when the optional repeated-call detector identifies a loop. Keep it disabled until you understand your workflow and have tested the thresholds you intend to use. It is not a substitute for backups, approvals, or application-level safety controls.

## 6. Problems Rariflat can help solve efficiently

### A. Choosing among tools that can perform similar tasks
**Problem:** A task could be handled by a browser, search tool, or terminal tool. Choosing manually every time adds friction.

**How Rariflat helps:** It compares task-token fit with observed reliability, usage rarity, and repeated-call restraint, then explains its ranking. This is most useful after the relevant tools have accumulated representative history.

### B. Repeating an unreliable workflow
**Problem:** A tool or workflow repeatedly fails, but the pattern is difficult to notice across many calls.

**How Rariflat helps:** It tracks local success counts and failure streaks. The status command makes the observed record visible, while reliability contributes to future recommendations.

### C. Repeated identical calls and potential loops
**Problem:** An agent may issue the same call repeatedly without making progress.

**How Rariflat helps:** The optional guard can detect repeated identical calls within a configurable time window and block them when explicitly enabled and configured. It is off by default.

### D. Limited visibility into tool activity
**Problem:** Tool calls happen in the background, making it harder to understand what the agent is doing.

**How Rariflat helps:** Character reactions identify common tool families and reflect started, completed, failed, or blocked events. The optional Hermes Desktop pane shows recent activity when the Desktop plugin surface is available.

### E. Comparing tool behavior over time
**Problem:** Teams need a lightweight local signal for which tools are used often, succeed consistently, or trigger repeated calls.

**How Rariflat helps:** It maintains local usage and outcome statistics and exposes measured ranking factors. These are operational signals, not a formal benchmark or proof that one tool is universally better.

## 7. Optional configuration

Set environment variables before starting Hermes when you need custom behavior:

| Variable | Default | Purpose |
|---|---:|---|
| `RARIFLAT_GUARD` | `0` | Set to `1` to enable the guard at startup. |
| `RARIFLAT_FAIL_STREAK` | `3` | Consecutive failures before the failure-streak guard blocks a tool. |
| `RARIFLAT_COOLDOWN` | `30` | Seconds before a failure-streak lockout can recover automatically. |
| `RARIFLAT_LOOP_REPEAT` | `0` | Repeated identical calls needed to trigger loop protection; `0` disables this detector. |
| `RARIFLAT_LOOP_WINDOW` | `30` | Repeated-call detection window in seconds. |
| `RARIFLAT_DATA_DIR` | Active Hermes home via `plugin_data_dir()` | Override the local score directory. |
| `RARIFLAT_VERBOSE` | `0` | Set to `1` for additional character logs. |

## 8. Data handling and limitations

- Rariflat stores its learned score data locally under the active Hermes home at `plugin-data/rariflat/scores.json`, using Hermes' profile-aware `plugin_data_dir()` API, unless `RARIFLAT_DATA_DIR` is set.
- Tool arguments are inspected in memory to extract task tokens and calculate repeat fingerprints. Credential-like fields and recognized inline secrets are filtered before learning and fingerprinting. Raw arguments and credential values are not intentionally persisted.
- The plugin itself does not initiate network requests, telemetry, or subprocess execution.
- Rarity and restraint are relative to the observed local history. A new installation has limited evidence; rankings should not be treated as objective quality scores.
- The Desktop pane requires a compatible Hermes Desktop plugin runtime and event bridge. The Python hooks and tools remain the primary functionality.
- Rariflat does not dispatch tasks to agents, execute recommendations, guarantee fewer failures, or replace human review.

## 9. Run the test suite from a source checkout

```bash
python -m pytest -q tests
node --test tests/desktop_event_contract.test.mjs
hermes plugins validate . --install-deps
hermes plugins doctor .
```

These checks cover the Python behavior, the Desktop event contract, and Hermes plugin validation. The event-contract tests do not by themselves prove end-to-end behavior in every live Hermes Desktop version.

## 10. Troubleshooting

**The plugin does not appear in Hermes**
- Run `hermes plugins list`.
- Confirm that the installation completed and that the plugin is enabled.
- Start a new Hermes session.

**Recommendations are empty**
- Rariflat needs observed tool history. Make a few representative calls, then ask for a recommendation again.

**The guard blocks a call**
- Run `/rariflat` to inspect status.
- Turn it off with `/rariflat guard off` if the block is unexpected.
- Review `RARIFLAT_FAIL_STREAK`, `RARIFLAT_LOOP_REPEAT`, and `RARIFLAT_LOOP_WINDOW` before enabling it again.

**Desktop characters do not appear**
- Confirm that you are using a compatible Hermes Desktop plugin runtime.
- Verify that the Desktop plugin is loaded and that the host exposes the official plugin event bridge.
- The Python hooks can still work even when the Desktop pane is unavailable.

## Links

- [Rariflat source repository](https://github.com/wadezigh96/rariflat-hermes)
- [Hermes plugin documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Hermes plugin catalog documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugin-catalog)
