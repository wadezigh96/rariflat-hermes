import json
import time


def call(ctx, tool, args=None, result="ok"):
    pre = ctx.hooks["pre_tool_call"](tool, args or {})
    if pre is None:
        ctx.hooks["post_tool_call"](tool, args or {}, result)
    return pre


def test_judge_result_cases(rf):
    assert rf.judge_result(None) is True
    assert rf.judge_result("") is True
    assert rf.judge_result("Found 3 results about error handling in Python") is True
    assert rf.judge_result("handle_error function is fine") is True
    assert rf.judge_result("Error: file not found") is False
    assert rf.judge_result("command not found: foo") is False
    assert rf.judge_result("No such file or directory") is False
    assert rf.judge_result({"error": "boom"}) is False
    assert rf.judge_result(json.dumps({"success": False})) is False
    assert rf.judge_result({"exit_code": 2}) is False
    assert rf.judge_result({"returncode": 1}) is False
    assert rf.judge_result({"success": True, "output": "ok"}) is True


def test_character_matching_by_token(rf):
    assert rf._get_character("web_search")["name"] == "Owl"
    assert rf._get_character("read_file")["name"] == "Archivist"
    assert rf._get_character("profile_lookup")["name"] == "Hermes"
    assert rf._get_character("execute_code")["name"] == "Hephaestus"


def test_frequent_tool_never_blocked_default(rf, ctx):
    for i in range(60):
        assert call(ctx, "terminal", {"cmd": f"echo {i}"}) is None


def test_block_return_shape_when_enabled(rf, ctx, monkeypatch):
    rf._get_store().set_guard(True)
    monkeypatch.setenv("RARIFLAT_FAIL_STREAK", "2")
    for _ in range(2):
        call(ctx, "web_search", {"q": "x"}, result="Error: timeout")
    blocked = ctx.hooks["pre_tool_call"]("web_search", {"q": "z"})
    assert blocked["action"] == "block"
    assert isinstance(blocked["message"], str) and blocked["message"]


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
    web = json.loads(ctx.tools["rariflat_route"]({"task": "find an asyncio tutorial"}))
    terminal = json.loads(ctx.tools["rariflat_route"]({"task": "check git status"}))
    assert web["best"] == "web_search"
    assert terminal["best"] == "terminal"
    assert web["best"] != terminal["best"]


def test_route_empty_history(rf, ctx):
    out = json.loads(ctx.tools["rariflat_route"]({"task": "anything"}))
    assert out["best"] is None and out["recommended"] == []


def test_atomic_write_and_corrupt_recovery(rf, tmp_path):
    store = rf.Store(tmp_path)
    store.record_result("terminal", {}, True, time.time())
    store.save(force=True)
    assert (tmp_path / "scores.json").exists()
    (tmp_path / "scores.json").write_text("{not json")
    second = rf.Store(tmp_path)
    assert second.tools == {}
    assert any(p.name.startswith("scores.json.corrupt-") for p in tmp_path.iterdir())


def test_own_tools_never_scored(rf, ctx):
    call(ctx, "rariflat_route", {"task": "x"}, result="ok")
    assert "rariflat_route" not in rf._get_store().tools


def test_args_none_or_non_dict(rf, ctx):
    assert call(ctx, "terminal", None) is None
    assert call(ctx, "terminal", "not-a-dict") is None


def test_commands(rf, ctx):
    call(ctx, "terminal", {"cmd": "ls"})
    command = ctx.commands["rariflat"]
    assert "terminal" in command("")
    assert "ON" in command("guard on") and "OFF" in command("guard off")
    assert "cleared" in command("reset")


def test_guard_resets_after_success(rf, ctx, monkeypatch):
    rf._get_store().set_guard(True)
    monkeypatch.setenv("RARIFLAT_FAIL_STREAK", "2")
    monkeypatch.setenv("RARIFLAT_COOLDOWN", "3600")
    call(ctx, "terminal", {}, result="Error: first")
    call(ctx, "terminal", {}, result="Error: second")
    assert ctx.hooks["pre_tool_call"]("terminal", {})["action"] == "block"
    ctx.hooks["post_tool_call"]("terminal", {}, "ok")
    assert ctx.hooks["pre_tool_call"]("terminal", {}) is None


def test_loop_detector_opt_in(rf, ctx, monkeypatch):
    rf._get_store().set_guard(True)
    monkeypatch.setenv("RARIFLAT_LOOP_REPEAT", "3")
    monkeypatch.setenv("RARIFLAT_LOOP_WINDOW", "30")
    assert ctx.hooks["pre_tool_call"]("browser", {"url": "https://example.com"}) is None
    assert ctx.hooks["pre_tool_call"]("browser", {"url": "https://example.com"}) is None
    assert ctx.hooks["pre_tool_call"]("browser", {"url": "https://example.com"})["action"] == "block"


def test_event_emitter_is_optional(rf, ctx):
    assert ctx.hooks["pre_tool_call"]("browser", {}) is None


def test_status_is_json(rf, ctx):
    result = json.loads(ctx.tools["rariflat_status"]({}))
    assert result["guard_enabled"] is False
    assert result["tracked_tools"] == 0
