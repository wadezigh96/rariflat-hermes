import json
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
    registry.register("agent-a", "A", "a2a", ["research", "web", "search"],
                      "https://a.example/card", endpoint="https://a.example")
    for i in range(5):
        registry.record("agent-a", "research web search", True, quality=95, duration_seconds=20)
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


def test_tier_order_is_mythic_then_legend_then_epic(tmp_path):
    registry = AgentRegistry(tmp_path)
    registry.register("mythic", "Mythic agent", "a2a", ["math"],
                      "https://m.example/card", endpoint="https://m.example")
    registry.register("legend", "Legend agent", "a2a", ["writing"],
                      "https://l.example/card", endpoint="https://l.example")
    for _ in range(5):
        registry.record("mythic", "math", True, quality=100)
        registry.record("legend", "writing", True, quality=0)
    rows = registry.rank("writing")
    assert rows[0]["tier"] == "MYTHIC"
    assert rows[1]["tier"] == "LEGEND"


def test_rejects_a2a_urls_with_query_tokens_or_fragments(tmp_path):
    registry = AgentRegistry(tmp_path)
    with pytest.raises(ValueError):
        registry.register("agent-a", "Bad", "a2a", ["research"],
                          "https://example.org/card?token=secret",
                          endpoint="https://example.org")
    with pytest.raises(ValueError):
        registry.register("agent-b", "Bad", "a2a", ["research"],
                          "https://example.org/card",
                          endpoint="https://example.org/agent#secret")


def test_rejects_a2a_urls_without_valid_hosts_or_with_empty_credentials(tmp_path):
    registry = AgentRegistry(tmp_path)
    invalid_urls = ["https://@", "https://:443", "https://user:@example.org", "https://example.org:bad"]
    for index, url in enumerate(invalid_urls):
        with pytest.raises(ValueError):
            registry.register(f"bad-{index}", "Bad", "a2a", ["research"],
                              "https://example.org/card", endpoint=url)
    with pytest.raises(ValueError):
        registry.register("bad-source", "Bad", "a2a", ["research"],
                          "https://@", endpoint="https://example.org")


def test_re_registration_with_new_identity_does_not_inherit_evidence(tmp_path):
    registry = AgentRegistry(tmp_path)
    registry.register("agent-a", "Researcher", "a2a", ["research"],
                      "https://a.example/card", endpoint="https://a.example")
    for _ in range(5):
        registry.record("agent-a", "research", True, quality=100)
    assert registry.summary("agent-a")["tier"] == "MYTHIC"

    same_agent = registry.register("agent-a", "Research lead", "a2a", ["research"],
                                    "https://a.example/card", endpoint="https://a.example")
    assert same_agent["observations"] == 5
    assert same_agent["tier"] == "MYTHIC"

    item = registry.register("agent-a", "Unrelated agent", "a2a", ["translation"],
                             "https://b.example/card", endpoint="https://b.example")

    assert item["observations"] == 0
    assert item["tier"] == "UNRANKED"
    assert item["evidence"] == "insufficient_observations"


def test_hermes_install_ref_is_repo_slug_not_arbitrary_command(tmp_path):
    registry = AgentRegistry(tmp_path)
    with pytest.raises(ValueError):
        registry.register("agent-bad", "Bad", "hermes", ["research"],
                          "https://github.com/acme/research-agent", install_ref="https://evil.example/install.sh")
    with pytest.raises(ValueError):
        registry.register("agent-cmd", "Bad", "hermes", ["research"],
                          "https://github.com/acme/research-agent", install_ref="curl|sh")
    item = registry.register("agent-good", "Good", "hermes", ["research"],
                             "https://github.com/acme/research-agent",
                             install_ref="acme/research-agent")
    assert item["install_ref"] == "acme/research-agent"


def test_registry_follows_profile_data_directory(tmp_path):
    active = {"dir": tmp_path / "profile-a"}
    registry = AgentRegistry(lambda: active["dir"])
    registry.register("agent-a", "Profile A", "a2a", ["research"],
                      "https://a.example/card", endpoint="https://a.example")
    active["dir"] = tmp_path / "profile-b"
    assert registry.rank() == []
    registry.register("agent-b", "Profile B", "a2a", ["coding"],
                      "https://b.example/card", endpoint="https://b.example")
    assert [row["id"] for row in registry.rank()] == ["agent-b"]
    assert (tmp_path / "profile-a" / "agents.json").exists()
    assert (tmp_path / "profile-b" / "agents.json").exists()


def test_rejects_hermes_source_with_query_or_mismatched_repository(tmp_path):
    registry = AgentRegistry(tmp_path)
    with pytest.raises(ValueError):
        registry.register("agent-a", "Bad", "hermes", ["research"],
                          "https://github.com/acme/repo?token=secret",
                          install_ref="acme/repo")
    with pytest.raises(ValueError):
        registry.register("agent-b", "Bad", "hermes", ["research"],
                          "https://github.com/other/repo",
                          install_ref="acme/repo")


def test_valid_json_with_invalid_registry_schema_fails_closed(tmp_path):
    path = tmp_path / "agents.json"
    path.write_text(json.dumps({"schema_version": 1, "agents": {
        "agent-a": {"id": "agent-a", "name": "Broken", "kind": "a2a",
                    "capabilities": ["research"], "source": "https://a.example/card",
                    "status": "source_unverified_not_connected",
                    "observations": [{"success": True}]}
    }}), encoding="utf-8")
    registry = AgentRegistry(tmp_path)
    assert registry.rank() == []
    with pytest.raises(RuntimeError):
        registry.register("agent-b", "Researcher", "a2a", ["research"],
                          "https://b.example/card", endpoint="https://b.example")
    assert path.exists()
