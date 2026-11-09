# Agent ranking: Hermes catalog + A2A

Rariflat provides a second ranking surface alongside tool/skill ranking.

## Tier thresholds

Tier is based on the agent's observed performance score and is withheld until at least five completed-task observations exist:

| Tier | Score |
|---|---:|
| MYTHIC | 90–100 |
| LEGEND | 80–89.99 |
| EPIC | 70–79.99 |
| DEVELOPING | Below 70 |
| UNRANKED | Fewer than five observations |

Ranking order is tier-first: MYTHIC, then LEGEND, then EPIC, then DEVELOPING, with UNRANKED last. Within a tier, the displayed ranking score breaks ties. That score blends current task capability fit (60%) with historical performance (40%) once there are five observations. Before that threshold, ranking is provisional and uses capability fit only; tier remains UNRANKED.

For Hermes delegated subagents, `subagent_start` / `subagent_stop` lifecycle hooks capture the role, goal, completion status, and measured duration when both events can be correlated by `child_session_id`. Hermes includes `child_subagent_id` at start but does not guarantee it in the stop payload; if the shared session ID is absent, Rariflat deliberately skips attribution rather than guessing between concurrent children. When correlation is available, the local ranking updates without a manual rating call. The hook records only the bounded task goal/summary needed for fit scoring; it does not store raw tool inputs or outputs. Primary-agent turns are not automatically attributed to a catalog agent.\n\nFor A2A agents, call `rariflat_agent_complete` from the integration that knows the real A2A task outcome; the generic Hermes subagent hook cannot reliably infer which external A2A endpoint completed a task.\n\nHistorical performance is calculated from locally recorded completed tasks:
- success rate = successful completions / recorded completions;
- average task fit = lexical overlap between task wording and declared capabilities;
- optional average quality = arithmetic mean of user/evaluator-supplied 0–100 quality scores;
- average duration = mean of supplied elapsed seconds.

When quality is available, performance score = 40% average task fit + 40% success rate + 20% average quality. When quality is not supplied, performance score = 50% average task fit + 50% success rate. Duration is displayed as an operational metric, not treated as quality or speed reward; faster is not automatically better.

## Register an agent

Use `rariflat_agent_register` with:
- `kind=hermes` for a Hermes catalog/repository agent and a verifiable `install_ref`;
- `kind=a2a` for an A2A agent, HTTPS `endpoint`, and Agent Card source.

Capabilities must be supplied from the actual catalog manifest or Agent Card. Do not invent capabilities. Registration stores metadata locally; it does not fetch remote URLs, install packages, connect to endpoints, or execute an agent. Runtime-observed Hermes subagent roles are registered separately from installable plugin catalog entries.

## Record a completed task

Call `rariflat_agent_complete` only after an agent task really finishes. Supply the agent ID, task summary, actual boolean outcome, and optionally a 0–100 quality score and measured duration in seconds. Do not infer success from a submitted request or a running task. A failure is a completed attempt with `success=false`.

Each completion is timestamped locally. The registry keeps the latest 500 observations per agent. It does not claim independent verification: the outcome and optional quality value are supplied by the caller. The UI labels this as observed data.

## Rank agents

Call `rariflat_agent_rank` with the user's task. It ranks both Hermes and A2A records together and keeps their kind, source, and connection/install state visible. It recommends only; it does not dispatch tasks, install Hermes plugins, or connect to A2A endpoints.

## Installation and connection

For registered Hermes agents with a validated GitHub `owner/repository` install reference, the Desktop card offers the official `hermes://plugin/install?...&enable=1` deep link. Hermes Desktop opens its own install review and confirmation flow; Rariflat never clones, runs shell commands, grants capabilities, or installs silently. Runtime-observed subagent roles are not installable plugins. For A2A agents, the card opens the declared Agent Card source for review only; this release does not implement an A2A connection handshake. Installation/connection always requires a separate explicit, reviewed action. A registered agent is not represented as installed or connected.
