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


class AgentRegistry:
    """Small local registry; no network calls, installs, or agent execution."""

    def __init__(self, data_dir):
        self.path = Path(data_dir) / "agents.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.agents = {}
        self._load()

    def _load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("agents"), dict):
                self.agents = {k: v for k, v in raw["agents"].items()
                               if isinstance(k, str) and isinstance(v, dict)}
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError):
            # Keep the registry untouched; never quarantine or overwrite malformed data.
            self.agents = {}

    def _save(self):
        payload = json.dumps({"schema_version": 1, "agents": self.agents},
                             ensure_ascii=False, indent=2)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(payload + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def register(self, agent_id, name, kind, capabilities, source,
                 endpoint="", install_ref="", description=""):
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
            parsed = urlparse(endpoint)
            if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError("A2A endpoint must be an HTTPS URL without embedded credentials")
        elif not install_ref:
            raise ValueError("Hermes agents require a verifiable install_ref (repository or catalog reference)")
        with self._lock:
            previous = self.agents.get(agent_id, {})
            self.agents[agent_id] = {
                "id": agent_id, "name": name, "kind": kind,
                "capabilities": caps, "source": source, "endpoint": endpoint,
                "install_ref": install_ref, "description": description,
                "registered_at": previous.get("registered_at", time.time()),
                "observations": previous.get("observations", []),
                "status": "registered_not_installed" if kind == "hermes" else "registered_not_connected",
            }
            self._save()
        return self.summary(agent_id)

    def record(self, agent_id, task, success, quality=None, duration_seconds=None):
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
        agent = self.agents[agent_id]
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
            "observations": n, "success_rate": round(success_rate, 2),
            "average_task_fit": round(avg_fit, 2),
            "average_quality": round(avg_quality, 2) if avg_quality is not None else None,
            "average_duration_seconds": round(sum(durations) / len(durations), 2) if durations else None,
            "score": round(score, 2), "tier": _tier(score, n),
            "evidence": "observed_completions" if n >= 5 else "insufficient_observations",
            "rate_note": "Rates use locally recorded completed tasks; quality is optional and omitted when unavailable.",
        }

    def rank(self, task=""):
        task_tokens = _tokens(task)
        rows = []
        for agent_id, agent in list(self.agents.items()):
            item = self.summary(agent_id)
            caps = _tokens(agent.get("capabilities", []))
            fit = 100.0 * len(task_tokens & caps) / max(1, len(task_tokens)) if task_tokens else item["average_task_fit"]
            # Ranking blends current task capability fit with measured historical score.
            item["requested_task_fit"] = round(fit, 2)
            item["ranking_score"] = round(0.6 * fit + 0.4 * item["score"], 2) if item["observations"] >= 5 else round(fit * 0.6, 2)
            rows.append(item)
        rows.sort(key=lambda x: (x["ranking_score"], x["observations"], x["name"].lower()), reverse=True)
        for index, row in enumerate(rows, 1):
            row["rank"] = index
        return rows
