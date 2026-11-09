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


def test_zero_cooldown_recovers_immediately(rf, ctx, monkeypatch):
    rf._get_store().set_guard(True)
    monkeypatch.setenv("RARIFLAT_FAIL_STREAK", "2")
    monkeypatch.setenv("RARIFLAT_COOLDOWN", "0")
    for _ in range(2):
        call(ctx, "terminal", {}, result="Error: unavailable")
    assert rf._get_store().tools["terminal"]["fail_streak"] == 2
    assert ctx.hooks["pre_tool_call"]("terminal", {}) is None
    assert rf._get_store().tools["terminal"]["fail_streak"] == 0


def test_guard_preference_survives_store_reload(rf, tmp_path):
    store = rf._get_store()
    store.set_guard(True)
    assert rf.Store(tmp_path).guard_enabled is True
    store.set_guard(False)
    assert rf.Store(tmp_path).guard_enabled is False


def test_guard_environment_setting_overrides_persisted_preference(rf, tmp_path, monkeypatch):
    rf.Store(tmp_path).set_guard(False)
    monkeypatch.setenv("RARIFLAT_GUARD", "1")
    assert rf.Store(tmp_path).guard_enabled is True


def test_loop_detector_opt_in(rf, ctx, monkeypatch):
    rf._get_store().set_guard(True)
    monkeypatch.setenv("RARIFLAT_LOOP_REPEAT", "3")
    monkeypatch.setenv("RARIFLAT_LOOP_WINDOW", "30")
    assert ctx.hooks["pre_tool_call"]("browser", {"url": "https://example.com"}) is None
    assert ctx.hooks["pre_tool_call"]("browser", {"url": "https://example.com"}) is None
    assert ctx.hooks["pre_tool_call"]("browser", {"url": "https://example.com"})["action"] == "block"


def test_loop_detector_normalizes_secrets(rf, monkeypatch):
    """Loop signatures must use the same safe fingerprint as ranking so rotating secrets do not create unique keys."""
    store = rf._get_store()
    store.set_guard(True)
    monkeypatch.setenv("RARIFLAT_LOOP_REPEAT", "3")
    monkeypatch.setenv("RARIFLAT_LOOP_WINDOW", "30")
    base = {"query": "search docs", "api_key": "sk-secret-1"}
    rotated = {"query": "search docs", "api_key": "sk-secret-2"}
    # Same safe fingerprint after redaction, so they count as the same call.
    assert store.loop_detected("web_search", base, now=1000.0) is False
    assert store.loop_detected("web_search", rotated, now=1001.0) is False
    assert store.loop_detected("web_search", {"query": "search docs", "api_key": "sk-secret-3"}, now=1002.0) is True


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


def test_argument_learning_can_be_disabled(rf, tmp_path, monkeypatch):
    monkeypatch.setenv("RARIFLAT_LEARN_ARGS", "0")
    store = rf.Store(tmp_path)
    store.record_result("web_search", {"query": "private project docs"}, True)
    assert store.tools["web_search"]["tokens"] == []
    assert store.tools["web_search"]["last_args_fingerprint"]


def test_failure_event_does_not_expose_raw_tool_output(rf, ctx, monkeypatch):
    emitted = []
    monkeypatch.setattr(rf, "_emit", lambda *args: emitted.append(args))
    ctx.hooks["post_tool_call"](
        "terminal", {}, "Error: Authorization: Bearer super-secret-value"
    )
    event = emitted[-1]
    assert event[0:3] == ("done", "terminal", False)
    assert "super-secret-value" not in event[3]
    assert "Authorization" not in event[3]


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

def test_rarity_changes_ranking(rf, monkeypatch):
    common = {
        "tokens": ["python", "asyncio"],
        "uses": 100,
        "successes": 100,
        "repeated_calls": 0,
    }
    rare = {
        "tokens": ["python", "asyncio"],
        "uses": 1,
        "successes": 1,
        "repeated_calls": 0,
    }
    tools = {"common_tool": common, "rare_tool": rare}

    # Hold restraint constant so rarity is the only differing score factor.
    monkeypatch.setattr(
        rf,
        "_recent_usage_metrics",
        lambda data: {"recent_uses": 0, "repeated_calls_30s": 0},
    )

    ranked_with_rarity = rf._rank_tools("python asyncio", tools)
    assert ranked_with_rarity[0]["skill"] == "rare_tool"

    common_row = next(row for row in ranked_with_rarity if row["skill"] == "common_tool")
    rare_row = next(row for row in ranked_with_rarity if row["skill"] == "rare_tool")
    for factor in ("task_fit", "reliability", "restraint"):
        assert common_row["factors"][factor] == rare_row["factors"][factor]

    # Flatten rarity for this comparison: without its contribution,
    # the usage-count tie-breaker should put common_tool first.
    class FlatMath:
        @staticmethod
        def log2(value):
            return 0

    monkeypatch.setattr(rf, "math", FlatMath)
    ranked_without_rarity = rf._rank_tools("python asyncio", tools)
    assert ranked_without_rarity[0]["skill"] == "common_tool"


def test_restraint_changes_ranking(rf):
    now = time.time()
    restrained = {
        "tokens": ["python", "asyncio"], "uses": 10, "successes": 10,
        "recent_events": [
            {"timestamp": now - 9 + i, "fingerprint": f"unique-{i}"}
            for i in range(10)
        ],
    }
    repetitive = {
        "tokens": ["python", "asyncio"], "uses": 10, "successes": 10,
        "recent_events": [
            {"timestamp": now - 9 + i, "fingerprint": "same-call" if i < 9 else "other-call"}
            for i in range(10)
        ],
    }
    ranked = rf._rank_tools("python asyncio", {"restrained_tool": restrained, "repetitive_tool": repetitive})
    assert ranked[0]["skill"] == "restrained_tool"
    assert ranked[0]["restraint"] == 100.0
    assert ranked[1]["restraint"] == 20.0


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


def test_route_emits_privacy_safe_desktop_decision_event(rf, ctx, monkeypatch):
    import sys
    from types import ModuleType

    emitted = []
    hermes_cli = ModuleType("hermes_cli")
    hermes_cli.__path__ = []
    events = ModuleType("hermes_cli.plugin_events")
    events.broadcast_plugin_event = lambda *args: emitted.append(args)
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.plugin_events", events)

    call(ctx, "web_search", {"query": "public plugin docs"})
    private_task = "customer-project-codeword-91"
    result = json.loads(ctx.tools["rariflat_route"]({"task": f"research {private_task}"}))
    route_events = [event for event in emitted if len(event) == 3 and event[1] == "route"]

    assert len(route_events) == 1
    plugin, event_type, payload = route_events[0]
    assert (plugin, event_type) == ("rariflat", "route")
    assert set(payload) == {"recommended", "weights", "minimum_observations"}
    assert payload["minimum_observations"] == 5
    assert payload["weights"] == {"task_fit": 40, "reliability": 25, "rarity": 20, "restraint": 15}
    assert len(payload["recommended"]) == 1
    item = payload["recommended"][0]
    assert item["skill"] == result["best"] == "web_search"
    assert item["uses"] == 1 and item["successes"] == 1 and item["failures"] == 0
    assert item["counts_capped"] is False
    assert set(item["factors"]) == {"task_fit", "reliability", "rarity", "restraint"}
    serialized = json.dumps(payload)
    assert private_task not in serialized
    assert "reason" not in payload and "task" not in payload and "args" not in payload
    assert set(item) == {"skill", "score", "uses", "successes", "failures", "counts_capped", "factors"}


def test_route_event_payload_caps_counts_consistently_and_limits_rows(rf):
    row = {
        "skill": "web_search",
        "score": 80,
        "uses": 1_500_000,
        "successes": 900_000,
        "failures": 600_000,
        "factors": {"task_fit": 80, "reliability": 60, "rarity": 20, "restraint": 100},
        "reason": "must not be sent to Desktop",
    }
    payload = rf._route_event_payload([row | {"skill": f"tool_{index}"} for index in range(4)])

    assert len(payload["recommended"]) == 3
    item = payload["recommended"][0]
    assert item["uses"] == 1_000_000
    assert item["successes"] == 900_000
    assert item["failures"] == 100_000
    assert item["successes"] + item["failures"] == item["uses"]
    assert item["counts_capped"] is True
    assert "reason" not in item


def test_repeated_call_fingerprint_excludes_credentials(rf, tmp_path):
    store = rf.Store(tmp_path)
    store.record_result("api_call", {"query": "weather", "api_key": "first-secret"}, True, timestamp=100)
    first = store.tools["api_call"]["last_args_fingerprint"]
    store.record_result("api_call", {"query": "weather", "api_key": "second-secret"}, True, timestamp=110)
    assert store.tools["api_call"]["last_args_fingerprint"] == first
    assert store.tools["api_call"]["repeated_calls"] == 1

def test_tokens_split_compound_tool_names_and_normalize_documentation(rf):
    tokens = rf._tokens("tool_search webSearch documentation")
    assert {"tool", "search", "web", "documentation"} <= tokens
    assert "search" in tokens


def test_natural_language_documentation_task_has_nonzero_task_fit(rf, ctx):
    # The tool's observed arguments contain searchable capability terms.
    call(ctx, "web_search", {"query": "public documentation Hermes plugins"})
    out = json.loads(ctx.tools["rariflat_route"]({
        "task": "find and summarize public documentation about Hermes plugins"
    }))
    assert out["recommended"]
    assert any(item["task_match_score"] > 0 for item in out["recommended"])
    assert out["best"] == "web_search"




def test_recent_restraint_uses_rolling_window(rf, tmp_path, monkeypatch):
    store = rf.Store(tmp_path)
    args = {"query": "same"}
    store.record_result("web_search", args, True, timestamp=100)
    store.record_result("web_search", args, True, timestamp=105)
    store.record_result("web_search", args, True, timestamp=110)
    metrics = rf._recent_usage_metrics(store.tools["web_search"], now=111, window=30)
    assert metrics == {"recent_uses": 3, "repeated_calls_30s": 2}
    monkeypatch.setattr(rf.time, "time", lambda: 111)
    ranked = rf._rank_tools("query same", {"web_search": store.tools["web_search"]})
    assert ranked[0]["restraint"] == 33.33
    metrics = rf._recent_usage_metrics(store.tools["web_search"], now=141, window=30)
    assert metrics == {"recent_uses": 0, "repeated_calls_30s": 0}


def test_recent_restraint_ignores_different_args(rf, tmp_path):
    store = rf.Store(tmp_path)
    store.record_result("web_search", {"query": "one"}, True, timestamp=100)
    store.record_result("web_search", {"query": "two"}, True, timestamp=105)
    metrics = rf._recent_usage_metrics(store.tools["web_search"], now=106)
    assert metrics == {"recent_uses": 2, "repeated_calls_30s": 0}


def test_usage_timestamps_and_failures_are_persisted(rf, tmp_path):
    store = rf.Store(tmp_path)
    store.record_result("web_search", {"query": "ok"}, True, timestamp=100)
    store.record_result("web_search", {"query": "bad"}, False, timestamp=110)
    item = store.tools["web_search"]
    assert item["uses"] == 2
    assert item["successes"] == 1 and item["failures"] == 1
    assert item["first_used"] == 100 and item["last_used"] == 110
    assert item["last_success"] == 100 and item["last_failure"] == 110
    store.save(force=True)
    reloaded = rf.Store(tmp_path)
    assert reloaded.tools["web_search"]["last_used"] == 110


def test_runtime_session_count_and_timestamps_persist(rf, tmp_path):
    store = rf.Store(tmp_path)
    store.record_session_start(timestamp=100)
    store.record_session_start(timestamp=200)
    reloaded = rf.Store(tmp_path)
    assert reloaded.sessions_started == 2
    assert reloaded.first_session_at == 100
    assert reloaded.last_session_at == 200

 
def test_legacy_repeat_totals_do_not_masquerade_as_live_window(rf, tmp_path):
    path = tmp_path / "scores.json"
    path.write_text(json.dumps({"tools": {
        "legacy_tool": {"uses": 12, "successes": 10, "repeated_calls": 7, "tokens": ["legacy"]}
    }}), encoding="utf-8")
    store = rf.Store(tmp_path)
    item = store.tools["legacy_tool"]
    assert item["repeated_calls_total"] == 7
    assert item["repeated_calls"] == 0
    assert item["recent_events"] == []
    metrics = rf._recent_usage_metrics(item, now=500, window=30)
    assert metrics == {"recent_uses": 0, "repeated_calls_30s": 0}
    ranked = rf._rank_tools("legacy", store.tools)
    assert ranked[0]["restraint"] == 100.0


def test_status_activity_includes_more_than_ten_tools(rf, ctx):
    store = rf._get_store()
    for i in range(12):
        store.record_result(f"tool_{i}", {"arg": i}, True, timestamp=100 + i)
    status = json.loads(ctx.tools["rariflat_status"]({}))
    assert len(status["tools_activity"]) == 12
    assert {item["name"] for item in status["tools_activity"]} == {f"tool_{i}" for i in range(12)}
