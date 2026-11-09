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

The displayed ranking score blends current task capability fit (60%) with historical performance (40%) once there are five observations. Before that threshold, ranking is provisional and uses capability fit only; tier remains UNRANKED.

Historical performance is calculated from locally recorded completed tasks:
- success rate = successful completions / recorded completions;
- average task fit = lexical overlap between task wording and declared capabilities;
- optional average quality = arithmetic mean of user/evaluator-supplied 0–100 quality scores;
- average duration = mean of supplied elapsed seconds.

When quality is available, performance score = 40% average task fit + 40% success rate + 20% average quality. When quality is not supplied, performance score = 50% average task fit + 50% success rate. Duration is displayed as an operational metric, not treated as quality or speed reward; faster is not automatically better.

## Register an agent

Use `rariflat_agent_register` with:
- `kind=hermes` for a Hermes catalog/repository agent and a verifiable `install_ref`;
- `kind=a2a` for an A2A agent, HTTPS `endpoint`, and Agent Card source.

Capabilities must be supplied from the actual catalog manifest or Agent Card. Do not invent capabilities. Registration stores metadata locally; it does not fetch remote URLs, install packages, connect to endpoints, or execute an agent.

## Record a completed task

Call `rariflat_agent_complete` only after an agent task really finishes. Supply the agent ID, task summary, actual boolean outcome, and optionally a 0–100 quality score and measured duration in seconds. Do not infer success from a submitted request or a running task. A failure is a completed attempt with `success=false`.

Each completion is timestamped locally. The registry keeps the latest 500 observations per agent. It does not claim independent verification: the outcome and optional quality value are supplied by the caller. The UI labels this as observed data.

## Rank agents

Call `rariflat_agent_rank` with the user's task. It ranks both Hermes and A2A records together and keeps their kind, source, and connection/install state visible. It recommends only; it does not dispatch tasks, install Hermes plugins, or connect to A2A endpoints.

## Installation and connection

This release intentionally does not execute arbitrary install instructions or connect to untrusted A2A endpoints. The Desktop pane shows the source and status so the user can review the origin first. Installation/connection requires a separate explicit, reviewed action. A registered agent is not represented as installed or connected.
