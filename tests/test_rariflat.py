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


def test_tokens_never_learn_credential_fields(rf):
    tokens = rf._tokens({
        "query": "python asyncio",
        "api_key": "sk-live-supersecret",
        "nested": {
            "Authorization": "Bearer topsecret",
            "clientSecret": "hidden-secret",
            "safe": "documentation",
        },
        "header": "Bearer inline-secret",
        "note": "password=hunter2",
    })
    joined = " ".join(tokens).lower()
    for secret in ("sk-live-supersecret", "topsecret", "hidden-secret", "inline-secret", "hunter2"):
        assert secret not in joined
    assert "python" in tokens and "asyncio" in tokens and "documentation" in tokens


def test_http_status_codes_use_http_semantics(rf):
    assert rf.judge_result({"status_code": 200}) is True
    assert rf.judge_result({"status_code": 204}) is True
    assert rf.judge_result({"status_code": 302}) is True
    assert rf.judge_result({"status_code": 400}) is False
    assert rf.judge_result({"status_code": 503}) is False
    assert rf.judge_result({"status_code": 0}) is False
    assert rf.judge_result({"exit_code": 1, "status_code": 200}) is False


def test_loop_cache_prunes_expired_signatures_and_is_bounded(rf, monkeypatch):
    store = rf.Store()
    monkeypatch.setenv("RARIFLAT_LOOP_REPEAT", "3")
    monkeypatch.setenv("RARIFLAT_LOOP_WINDOW", "10")
    for i in range(1100):
        store.loop_detected("browser", {"url": f"https://example.com/{i}"}, now=100.0)
    assert len(store._recent_calls) <= 1024
    store.loop_detected("browser", {"url": "https://new.example/"}, now=200.0)
    assert len(store._recent_calls) == 1

def test_rarity_changes_ranking(rf):
    common = {"tokens": ["python", "asyncio"], "uses": 100, "successes": 90, "repeated_calls": 0}
    rare = {"tokens": ["python", "asyncio"], "uses": 1, "successes": 1, "repeated_calls": 0}
    ranked = rf._rank_tools("python asyncio", {"common_tool": common, "rare_tool": rare})
    assert ranked[0]["skill"] == "rare_tool"
    assert ranked[0]["rarity"] > ranked[1]["rarity"]


def test_restraint_changes_ranking(rf):
    restrained = {"tokens": ["python", "asyncio"], "uses": 10, "successes": 10, "repeated_calls": 0}
    repetitive = {"tokens": ["python", "asyncio"], "uses": 10, "successes": 10, "repeated_calls": 8}
    ranked = rf._rank_tools("python asyncio", {"restrained_tool": restrained, "repetitive_tool": repetitive})
    assert ranked[0]["skill"] == "restrained_tool"
    assert ranked[0]["restraint"] > ranked[1]["restraint"]


def test_repeated_call_metric_is_learned(rf, tmp_path):
    store = rf.Store(tmp_path)
    store.record_result("browser", {"url": "https://example.com"}, True, timestamp=100)
    store.record_result("browser", {"url": "https://example.com"}, True, timestamp=110)
    assert store.tools["browser"]["repeated_calls"] == 1
    store.record_result("browser", {"url": "https://different.example"}, True, timestamp=115)
    assert store.tools["browser"]["repeated_calls"] == 1


def test_route_explains_all_ranking_factors_and_router_scope(rf, ctx):
    call(ctx, "web_search", {"query": "python asyncio tutorial"})
    out = json.loads(ctx.tools["rariflat_route"]({"task": "python asyncio tutorial"}))
    assert out["router_type"] == "tool_skill_recommender"
    assert out["dispatches_to_agent"] is False
    item = out["recommended"][0]
    assert {"rarity", "restraint", "reliability", "reason", "factors"} <= item.keys()
    assert all(key in item["reason"] for key in ("rarity", "restraint", "reliability"))


def test_repeated_call_fingerprint_excludes_credentials(rf, tmp_path):
    store = rf.Store(tmp_path)
    store.record_result("api_call", {"query": "weather", "api_key": "first-secret"}, True, timestamp=100)
    first = store.tools["api_call"]["last_args_fingerprint"]
    store.record_result("api_call", {"query": "weather", "api_key": "second-secret"}, True, timestamp=110)
    assert store.tools["api_call"]["last_args_fingerprint"] == first
    assert store.tools["api_call"]["repeated_calls"] == 1
