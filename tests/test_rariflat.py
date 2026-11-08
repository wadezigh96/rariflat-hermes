"""Tests for the Rariflat plugin. No Hermes install needed: a fake ctx stands in for the host."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("rariflat_plugin", ROOT / "__init__.py")
rf = importlib.util.module_from_spec(_spec)
sys.modules["rariflat_plugin"] = rf
_spec.loader.exec_module(rf)

OK_JSON = '{"output": "3 files", "exit_code": 0, "error": null}'


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("RARIFLAT_GUARD", "RARIFLAT_DENY", "RARIFLAT_ALLOW", "RARIFLAT_CONSOLE", "RARIFLAT_DESKTOP_EVENTS"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def app(tmp_path):
    a = rf.Rariflat(tmp_path)
    a.bridge._probed = True  # never touch a real gateway in tests
    return a


def write_config(app, data):
    app.config.path.parent.mkdir(parents=True, exist_ok=True)
    app.config.path.write_text(json.dumps(data), encoding="utf-8")


# --- #2 lockout regression -----------------------------------------------------------


def test_default_config_never_blocks_even_after_many_calls(app):
    for i in range(80):
        assert app.before(tool_name="terminal", args={}) is None, f"blocked at call {i + 1}"
        app.after(tool_name="terminal", args={}, result=OK_JSON)
    assert app.before(tool_name="terminal", args={}) is None
    assert app.guard("terminal")["blocked"] is False


def test_failures_and_hostile_result_text_never_cause_blocking(app):
    hostile = "denied blocked refuse restrain error failed"
    for _ in range(100):
        app.after(tool_name="web_search", args={}, result=hostile)
    assert app.before(tool_name="web_search", args={}) is None
    assert app.guard("web_search")["blocked"] is False


# --- #1 block shape / guard parity ---------------------------------------------------


def test_block_directive_shape_when_enabled(app):
    write_config(app, {"guard": {"enabled": True, "deny": ["Terminal"]}})
    result = app.before(tool_name="terminal", args={})
    assert result["action"] == "block"
    assert isinstance(result["message"], str) and result["message"].strip()
    assert set(result) == {"action", "message"}
    assert app.before(tool_name="read_file", args={}) is None


def test_guard_tool_reports_exactly_what_the_hook_does(app):
    write_config(app, {"guard": {"enabled": True, "deny": ["terminal"]}})
    for tool in ("terminal", "read_file"):
        hook_blocks = app.before(tool_name=tool, args={}) is not None
        assert app.guard(tool)["blocked"] is hook_blocks


def test_allow_list_and_env_override(app, monkeypatch):
    write_config(app, {"guard": {"enabled": True, "allow": ["read_file"]}})
    assert app.before(tool_name="terminal") is not None
    assert app.before(tool_name="read_file") is None
    monkeypatch.setenv("RARIFLAT_GUARD", "0")
    assert app.before(tool_name="terminal") is None


def test_guard_disabled_ignores_deny_list(app):
    write_config(app, {"guard": {"enabled": False, "deny": ["terminal"]}})
    assert app.before(tool_name="terminal") is None


def test_own_tools_never_blocked_or_scored(app):
    write_config(app, {"guard": {"enabled": True, "deny": ["rariflat_route"], "allow": []}})
    assert app.before(tool_name="rariflat_route") is None
    assert app.guard("rariflat_guard")["blocked"] is False
    app.after(tool_name="rariflat_route", args={}, result=OK_JSON)
    app.after(tool_name="rariflat_status", args={}, result="Error: x")
    assert app.store.data == {}


def test_block_message_echo_is_not_scored(app):
    app.after(tool_name="terminal", args={}, result=rf.block_message("terminal", "tool is on the deny list"))
    assert app.store.data == {}


def test_empty_result_is_not_scored(app):
    app.after(tool_name="terminal", args={}, result=None)
    app.after(tool_name="web_search", args={}, result="   ")
    assert app.store.data == {}


def test_hooks_fail_open(app, monkeypatch):
    def boom():
        raise RuntimeError("config exploded")
    monkeypatch.setattr(app.config, "snapshot", boom)
    assert app.before(tool_name="terminal") is None
    app.after(tool_name="terminal", result=OK_JSON)  # must not raise


# --- #3 routing uses the task --------------------------------------------------------


def _seed(app):
    for tool in ("web_search", "read_file", "terminal"):
        for _ in range(3):
            app.after(tool_name=tool, args={}, result=OK_JSON)


def test_route_depends_on_task(app):
    _seed(app)
    assert app.route("search the web for news")["best"] == "web_search"
    assert app.route("write a file to disk")["best"] == "read_file"
    assert app.route("run a shell command")["best"] == "terminal"


def test_route_admits_when_nothing_matches(app):
    _seed(app)
    out = app.route("compose a symphony")
    assert out["best"] is None and out["recommended"] == []
    assert "No tool seen" in out["message"]


def test_route_empty_task_and_empty_history(app):
    assert app.route("")["best"] is None
    assert app.route("search the web")["best"] is None


def test_route_prefers_more_reliable_tool_on_tie(app):
    for _ in range(5):
        app.after(tool_name="web_search", result=OK_JSON)
        app.after(tool_name="browser_search", result="Error: boom")
    assert app.route("search")["best"] == "web_search"


# --- #4 success detection -------------------------------------------------------------


@pytest.mark.parametrize("result,expected", [
    ("", True),                                           # mkdir / touch: no output is fine
    (None, True),
    ("def handle_error(): ...", True),                    # file that merely mentions 'error'
    ("Reading config.py\n    except Error:\n", True),
    (OK_JSON, True),
    ('{"results": [{"title": "error budgets"}]}', True),
    ("bash: foo: command not found", False),
    ("Exit code 1: No such file or directory", False),
    ("Error: boom", False),
    ("Traceback (most recent call last):\n  File x", False),
    ('{"output": "", "exit_code": 2}', False),
    ('{"error": "timeout"}', False),
    ('{"success": false}', False),
    ({"returncode": 1}, False),
    ({"returncode": 0, "error": None}, True),
])
def test_classify(result, expected):
    assert rf.classify(result) is expected


def test_classify_uses_structured_hook_kwargs():
    assert rf.classify("looks fine", error_type="timeout") is False
    assert rf.classify("looks fine", status="error") is False
    assert rf.classify("looks fine", status="ok") is True


# --- #7 tool-name matching ------------------------------------------------------------


@pytest.mark.parametrize("name,key", [
    ("web_search", "web"), ("read_file", "file"), ("terminal", "terminal"),
    ("profile", "default"), ("get_error_logs", "default"), ("mcp.github.search-issues", "search"),
    ("", "default"), (None, "default"),
])
def test_character_key_uses_whole_tokens(name, key):
    assert rf.character_key(name) == key


# --- #5 persistence -------------------------------------------------------------------


def test_flush_writes_valid_json_atomically(app):
    for _ in range(3):
        app.after(tool_name="terminal", result=OK_JSON)
    assert app.store.flush() is True
    assert json.loads(app.store.file.read_text()) == {"terminal": {"uses": 3, "successes": 3}}
    assert [p.name for p in app.store.dir.iterdir() if p.name.startswith(".scores-")] == []


def test_periodic_flush_after_enough_calls(app):
    for _ in range(rf.FLUSH_EVERY):
        app.after(tool_name="terminal", result=OK_JSON)
    assert app.store.file.exists()


def test_corrupt_file_is_quarantined_not_wiped(tmp_path):
    (tmp_path / "scores.json").write_text("{not json", encoding="utf-8")
    store = rf.Store(tmp_path)
    assert store.data == {}
    assert not (tmp_path / "scores.json").exists()
    quarantined = list(tmp_path.glob("scores.json.corrupt-*"))
    assert len(quarantined) == 1 and quarantined[0].read_text() == "{not json"
    store.record("terminal", True)
    assert store.flush() is True


def test_legacy_scores_are_migrated(tmp_path):
    legacy = {"terminal": {"rarity": 90, "restraint": 10, "uses": 5, "successes": 4}, "junk": 7}
    (tmp_path / "scores.json").write_text(json.dumps(legacy), encoding="utf-8")
    store = rf.Store(tmp_path)
    assert store.data == {"terminal": {"uses": 5, "successes": 4}}


def test_two_processes_add_up_instead_of_overwriting(tmp_path):
    a, b = rf.Store(tmp_path), rf.Store(tmp_path)
    for _ in range(3):
        a.record("terminal", True)
    for _ in range(2):
        b.record("terminal", False)
    assert a.flush() and b.flush()
    assert json.loads((tmp_path / "scores.json").read_text()) == {"terminal": {"uses": 5, "successes": 3}}


def test_unwritable_dir_does_not_raise(tmp_path):
    blocker = tmp_path / "file-not-dir"
    blocker.write_text("x")
    store = rf.Store(blocker / "sub")
    store.record("terminal", True)
    assert store.flush() is False
    assert store.data["terminal"]["uses"] == 1  # still usable in memory


# --- #6 desktop events ----------------------------------------------------------------


def test_events_are_json_safe_and_can_be_disabled(app, monkeypatch):
    sent = []
    app.bridge._fn = lambda plugin_id, event, payload: sent.append((plugin_id, event, payload))
    app.before(tool_name="web_search")
    app.after(tool_name="web_search", result=OK_JSON)
    assert [(p, e, pl["phase"]) for p, e, pl in sent] == [("rariflat", "tool", "start"), ("rariflat", "tool", "end")]
    json.dumps([pl for _, _, pl in sent])
    sent.clear()
    monkeypatch.setenv("RARIFLAT_DESKTOP_EVENTS", "0")
    app.before(tool_name="web_search")
    assert sent == []


def test_bridge_failure_never_propagates(app):
    def broken(*a, **k):
        raise RuntimeError("socket gone")
    app.bridge._fn = broken
    assert app.before(tool_name="terminal") is None
    app.after(tool_name="terminal", result=OK_JSON)


def test_blocked_call_emits_cerberus(app):
    sent = []
    app.bridge._fn = lambda p, e, payload: sent.append(payload)
    write_config(app, {"guard": {"enabled": True, "deny": ["terminal"]}})
    app.before(tool_name="terminal")
    assert sent[-1]["phase"] == "blocked" and sent[-1]["character"] == "Cerberus"


# --- registration and manifests -------------------------------------------------------


class FakeCtx:
    def __init__(self):
        self.tools, self.hooks, self.commands, self.unload = {}, {}, {}, []

    def register_tool(self, name, toolset, schema, handler, **kw):
        self.tools[name] = (schema, handler)

    def register_hook(self, name, fn, **kw):
        self.hooks[name] = fn

    def register_command(self, name, handler, description="", **kw):
        self.commands[name] = handler

    def on_unload(self, cb):
        self.unload.append(cb)


@pytest.fixture
def registered(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    ctx = FakeCtx()
    rf.register(ctx)
    return ctx


def test_register_wires_everything(registered):
    ctx = registered
    assert set(ctx.tools) == {"rariflat_route", "rariflat_status", "rariflat_guard"}
    assert set(ctx.hooks) == {"pre_tool_call", "post_tool_call"}
    assert "rariflat" in ctx.commands and ctx.unload
    for name, (schema, handler) in ctx.tools.items():
        assert schema["name"] == name
        assert isinstance(json.loads(handler(None)), dict)            # args=None must not crash
        assert isinstance(json.loads(handler("not a dict")), dict)
    assert "Rariflat" in ctx.commands["rariflat"]("")


def test_route_tool_handler_end_to_end(registered):
    ctx = registered
    ctx.hooks["post_tool_call"](tool_name="web_search", args={}, result=OK_JSON)
    out = json.loads(ctx.tools["rariflat_route"][1]({"task": "search the web"}))
    assert out["best"] == "web_search"


def _load_yaml(path):
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_manifest_matches_code_and_catalog(registered):
    manifest = _load_yaml(ROOT / "plugin.yaml")
    catalog = _load_yaml(ROOT / "plugin-catalog" / "rariflat.yaml")
    assert set(manifest["provides_tools"]) == set(registered.tools)
    assert set(manifest["provides_hooks"]) == set(registered.hooks)
    assert manifest["version"] == rf.__version__ == catalog["version"]
    assert set(catalog["capabilities"]["provides_tools"]) == set(manifest["provides_tools"])
    assert set(catalog["capabilities"]["provides_hooks"]) == set(manifest["provides_hooks"])
    assert manifest["name"] == catalog["name"] == "rariflat"
