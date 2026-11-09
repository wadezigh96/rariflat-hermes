# Submission checklist

## Verify the plugin before publishing

- [x] Run `python -m pytest -q tests`, `node --test tests/desktop_event_contract.test.mjs`, `bash tests/test_install.sh`, and `git diff --check`.
- [x] Run `hermes plugins validate . --install-deps` and `hermes plugins doctor .` using Hermes `>=0.22.6`, against source SHA `770841abcf47ce831ef3d3035926862161034720`.
- [x] Confirm `plugin.yaml` capabilities match the registered tools and hooks (6 tools, 4 hooks).
- [ ] Test the optional Desktop pane in Hermes Desktop and capture a genuine screenshot for the catalog PR; unit tests alone do not prove live Desktop integration.
- [x] Push the finished source changes. The draft entry at `plugin-catalog/rariflat.yaml` and immutable install instructions now pin the pushed 40-character source SHA above. Never pin an unpushed or older tree.

## Complete the contest entry

The local YAML file in this repository is only a draft. The required catalog PR must add one `plugin-catalog/rariflat.yaml` file to the official [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent) repository. It must pin the exact public source commit and include accurate capabilities and disclosure. A PR to this Rariflat repository does not satisfy that catalog requirement.

- [x] Update the existing catalog PR #151221 in `NousResearch/hermes-agent` to the exact pushed SHA and matching compatibility/disclosure metadata ([fork commit `78c6101eab`](https://github.com/wadezigh96/hermes-agent/commit/78c6101eab)).
- [ ] Add a genuine Hermes Desktop screenshot to PR #151221 after testing the live pane; contract tests are not a substitute for runtime evidence.
- [ ] Post a working demo video on X, keep it under 90 seconds, show the plugin operating, and tag `@NousResearch`.
- [ ] Submit both the official catalog PR link and the X demo link through the [hackathon entry form](https://form.typeform.com/to/FwJLvOln).
- [ ] Submit by **5:00 PM Eastern Time on November 11, 2026**, per the [official announcement](https://x.com/NousResearch/status/2118094256438936062).

The [demo outline](DEMO.md) is designed to show usefulness, reliability, polish, and the plugin behavior judges need to see. Do not use a mock UI in place of the running plugin.
