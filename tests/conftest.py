import importlib.util
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def rf(tmp_path, monkeypatch):
    monkeypatch.setenv("RARIFLAT_DATA_DIR", str(tmp_path))
    for k in ("RARIFLAT_GUARD", "RARIFLAT_LEARN_ARGS", "RARIFLAT_FAIL_STREAK", "RARIFLAT_COOLDOWN", "RARIFLAT_LOOP_REPEAT", "RARIFLAT_LOOP_WINDOW"):
        monkeypatch.delenv(k, raising=False)
    spec = importlib.util.spec_from_file_location("rariflat_plugin", ROOT / "__init__.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._reset_for_tests(tmp_path)
    return mod


class FakeCtx:
    def __init__(self):
        self.tools, self.hooks, self.commands, self.events = {}, {}, {}, []

    def register_tool(self, name, toolset, schema, handler):
        self.tools[name] = handler

    def register_hook(self, name, fn):
        self.hooks[name] = fn

    def register_command(self, name, handler, description=""):
        self.commands[name] = handler


@pytest.fixture
def ctx(rf):
    c = FakeCtx()
    rf.register(c)
    return c
