# Tests

Run from the repo root (no Hermes install required):

```bash
pip install pytest
python -m pytest -q tests
```

Tests cover: lockout regression, block return shape, route uses task, success detection cases, atomic write / corrupt recovery, own tools never scored, args None handling.
