import pytest

from agent_ranking import AgentRegistry, _tier


def test_tiers_require_five_real_completions():
    assert _tier(100, 0) == "UNRANKED"
    assert _tier(100, 4) == "UNRANKED"
    assert _tier(90, 5) == "MYTHIC"
    assert _tier(80, 5) == "LEGEND"
    assert _tier(70, 5) == "EPIC"
    assert _tier(69.99, 5) == "DEVELOPING"


def test_registration_is_not_performance_evidence(tmp_path):
    registry = AgentRegistry(tmp_path)
    item = registry.register(
        "agent-a", "Researcher", "a2a", ["research", "web search"],
        "https://example.org/.well-known/agent-card.json",
        endpoint="https://example.org",
    )
    assert item["observations"] == 0
    assert item["tier"] == "UNRANKED"
    assert item["success_rate"] == 0
    assert item["status"] == "source_unverified_not_connected"


def test_completion_updates_live_observed_rates_and_average_duration(tmp_path):
    registry = AgentRegistry(tmp_path)
    registry.register(
        "agent-a", "Researcher", "a2a", ["research", "web", "search"],
        "https://example.org/agent-card.json", endpoint="https://example.org",
    )
    for i in range(5):
        item = registry.record("agent-a", "research web search", i != 0,
                               quality=90 if i else 50, duration_seconds=10 + i)
    assert item["observations"] == 5
    assert item["success_rate"] == 80
    assert item["average_quality"] == 82
    assert item["average_duration_seconds"] == 12
    assert item["tier"] == "LEGEND"
    assert item["evidence"] == "observed_completions"


def test_rank_prioritizes_capability_fit_but_discloses_low_history(tmp_path):
    registry = AgentRegistry(tmp_path)
    registry.register("researcher", "Researcher", "a2a", ["research", "web", "search"],
                      "https://a.example/card", endpoint="https://a.example")
    registry.register("coder", "Coder", "hermes", ["python", "coding", "terminal"],
                      "https://github.com/example/coder", install_ref="example/coder")
    rows = registry.rank("research web search")
    assert rows[0]["id"] == "researcher"
    assert rows[0]["tier"] == "UNRANKED"
    assert rows[0]["evidence"] == "insufficient_observations"
    assert rows[0]["requested_task_fit"] == 100


def test_rejects_non_https_a2a_and_hermes_without_install_reference(tmp_path):
    registry = AgentRegistry(tmp_path)
    with pytest.raises(ValueError):
        registry.register("agent-a", "Bad", "a2a", ["research"], "source", endpoint="http://example.org")
    with pytest.raises(ValueError):
        registry.register("agent-b", "Bad", "hermes", ["coding"], "source")


def test_persists_agent_records_without_running_install_or_agent(tmp_path):
    registry = AgentRegistry(tmp_path)
    registry.register("agent-a", "Researcher", "a2a", ["research"],
                      "https://example.org/card", endpoint="https://example.org")
    registry.record("agent-a", "research", True)
    reloaded = AgentRegistry(tmp_path)
    assert reloaded.summary("agent-a")["observations"] == 1
    assert reloaded.summary("agent-a")["status"] == "source_unverified_not_connected"


def test_corrupt_registry_is_not_overwritten(tmp_path):
    path = tmp_path / "agents.json"
    path.write_text("{broken", encoding="utf-8")
    registry = AgentRegistry(tmp_path)
    assert registry.rank() == []
    with pytest.raises(RuntimeError):
        registry.register("agent-a", "Researcher", "a2a", ["research"],
                          "https://example.org/card", endpoint="https://example.org")
    assert path.read_text(encoding="utf-8") == "{broken"


def test_task_ranking_and_historical_performance_are_separate(tmp_path):
    registry = AgentRegistry(tmp_path)
    registry.register("a", "A", "a2a", ["research", "web", "search"],
                      "https://a.example/card", endpoint="https://a.example")
    for i in range(5):
        registry.record("a", "research web search", True, quality=95, duration_seconds=20)
    row = registry.rank("research web search")[0]
    assert row["performance_score"] == 99
    assert row["requested_task_fit"] == 100
    assert row["tier"] == "MYTHIC"


def test_runtime_role_is_distinguished_from_installable_plugin(tmp_path):
    registry = AgentRegistry(tmp_path)
    agent_id = registry.register_runtime("researcher")
    item = registry.summary(agent_id)
    assert item["kind"] == "hermes"
    assert item["status"] == "runtime_observed"
    assert item["source_verified"] is False
    assert item["install_ref"] == "runtime:subagent"
