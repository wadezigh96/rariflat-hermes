import json
import time


def call(ctx, tool, args=None, result="ok"):
    pre = ctx.hooks["pre_tool_call"](tool, args or {})
    if pre is None:
        ctx.hooks["post_tool_call"](tool, args or {}, result)
    return pre


def test_judge_result_cases(rf):
    # empty / None success
    assert rf.judge_result(None) is True
    assert rf.judge_result("") is True
    # plain text containing "error"/"fail" but not at start is success
    assert rf.judge_result("Found 3 results about error handling in Python") is True
    assert rf.judge_result("handle_error function is fine") is True
    # starts with failure phrase
    assert rf.judge_result("Error: file not found") is False
    assert rf.judge_result("command not found: foo") is False
    assert rf.judge_result("No such file or directory") is False
    # structured
    assert rf.judge_result({"error": "boom"}) is False
    assert rf.judge_result(json.dumps({"success": False})) is False
    assert rf.judge_result({"exit_code": 2}) is False
    assert rf.judge_result({"returncode": 1}) is False
    assert rf.judge_result({"success": True, "output": "ok"}) is True


def test_character_matching_by_token(rf):
    assert rf._get_character("web_search")["name"] == "Owl"
    assert rf._get_character("read_file")["name"] == "Archivist"
    assert rf._get_character("profile_lookup")["name"] == "Hermes"  # 'file' inside 'profile' must not match
    assert rf._get_character("execute_code")["name"] == "Hephaestus"


def test_frequent_tool_never_blocked_default(rf, ctx):
    """Regression: 50+ normal calls must never block with default config (guard off)."""
    for i in range(60):
        assert call(ctx, "terminal", {"cmd": f"echo {i}"}) is None


def test_block_return_shape_when_enabled(rf, ctx, monkeypatch):
    rf._get_store().set_guard(True)
    monkeypatch.setenv("RARIFLAT_FAIL_STREAK", "2")
    for _ in range(2):
        call(ctx, "web_search", {"q": "x"}, result="Error: timeout")
    blocked = ctx.hooks["pre_tool_call"]("web_search", {"q": "z"})
    assert blocked is not None
    assert blocked.get("action") == "block"
    assert isinstance(blocked.get("message"), str) and len(blocked["message"]) > 0


def test_guard_off_by_default_only_warns(rf, ctx):
    for _ in range(5):
        call(ctx, "web_search", {"q": "x"}, result="Error: timeout")
    assert call(ctx, "web_search", {"q": "y"}) is None


def test_never_blocks_own_tools(rf, ctx):
    rf._get_store().set_guard(True)
    for _ in range(10):
        assert ctx.hooks["pre_tool_call"]("rariflat_route", {"task": "x"}) is None
        assert ctx.hooks["pre_tool_call"]("rariflat_guard", {"tool": "x"}) is None


def test_route_uses_task(rf, ctx):
    for _ in range(4):
        call(ctx, "web_search", {"query": "python asyncio tutorial"})
        call(ctx, "terminal", {"cmd": "git status"})
    out = json.loads(ctx.tools["rariflat_route"]({"task": "find an asyncio tutorial"}))
    assert out["best"] == "web_search"
    out2 = json.loads(ctx.tools["rariflat_route"]({"task": "check git status"}))
    assert out2["best"] == "terminal"
    # different tasks produce different results
    assert out["best"] != out2["best"]


def test_route_empty_history(rf, ctx):
    out = json.loads(ctx.tools["rariflat_route"]({"task": "anything"}))
    assert out["best"] is None and out["recommended"] == []


def test_atomic_write_and_corrupt_recovery(rf, tmp_path):
    s = rf.Store(tmp_path)
    s.record_result("terminal", {}, True, time.time())
    s.save(force=True)
    assert (tmp_path / "scores.json").exists()
    # corrupt it
    (tmp_path / "scores.json").write_text("{not json")
    s2 = rf.Store(tmp_path)
    assert s2.tools == {}
    # original renamed
    assert any(p.name.startswith("scores.json.corrupt-") for p in tmp_path.iterdir())


def test_own_tools_never_scored(rf, ctx):
    call(ctx, "rariflat_route", {"task": "x"}, result="ok")
    assert "rariflat_route" not in rf._get_store().tools or rf._get_store().tools["rariflat_route"].get("uses", 0) == 0


def test_args_none_or_non_dict(rf, ctx):
    assert call(ctx, "terminal", None) is None
    assert call(ctx, "terminal", "not-a-dict") is None


def test_commands(rf, ctx):
    call(ctx, "terminal", {"cmd": "ls"})
    cmd = ctx.commands["rariflat"]
    assert "terminal" in cmd("")
    assert "ON" in cmd("guard on") and "OFF" in cmd("guard off")
    assert "cleared" in cmd("reset")
