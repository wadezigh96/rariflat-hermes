# Rariflat 2.0.0 — Live Demo

This is the reproducible **Hermes CLI** demo. It installs the pinned Rariflat source through Hermes' own plugin manager, enables it, checks discovery/registration with Plugin Doctor, and then asks the real Hermes agent to invoke Rariflat tools.

> Scope: this is a CLI live demo. It is not proof of the Hermes Desktop pane. Desktop UI verification requires a real compatible Hermes Desktop runtime.

## Requirements

- Hermes Agent CLI installed and on PATH.
- A working model/provider configured in Hermes (the final agent run uses your configured provider).
- Network access for the Git installation and the harmless search step.
- A terminal session where you can approve any tool permissions Hermes requests.

## Run on Android / Termux

From a Termux shell:

```bash
pkg update
pkg install git
git clone --depth 1 --branch fix/rariflat-2.0.0-finalization-audit https://github.com/wadezigh96/rariflat-hermes.git
cd rariflat-hermes
bash scripts/live-demo.sh
```

The script:
1. Checks that Hermes is installed and prints its version.
2. Backs up an existing `~/.hermes/plugins/rariflat` before replacing it.
3. Installs the immutable source revision `c3434bb632707f1bef6b5a95883913bd2aac9595` using `hermes plugins install`.
4. Enables the plugin and lists installed plugins.
5. Runs `hermes plugins doctor` against the installed plugin.
6. Starts a one-shot, real Hermes agent session that calls `rariflat_status`, attempts harmless real tool calls only when available, and invokes `rariflat_route` for two distinct tasks.

The script does not set up API credentials, enable the optional guard, modify project files, or grant tool permissions. If Hermes has no configured model/provider, the installation and Doctor checks can still complete, but the agent demonstration will stop at the provider/authentication error. Configure Hermes first with `hermes model` or your existing provider's setup flow.

## Expected verification

The installation portion must show:
- Hermes CLI version.
- Successful plugin installation.
- `rariflat` listed as enabled.
- Plugin Doctor reports successful discovery, manifest parsing, import, and registration.

The agent portion must show real tool calls/results and actual Rariflat output. A fresh install may have little or no observed history; if so, the output must say that rather than inventing rankings. Recommendations improve only after Rariflat observes ordinary tool calls.

## Manual fallback

If you prefer to run each step yourself:

```bash
hermes plugins install wadezigh96/rariflat-hermes --ref c3434bb632707f1bef6b5a95883913bd2aac9595
hermes plugins enable rariflat
hermes plugins list
hermes plugins doctor ~/.hermes/plugins/rariflat
hermes chat
```

In the chat session, ask Hermes to call `rariflat_status`, then make ordinary tool calls, then call `rariflat_route` with a concrete task. Do not treat a route recommendation as an automatic tool invocation.

## Desktop demonstration

The repository's automated Node tests validate the Desktop event contract, and Hermes CLI validation checks that the Desktop bundle stays within the supported plugin SDK surface. Neither is a live Desktop UI test. To claim a Desktop demo, load the installed plugin in a compatible Hermes Desktop build and capture genuine UI evidence from that running application.

## Troubleshooting

- **`hermes: command not found`:** install Hermes CLI and ensure its bin directory is on PATH.
- **Install/enable fails:** inspect the full Hermes error; do not bypass capability consent or use unpinned source.
- **Provider/auth error:** configure a working model with `hermes model`, then rerun the script.
- **No recommendations:** make ordinary real tool calls first; a new plugin has no pre-install history.
- **Desktop pane absent:** this CLI demo does not validate Desktop. Verify against a real compatible Desktop runtime.
