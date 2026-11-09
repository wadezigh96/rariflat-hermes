"""Evidence-based ranking for Hermes plugins and A2A agents.

Only explicitly recorded task completions affect performance rates. Agent cards and
manifests describe declared capabilities; they are not treated as proof of quality.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

TIERS = (("MYTHIC", 90.0), ("LEGEND", 80.0), ("EPIC", 70.0))
TIER_ORDER = {"MYTHIC": 5, "LEGEND": 4, "EPIC": 3, "DEVELOPING": 2, "UNRANKED": 1}
_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{1,79}$")


def _tokens(value):
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(x) for x in value)
    return set(_TOKEN_RE.findall(str(value or "").lower()))


def _tier(score, observations):
    if observations < 5:
        return "UNRANKED"
    for name, threshold in TIERS:
        if score >= threshold:
            return name
    return "DEVELOPING"


def _is_clean_https_url(value):
    try:
        parsed = urlparse(value)
        # Accessing .port also validates that any supplied port is numeric and in range.
        parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
    )


class AgentRegistry:
    """Small local registry; no network calls, installs, or agent execution."""

    def __init__(self, data_dir):
        self._data_dir_provider = data_dir if callable(data_dir) else None
        self.data_dir = Path(data_dir() if callable(data_dir) else data_dir).expanduser()
        self.path = self.data_dir / "agents.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.agents = {}
        self._load_error = False
        self._load()

    def _refresh_profile(self):
        """Follow Hermes' active profile data directory before every operation."""
        if self._data_dir_provider is None:
            return
        next_dir = Path(self._data_dir_provider()).expanduser()
        if next_dir == self.data_dir:
            return
        self.data_dir = next_dir
        self.path = next_dir / "agents.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.agents = {}
        self._load_error = False
        self._load()

    def _load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if (not isinstance(raw, dict) or raw.get("schema_version") != 1
                    or not isinstance(raw.get("agents"), dict)):
                raise ValueError("unsupported or invalid agent registry schema")
            required = {"id", "name", "kind", "capabilities", "source", "status", "observations"}
            validated = {}
            for key, agent in raw["agents"].items():
                if (not isinstance(key, str) or not isinstance(agent, dict)
                        or not required.issubset(agent) or agent.get("id") != key
                        or not isinstance(agent.get("name"), str)
                        or agent.get("kind") not in {"hermes", "a2a"}
                        or not isinstance(agent.get("capabilities"), list)
                        or not all(isinstance(x, str) for x in agent["capabilities"])
                        or not isinstance(agent.get("source"), str)
                        or not isinstance(agent.get("status"), str)
                        or not isinstance(agent.get("observations"), list)):
                    raise ValueError("invalid agent registry record")
                for event in agent["observations"]:
                    if (not isinstance(event, dict)
                            or not isinstance(event.get("success"), bool)
                            or not isinstance(event.get("timestamp"), (int, float))
                            or not isinstance(event.get("task_fit"), (int, float))):
                        raise ValueError("invalid agent observation")
                validated[key] = agent
            self.agents = validated
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError):
            # Fail closed: do not silently replace a malformed local registry.
            self._load_error = True
            self.agents = {}

    def _save(self):
        if self._load_error:
            raise RuntimeError("Agent registry data is unreadable; refusing to overwrite it")
        payload = json.dumps({"schema_version": 1, "agents": self.agents},
                             ensure_ascii=False, indent=2)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(payload + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def register(self, agent_id, name, kind, capabilities, source,
                 endpoint="", install_ref="", description=""):
        with self._lock:
            self._refresh_profile()
        agent_id = str(agent_id or "").strip()
        name = str(name or "").strip()[:100]
        kind = str(kind or "").lower().strip()
        source = str(source or "").strip()[:300]
        endpoint = str(endpoint or "").strip()
        install_ref = str(install_ref or "").strip()[:300]
        description = str(description or "").strip()[:500]
        caps = sorted({str(x).strip().lower()[:60] for x in
                       (capabilities if isinstance(capabilities, list) else [])
                       if str(x).strip()})[:40]
        if not _ID_RE.fullmatch(agent_id):
            raise ValueError("agent_id must be 2-80 safe characters")
        if not name or kind not in {"hermes", "a2a"} or not caps or not source:
            raise ValueError("name, kind (hermes/a2a), capabilities, and source are required")
        if kind == "a2a":
            if not _is_clean_https_url(endpoint):
                raise ValueError("A2A endpoint must be HTTPS and must not embed credentials, query tokens, or fragments")
            if not _is_clean_https_url(source):
                raise ValueError("A2A Agent Card source must be a clean HTTPS URL without embedded credentials or query tokens")
        elif install_ref == "runtime:subagent":
            if source != "Hermes subagent lifecycle hook (runtime-observed)":
                raise ValueError("runtime Hermes source must use the fixed lifecycle-hook descriptor")
        else:
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", install_ref):
                raise ValueError("Hermes install_ref must be a GitHub owner/repository slug; arbitrary URLs and shell commands are not accepted")
            if not _is_clean_https_url(source):
                raise ValueError("Hermes source must be a clean HTTPS GitHub repository URL")
            parsed = urlparse(source)
            parts = [part for part in parsed.path.split("/") if part]
            if parsed.hostname.lower() != "github.com" or len(parts) != 2:
                raise ValueError("Hermes source must point to https://github.com/<owner>/<repository>")
            if "/".join(parts) != install_ref:
                raise ValueError("Hermes source repository must match install_ref")
        with self._lock:
            if self._load_error:
                raise RuntimeError("Agent registry data is unreadable; refusing changes")
            previous = self.agents.get(agent_id, {})
            same_identity = (
                previous.get("kind") == kind
                and previous.get("source") == source
                and previous.get("endpoint", "") == endpoint
                and previous.get("install_ref", "") == install_ref
                and previous.get("capabilities") == caps
            )
            self.agents[agent_id] = {
                "id": agent_id, "name": name, "kind": kind,
                "capabilities": caps, "source": source, "endpoint": endpoint,
                "install_ref": install_ref, "description": description,
                "registered_at": previous.get("registered_at", time.time()) if same_identity else time.time(),
                "observations": previous.get("observations", []) if same_identity else [],
                "status": "source_unverified_not_installed" if kind == "hermes" else "source_unverified_not_connected",
            }
            self._save()
        return self.summary(agent_id)

    def register_runtime(self, role):
        with self._lock:
            self._refresh_profile()
        """Register a Hermes delegated role observed directly from runtime hooks."""
        role = str(role or "unassigned").strip()[:60] or "unassigned"
        safe_role = re.sub(r"[^a-zA-Z0-9._-]+", "-", role).strip("-") or "unassigned"
        agent_id = ("hermes-runtime-" + safe_role)[:80]
        with self._lock:
            existing = self.agents.get(agent_id)
        if existing is None:
            self.register(
                agent_id, role, "hermes", [role],
                "Hermes subagent lifecycle hook (runtime-observed)",
                install_ref="runtime:subagent",
                description="Observed delegated Hermes subagent role; not a separately installed plugin.",
            )
            with self._lock:
                self.agents[agent_id]["status"] = "runtime_observed"
                self._save()
        return agent_id

    def record(self, agent_id, task, success, quality=None, duration_seconds=None):
        with self._lock:
            self._refresh_profile()
        agent_id = str(agent_id or "").strip()
        task = str(task or "").strip()[:1000]
        if not task or not isinstance(success, bool):
            raise ValueError("task and boolean success are required")
        quality_value = None
        if quality is not None:
            quality_value = float(quality)
            if not 0 <= quality_value <= 100:
                raise ValueError("quality must be between 0 and 100")
        duration = None
        if duration_seconds is not None:
            duration = float(duration_seconds)
            if not 0 <= duration <= 7 * 24 * 3600:
                raise ValueError("duration_seconds must be between 0 and 604800")
        with self._lock:
            if self._load_error:
                raise RuntimeError("Agent registry data is unreadable; refusing changes")
            agent = self.agents.get(agent_id)
            if not agent:
                raise ValueError("agent is not registered")
            task_tokens = _tokens(task)
            cap_tokens = _tokens(agent.get("capabilities", []))
            fit = 100.0 * len(task_tokens & cap_tokens) / max(1, len(task_tokens))
            event = {
                "timestamp": time.time(), "task_fit": round(fit, 2),
                "success": success, "quality": quality_value, "duration_seconds": duration,
            }
            events = agent.setdefault("observations", [])
            events.append(event)
            agent["observations"] = events[-500:]
            self._save()
        return self.summary(agent_id)

    def summary(self, agent_id):
        with self._lock:
            self._refresh_profile()
        agent = self.agents.get(str(agent_id or "").strip())
        if agent is None:
            raise ValueError("agent is not registered")
        events = agent.get("observations", [])
        n = len(events)
        success_rate = 100.0 * sum(bool(e.get("success")) for e in events) / n if n else 0.0
        avg_fit = sum(float(e.get("task_fit", 0)) for e in events) / n if n else 0.0
        quality_events = [float(e["quality"]) for e in events if isinstance(e.get("quality"), (int, float))]
        avg_quality = sum(quality_events) / len(quality_events) if quality_events else None
        # A missing quality score is neutral, not silently treated as perfect.
        score = (0.4 * avg_fit + 0.4 * success_rate + 0.2 * avg_quality) if avg_quality is not None else (0.5 * avg_fit + 0.5 * success_rate)
        durations = [float(e["duration_seconds"]) for e in events if isinstance(e.get("duration_seconds"), (int, float))]
        return {
            "id": agent["id"], "name": agent["name"], "kind": agent["kind"],
            "capabilities": agent["capabilities"], "source": agent["source"],
            "endpoint": agent.get("endpoint", ""), "install_ref": agent.get("install_ref", ""),
            "description": agent.get("description", ""), "status": agent["status"],
            "source_verified": False,
            "observations": n, "success_rate": round(success_rate, 2),
            "average_task_fit": round(avg_fit, 2),
            "average_quality": round(avg_quality, 2) if avg_quality is not None else None,
            "average_duration_seconds": round(sum(durations) / len(durations), 2) if durations else None,
            "score": round(score, 2), "performance_score": round(score, 2), "tier": _tier(score, n),
            "evidence": "observed_completions" if n >= 5 else "insufficient_observations",
            "rate_note": "Rates use locally recorded completed tasks; quality is optional and omitted when unavailable.",
        }

    def rank(self, task=""):
        with self._lock:
            self._refresh_profile()
        task_tokens = _tokens(task)
        rows = []
        for agent_id, agent in list(self.agents.items()):
            item = self.summary(agent_id)
            caps = _tokens(agent.get("capabilities", []))
            fit = 100.0 * len(task_tokens & caps) / max(1, len(task_tokens)) if task_tokens else item["average_task_fit"]
            # Ranking blends current task capability fit with measured historical score.
            item["requested_task_fit"] = round(fit, 2)
            item["ranking_score"] = round(0.6 * fit + 0.4 * item["score"], 2) if item["observations"] >= 5 else round(fit, 2)
            rows.append(item)
        rows.sort(key=lambda x: (TIER_ORDER.get(x["tier"], 0), x["ranking_score"], x["observations"], x["name"].lower()), reverse=True)
        for index, row in enumerate(rows, 1):
            row["rank"] = index
        return rows
