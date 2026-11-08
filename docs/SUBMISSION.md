# Submission checklist

## Verify the plugin before publishing

- [ ] Run `python -m pytest -q tests`, `node --test tests/desktop_event_contract.test.mjs`, `bash tests/test_install.sh`, and `git diff --check`.
- [ ] Run `hermes plugins validate . --install-deps` and `hermes plugins doctor .` using the current Hermes CLI.
- [ ] Confirm `plugin.yaml` capabilities match the registered tools and hooks.
- [ ] Test the optional Desktop pane in Hermes Desktop and capture a genuine screenshot for the catalog PR; unit tests alone do not prove live Desktop integration.
- [ ] Push the finished source changes. Then use the pushed 40-character commit SHA in the draft entry at `plugin-catalog/rariflat.yaml` and in the immutable install instructions. Never pin an unpushed or older tree.

## Complete the contest entry

The local YAML file in this repository is only a draft. The required catalog PR must add one `plugin-catalog/rariflat.yaml` file to the official [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent) repository. It must pin the exact public source commit and include accurate capabilities and disclosure. A PR to this Rariflat repository does not satisfy that catalog requirement.

- [ ] Open the catalog PR to `NousResearch/hermes-agent` with the exact pushed SHA, a description of the plugin and Hermes surfaces used, security/disclosure notes, and the Desktop screenshot.
- [ ] Post a working demo video on X, keep it under 90 seconds, show the plugin operating, and tag `@NousResearch`.
- [ ] Submit both the official catalog PR link and the X demo link through the [hackathon entry form](https://form.typeform.com/to/FwJLvOln).
- [ ] Submit by **5:00 PM Eastern Time on November 11, 2026**, per the [official announcement](https://x.com/NousResearch/status/2118094256438936062).

The [demo outline](DEMO.md) is designed to show usefulness, reliability, polish, and the plugin behavior judges need to see. Do not use a mock UI in place of the running plugin.
