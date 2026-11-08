# Demo Video Script (< 90 seconds)

Record this with the actual Hermes Agent runtime and, if available, the compatible Hermes Desktop pane. Keep the final X video under 90 seconds. Avoid mockups: show real tool calls, the returned plugin data, the live route decision card, and the guard blocking a call.

**0:00–0:08 — Problem and plugin**

"When an agent uses tools, reliability and repeated-call patterns are hard to see. Rariflat turns observed tool activity into a local, explainable signal."

**0:08–0:24 — Live activity**

Run ordinary calls with at least three different tool/skill names supported by the runtime (for example, web/search, terminal, and file). Show the corresponding characters update in the Desktop pane. Briefly show `/rariflat` with the recorded usage and success counts. This gives the router enough candidates to display two alternatives; if fewer tools are available, show the alternatives it actually returns rather than manufacturing history.

**0:24–0:43 — Decision Card**

Call `rariflat_route` with a concrete task related to the calls just made, such as finding documentation. Show the top recommendation with all four factor scores and weights, plus scores and evidence badges for up to two alternatives. If the data is new, point out the limited-history badge; do not describe it as calibrated confidence. Say clearly that this is advisory: it does not dispatch another agent.

**0:43–1:07 — Reliability guard**

Show the guard disabled by default, enable it with `/rariflat guard on`, then produce the configured number of genuine failed calls. Make the next call to that tool and show the block event in the pane and the returned message. Do not claim a cooldown countdown: the guard reports a failure-streak or repeated-call reason.

**1:07–1:22 — Control and privacy**

Run `/rariflat guard off`, show the tool can be used again, and close with: "Scores stay local; the Desktop route card receives aggregate scores and counts, not the task text or tool arguments; argument-token learning can be disabled; the guard is opt-in." Tag `@NousResearch` in the X post.
