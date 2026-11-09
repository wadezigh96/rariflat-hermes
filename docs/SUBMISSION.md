# Submission checklist

## Source and validation

- [x] Source is published on the repository default branch at [commit 5d00db7](https://github.com/wadezigh96/rariflat-hermes/commit/5d00db7bcc949405d035bf37dfa7b5ba51aaaa82).
- [x] README, quickstart, and the local catalog draft pin the same immutable source commit.
- [x] The plugin declares six tools and four hooks; the manifest and catalog draft list the same capabilities.
- [x] Python unit tests, Desktop event-contract tests, installer smoke test, and Hermes validation are part of GitHub Actions.
- [x] Local isolated functional testing on Hermes 0.22.2 exercised all six handlers and all four hooks using a temporary data directory.
- [ ] Validate the unmodified repository manifest on Hermes >=0.22.6. The installed Termux runtime is Hermes 0.22.2; its local compatibility test used a separate test copy with the minimum version lowered and does not satisfy this official requirement.
- [ ] Test the optional Desktop pane in a compatible Hermes Desktop runtime and capture a genuine screenshot. Contract tests and backend event inspection are not proof of a live UI session.

## Hackathon deliverables

- [ ] Confirm the official catalog PR status and ensure its entry pins the same validated source SHA.
- [ ] Record a genuine demo video under 90 seconds using the real Hermes runtime; do not substitute mock UI or simulated activity.
- [ ] Publish the demo and tag `@NousResearch`.
- [ ] Submit the official catalog PR link and demo link through the official entry form.
- [ ] Re-check the official deadline and submission requirements before submitting.

## Safety and scope

- Rariflat's router is advisory: it ranks previously observed tool names and does not dispatch tasks or execute recommendations.
- The guard is opt-in and disabled by default.
- Registry and score data are local. Rariflat itself does not initiate network requests, telemetry, or subprocess execution.
- Do not claim live Desktop integration until it has been tested in a compatible Desktop runtime.
