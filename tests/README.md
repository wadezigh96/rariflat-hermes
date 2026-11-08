# Tests

Run from the repo root (needs only `pytest`; `pyyaml` enables the manifest-consistency test):

    pip install pytest pyyaml
    python -m pytest tests -v

The tests use a fake plugin context and a temp directory; they do not need Hermes installed
and never touch `~/.hermes`.
