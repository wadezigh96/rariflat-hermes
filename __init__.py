"""Rariflat — status characters, reliability-aware routing, and opt-in loop guard."""
from __future__ import annotations

import atexit
import hashlib
import importlib.util
import json
import logging
import math
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("rariflat")
_VERBOSE = os.getenv("RARIFLAT_VERBOSE", "").strip().lower() in {"1", "true", "yes", "on"}
if _VERBOSE:
    logger.setLevel(logging.INFO)

OWN_TOOLS = {"rariflat_route", "rariflat_status", "rariflat_guard", "rariflat_agent_register", "rariflat_agent_complete", "rariflat_agent_rank"}
STOP_WORDS = {"a", "an", "and", "are", "as", "at", "by", "for", "from", "how", "i", "in", "into", "is", "it", "of", "on", "or", "please", "the", "to", "use", "with", "check", "find", "do", "this", "that", "me", "my"}
FAILURE_PREFIXES = ("error:", "error ", "failed:", "failed ", "failure:", "failure ", "command not found", "no such file or directory", "permission denied", "traceback (most recent call last)", "exception:", "timed out", "timeout:")
_ROUTE_WEIGHTS = {"task_fit": 0.40, "reliability": 0.25, "rarity": 0.20, "restraint": 0.15}
_MIN_ROUTE_OBSERVATIONS = 5
_MAX_ROUTE_EVENT_RECOMMENDATIONS = 3
_MAX_ROUTE_EVENT_COUNT = 1_000_000

CHARACTERS = {
    "web": {"name": "Owl", "emoji": "🦉", "awaken": ["scans the horizon"], "success": ["knowledge found"], "fail": ["the trail goes cold"]},
    "search": {"name": "Owl", "emoji": "🦉", "awaken": ["hunts for knowledge"], "success": ["returns with what it sought"], "fail": ["returns empty-taloned"]},
    "browser": {"name": "Scout", "emoji": "🔍", "awaken": ["maps the path ahead"], "success": ["marks the territory"], "fail": ["the path is blocked"]},
    "terminal": {"name": "Hephaestus", "emoji": "⚒️", "awaken": ["stokes the forge"], "success": ["strikes true"], "fail": ["the metal cracks"]},
    "code": {"name": "Hephaestus", "emoji": "⚒️", "awaken": ["shapes the code"], "success": ["the artifact takes form"], "fail": ["the form collapses"]},
    "file": {"name": "Archivist", "emoji": "📜", "awaken": ["unrolls an ancient scroll"], "success": ["files the knowledge"], "fail": ["the page is missing"]},
    "memory": {"name": "Mnemosyne", "emoji": "🧠", "awaken": ["stirs the waters of memory"], "success": ["the memory surfaces"], "fail": ["the memory slips away"]},
    "skill": {"name": "Mentor", "emoji": "🎓", "awaken": ["opens the lesson"], "success": ["the student understands"], "fail": ["the lesson needs repeating"]},
    "skills": {"name": "Mentor", "emoji": "🎓", "awaken": ["opens the lesson"], "success": ["the student understands"], "fail": ["the lesson needs repeating"]},
    "image": {"name": "Muse", "emoji": "🎨", "awaken": ["dips the brush"], "success": ["the vision appears"], "fail": ["the colors run"]},
    "vision": {"name": "Seer", "emoji": "👁️", "awaken": ["opens the third eye"], "success": ["the truth is revealed"], "fail": ["the veil thickens"]},
    "tts": {"name": "Bard", "emoji": "🎵", "awaken": ["tunes the instrument"], "success": ["the song carries"], "fail": ["a string snaps"]},
    "error": {"name": "Cerberus", "emoji": "🐾", "awaken": ["all three heads rise"], "success": ["the threat is contained"], "fail": ["the guardians bark"]},
    "default": {"name": "Hermes", "emoji": "🚀", "awaken": ["laces the winged sandals"], "success": ["delivers the message"], "fail": ["the wind shifts"]},
}


_SENSITIVE_KEY_RE = re.compile(
    r"(?:^|[_-])(password|passwd|pwd|secret|token|api[_-]?key|"
    r"access[_-]?key|private[_-]?key|authorization|cookie|credential)s?(?:$|[_-])",
    re.IGNORECASE,
)
_INLINE_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret|client[_-]?secret)\b(\s*[:=]\s*)[^\s,;]+"
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[^\s,;]+")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")


def _safe_token_parts(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            key_text = str(key)
            if _SENSITIVE_KEY_RE.search(re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key_text).replace(" ", "_")):
                continue
            parts.append(key_text)
            parts.extend(_safe_token_parts(item))
        return parts
    if isinstance(value, (list, tuple, set)):
        return [part for item in value for part in _safe_token_parts(item)]
    text = str(value)
    text = _INLINE_SECRET_RE.sub(r"\1\2[REDACTED]", text)
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    text = _JWT_RE.sub("[REDACTED]", text)
    return [text]


# Capability aliases bridge natural-language task wording and common tool names.
# Keep this intentionally small and inspectable; this is lexical matching, not an
# embedding model or a claim of semantic understanding.
_ROUTING_ALIASES = {
    "documentation": "search",
    "document": "search",
    "docs": "search",
    "lookup": "search",
    "research": "search",
    "browse": "search",
    "browsing": "search",
    "internet": "search",
    "online": "search",
}


def _tokens(value: Any) -> set[str]:
    """Extract safe routing tokens, splitting tool-name compounds and normalizing aliases."""
    parts = _safe_token_parts(value)
    text = " ".join(parts)
    # Split snake_case, kebab-case, dotted names, and CamelCase before tokenizing.
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = re.findall(r"[a-z0-9+-]{2,}", re.sub(r"[_./:-]+", " ", text.lower()))
    tokens = {word for word in words if word not in STOP_WORDS}
    tokens.update(_ROUTING_ALIASES[word] for word in tuple(tokens) if word in _ROUTING_ALIASES)
    return tokens


def _safe_fingerprint_value(value: Any) -> Any:
    """Build a stable fingerprint without credential-like fields or inline secrets."""
    if isinstance(value, dict):
        safe = {}
        for key, item in value.items():
            key_text = str(key)
            normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key_text).replace(" ", "_")
            if _SENSITIVE_KEY_RE.search(normalized):
                continue
            safe[key_text] = _safe_fingerprint_value(item)
        return safe
    if isinstance(value, (list, tuple)):
        return [_safe_fingerprint_value(item) for item in value]
    if isinstance(value, str):
        value = _INLINE_SECRET_RE.sub(r"\1\2[REDACTED]", value)
        value = _BEARER_RE.sub("Bearer [REDACTED]", value)
        return _JWT_RE.sub("[REDACTED]", value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return str(value)


def _learn_args_enabled() -> bool:
    """Whether argument text may contribute task tokens to local recommendations."""
    return os.getenv("RARIFLAT_LEARN_ARGS", "1").strip().lower() not in {"0", "false", "no", "off"}


def _get_character(tool_name: str) -> dict:
    for token in re.split(r"[^a-z0-9]+", str(tool_name or "").lower()):
        if token in CHARACTERS and token != "default":
            return CHARACTERS[token]
    return CHARACTERS["default"]


def judge_result(result: Any) -> bool:
    """Prefer structured outcome signals; empty output is a successful completion."""
    if result is None or result == "":
        return True
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        if result.get("success") is False or result.get("ok") is False or result.get("error"):
            return False
        for key in ("exit_code", "returncode"):
            value = result.get(key)
            if isinstance(value, (int, float)) and value != 0:
                return False
        # HTTP 2xx succeeds; redirects are not failures, but 4xx/5xx are.
        status_code = result.get("status_code")
        if isinstance(status_code, (int, float)) and (
            status_code == 0 or status_code < 100 or status_code >= 400
        ):
            return False
        return True
    if isinstance(result, (int, float)):
        return result == 0
    text = str(result).strip()
    if not text:
        return True
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return judge_result(parsed)
        except (ValueError, TypeError):
            pass
    lowered = text.lower()
    return not any(lowered.startswith(prefix) for prefix in FAILURE_PREFIXES)


def _recent_usage_metrics(data: dict, now: float | None = None, window: int = 30) -> dict:
    """Count calls and duplicate fingerprints in a rolling time window."""
    stamp = float(now if now is not None else time.time())
    events = data.get("recent_events", [])
    if not isinstance(events, list):
        events = []
    fresh = [
        event for event in events
        if isinstance(event, dict)
        and isinstance(event.get("timestamp"), (int, float))
        and 0 <= stamp - float(event["timestamp"]) <= window
    ]
    seen: set[str] = set()
    repeats = 0
    for event in sorted(fresh, key=lambda item: float(item["timestamp"])):
        fingerprint = str(event.get("fingerprint", ""))
        if fingerprint and fingerprint in seen:
            repeats += 1
        if fingerprint:
            seen.add(fingerprint)
    return {"recent_uses": len(fresh), "repeated_calls_30s": repeats}


def _rank_tools(task: str, tools: dict[str, dict]) -> list[dict]:
    """Rank tools using measurable task fit, reliability, usage rarity and restraint."""
    task_tokens = _tokens(task)
    ranked = []
    for name, data in tools.items():
        learned = set(data.get("tokens", [])) | _tokens(name)
        overlap = len(task_tokens & learned)
        match = (overlap / max(1, len(task_tokens))) * 100 if task_tokens else 0.0
        uses = max(0, int(data.get("uses", 0)))
        successes = max(0, min(uses, int(data.get("successes", 0))))
        reliability = (successes / uses) * 100 if uses else 50.0
        # Rarity is derived from observed call frequency, not a manually tuned counter.
        rarity = 100.0 / (1.0 + math.log2(uses + 1))
        # Prefer a live rolling window; retain legacy counters for old score files/tests.
        recent = _recent_usage_metrics(data)
        recent_uses = recent["recent_uses"]
        repeated_calls = recent["repeated_calls_30s"]
        # Legacy records are migrated on load to an empty live window. Lifetime
        # repeat totals remain available separately and never contaminate live restraint.
        restraint = (1.0 - repeated_calls / recent_uses) * 100 if recent_uses else 100.0
        factor_values = {
            "task_fit": match,
            "reliability": reliability,
            "rarity": rarity,
            "restraint": restraint,
        }
        score = sum(factor_values[factor] * weight for factor, weight in _ROUTE_WEIGHTS.items())
        ranked.append({
            "skill": name,
            "score": round(score, 2),
            "rarity": round(rarity, 2),
            "restraint": round(restraint, 2),
            "reliability": round(reliability, 2),
            "task_match": overlap,
            "task_match_score": round(match, 2),
            "uses": uses,
            "successes": successes,
            "failures": uses - successes,
            "repeated_calls": repeated_calls,
            "repeated_calls_30s": repeated_calls,
            "recent_uses": recent_uses,
            "first_used": data.get("first_used"),
            "last_used": data.get("last_used"),
            "reason": (
                f"Task fit {match:.1f}/100 (overlap {overlap}); "
                f"reliability {reliability:.1f}/100 ({successes}/{uses} successes); "
                f"rarity {rarity:.1f}/100 (observed uses: {uses}); "
                f"restraint {restraint:.1f}/100 ({repeated_calls} repeated calls among {recent_uses} recent uses in 30s). "
                "Weighted score: 40% task fit, 25% reliability, "
                "20% rarity, 15% restraint."
            ),
            "factors": {
                "task_fit": round(match, 2),
                "reliability": round(reliability, 2),
                "rarity": round(rarity, 2),
                "restraint": round(restraint, 2),
            },
        })
    ranked.sort(key=lambda row: (row["score"], row["uses"], row["skill"]), reverse=True)
    return ranked

class Store:
    """Thread-safe local score store with atomic writes and corruption quarantine."""
    def __init__(self, data_dir: Path | str | None = None):
        configured = data_dir or os.getenv("RARIFLAT_DATA_DIR")
        self.data_dir = Path(configured).expanduser() if configured else Path.home() / ".hermes" / "plugin-data" / "rariflat"
        self.path = self.data_dir / "scores.json"
        self.tools: dict[str, dict] = {}
        self.guard_enabled = os.getenv("RARIFLAT_GUARD", "").strip().lower() in {"1", "true", "yes", "on"}
        self._lock = threading.RLock()
        self._last_save = 0.0
        self._recent_calls: dict[str, list[float]] = {}
        self.sessions_started = 0
        self.first_session_at: float | None = None
        self.last_session_at: float | None = None
        self._load()

    def _load(self) -> None:
        with self._lock:
            if not self.path.exists():
                return
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                raw = data.get("tools", data) if isinstance(data, dict) else {}
                if isinstance(raw, dict):
                    self.tools = {str(k): v for k, v in raw.items() if isinstance(v, dict)}
                    # Legacy score files have lifetime repeat counters but no timestamps.
                    # Preserve those totals, but never mislabel them as repeats in the live window.
                    for item in self.tools.values():
                        if "recent_events" not in item:
                            item["repeated_calls_total"] = int(item.get("repeated_calls_total", item.get("repeated_calls", 0)))
                            item["repeated_calls"] = 0
                            item["recent_events"] = []
                if isinstance(data, dict) and "tools" in data:
                    if "RARIFLAT_GUARD" not in os.environ and isinstance(data.get("guard_enabled"), bool):
                        self.guard_enabled = data["guard_enabled"]
                    self.sessions_started = max(0, int(data.get("sessions_started", 0)))
                    self.first_session_at = data.get("first_session_at")
                    self.last_session_at = data.get("last_session_at")
            except (OSError, ValueError, TypeError) as exc:
                damaged = self.path.with_name(f"scores.json.corrupt-{int(time.time() * 1000)}")
                try:
                    self.path.replace(damaged)
                    logger.warning("Rariflat quarantined corrupt score data: %s", exc)
                except OSError:
                    logger.warning("Rariflat could not quarantine corrupt score data: %s", exc)

    def record_session_start(self, timestamp: float | None = None) -> None:
        """Record a plugin runtime start; this is not an account-login signal."""
        now = float(timestamp if timestamp is not None else time.time())
        with self._lock:
            self.sessions_started += 1
            if self.first_session_at is None:
                self.first_session_at = now
            self.last_session_at = now
        self.save(force=True)

    def set_guard(self, enabled: bool) -> None:
        with self._lock:
            self.guard_enabled = bool(enabled)
        self.save(force=True)

    def loop_detected(self, tool: str, args: Any, now: float | None = None) -> bool:
        try:
            repeats = max(0, int(os.getenv("RARIFLAT_LOOP_REPEAT", "0")))
            window = max(1, int(os.getenv("RARIFLAT_LOOP_WINDOW", "30")))
        except ValueError:
            return False
        if repeats < 2:
            return False
        stamp = float(now if now is not None else time.time())
        try:
            signature = json.dumps(args if isinstance(args, (dict, list, str, int, float, bool)) else str(args), sort_keys=True, default=str)
        except (TypeError, ValueError):
            signature = repr(args)
        key = tool + ":" + hashlib.sha256(signature.encode("utf-8")).hexdigest()
        with self._lock:
            # Prune expired signatures globally and bound high-cardinality inputs.
            for old_key, timestamps in list(self._recent_calls.items()):
                fresh = [t for t in timestamps if 0 <= stamp - t <= window]
                if fresh:
                    self._recent_calls[old_key] = fresh
                else:
                    self._recent_calls.pop(old_key, None)
            recent = self._recent_calls.pop(key, [])
            recent.append(stamp)
            recent = recent[-repeats:]
            self._recent_calls[key] = recent
            while len(self._recent_calls) > 1024:
                self._recent_calls.pop(next(iter(self._recent_calls)))
            return len(recent) >= repeats

    def record_result(self, tool_name: str, args: Any, success: bool, timestamp: float | None = None) -> None:
        if not tool_name or tool_name in OWN_TOOLS:
            return
        now = float(timestamp if timestamp is not None else time.time())
        with self._lock:
            item = self.tools.setdefault(tool_name, {"uses": 0, "successes": 0, "repeated_calls": 0, "fail_streak": 0, "tokens": [], "last_used": 0, "last_failure": 0})
            fingerprint_source = json.dumps(
                _safe_fingerprint_value(args),
                sort_keys=True, default=str,
            )
            fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
            previous_used = float(item.get("last_used", 0))
            if item.get("last_args_fingerprint") == fingerprint and 0 <= now - previous_used <= 30:
                item["repeated_calls"] = int(item.get("repeated_calls", 0)) + 1
            item["repeated_calls_total"] = int(item.get("repeated_calls_total", item.get("repeated_calls", 0)))
            item["last_args_fingerprint"] = fingerprint
            item["uses"] = int(item.get("uses", 0)) + 1
            item["first_used"] = item.get("first_used") or now
            item["last_used"] = now
            events = item.get("recent_events", [])
            if not isinstance(events, list):
                events = []
            events = [
                event for event in events
                if isinstance(event, dict)
                and isinstance(event.get("timestamp"), (int, float))
                and 0 <= now - float(event["timestamp"]) <= 30
            ]
            events.append({"timestamp": now, "fingerprint": fingerprint})
            item["recent_events"] = events[-256:]
            if success:
                item["successes"] = int(item.get("successes", 0)) + 1
                item["fail_streak"] = 0
                item["last_success"] = now
            else:
                item["failures"] = int(item.get("failures", 0)) + 1
                item["fail_streak"] = int(item.get("fail_streak", 0)) + 1
                item["last_failure"] = now
            if _learn_args_enabled():
                item["tokens"] = sorted(set(item.get("tokens", [])) | _tokens(args))[:160]
        self.save()

    def save(self, force: bool = False) -> None:
        with self._lock:
            now = time.monotonic()
            if not force and now - self._last_save < 0.5:
                return
            tmp_name = None
            try:
                self.data_dir.mkdir(parents=True, exist_ok=True)
                payload = json.dumps({
                    "tools": self.tools,
                    "guard_enabled": self.guard_enabled,
                    "sessions_started": self.sessions_started,
                    "first_session_at": self.first_session_at,
                    "last_session_at": self.last_session_at,
                }, ensure_ascii=False, indent=2, sort_keys=True)
                fd, tmp_name = tempfile.mkstemp(prefix=".scores-", suffix=".tmp", dir=str(self.data_dir))
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_name, self.path)
                self._last_save = now
            except OSError as exc:
                logger.warning("Rariflat could not save scores: %s", exc)
            finally:
                if tmp_name and os.path.exists(tmp_name):
                    try:
                        os.unlink(tmp_name)
                    except OSError:
                        pass


_store_lock = threading.RLock()
_store: Store | None = None


def _get_store() -> Store:
    global _store
    with _store_lock:
        if _store is None:
            _store = Store()
        return _store


def _reset_for_tests(data_dir: Path | str | None = None) -> None:
    global _store
    with _store_lock:
        _store = Store(data_dir)


def _emit(phase: str, tool: str, success: bool | None = None, reason: str = "") -> None:
    try:
        from hermes_cli.plugin_events import broadcast_plugin_event
        broadcast_plugin_event("rariflat", "tool", {"phase": phase, "tool": str(tool), "success": success, "reason": reason})
    except Exception as exc:
        logger.debug("Rariflat desktop event unavailable: %s", exc)


def _route_event_payload(recommended: list[dict]) -> dict:
    """Project route results to a privacy-safe Desktop summary; never include task text or reasons."""
    def percentage(value: Any) -> float:
        try:
            number = float(value)
            return round(max(0.0, min(100.0, number)), 2) if math.isfinite(number) else 0.0
        except (TypeError, ValueError):
            return 0.0

    def raw_count(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError, OverflowError):
            return 0

    def count(value: Any) -> int:
        return min(_MAX_ROUTE_EVENT_COUNT, raw_count(value))

    rows = []
    for item in recommended[:_MAX_ROUTE_EVENT_RECOMMENDATIONS]:
        if not isinstance(item, dict):
            continue
        factors = item.get("factors") if isinstance(item.get("factors"), dict) else {}
        skill = "".join(char for char in str(item.get("skill") or "")[:80] if char.isprintable()).strip()
        if not skill:
            continue
        raw_uses = raw_count(item.get("uses"))
        raw_successes = raw_count(item.get("successes"))
        raw_failures = raw_count(item.get("failures"))
        uses = count(raw_uses)
        successes = min(uses, count(raw_successes))
        failures = uses - successes
        rows.append({
            "skill": skill,
            "score": percentage(item.get("score")),
            "uses": uses,
            "successes": successes,
            "failures": failures,
            "counts_capped": any(value > _MAX_ROUTE_EVENT_COUNT for value in (raw_uses, raw_successes, raw_failures)),
            "factors": {factor: percentage(factors.get(factor)) for factor in _ROUTE_WEIGHTS},
        })
    return {
        "recommended": rows,
        "weights": {factor: round(weight * 100) for factor, weight in _ROUTE_WEIGHTS.items()},
        "minimum_observations": _MIN_ROUTE_OBSERVATIONS,
    }


def _emit_route(recommended: list[dict]) -> None:
    """Send only aggregate route metadata to the optional local Desktop pane."""
    try:
        from hermes_cli.plugin_events import broadcast_plugin_event
        broadcast_plugin_event("rariflat", "route", _route_event_payload(recommended))
    except Exception as exc:
        logger.debug("Rariflat Desktop route event unavailable: %s", exc)



def _emit_agent_rank(recommended: list[dict]) -> None:
    """Send a bounded, privacy-safe agent ranking summary to the Desktop pane."""
    try:
        from hermes_cli.plugin_events import broadcast_plugin_event
        rows = []
        for index, item in enumerate(recommended[:10], 1):
            if not isinstance(item, dict):
                continue
            rows.append({
                "rank": index,
                "id": str(item.get("id") or "")[:80],
                "name": str(item.get("name") or "")[:100],
                "kind": item.get("kind") if item.get("kind") in {"hermes", "a2a"} else "unknown",
                "source": str(item.get("source") or "")[:300],
                "install_ref": str(item.get("install_ref") or "")[:300],
                "endpoint": str(item.get("endpoint") or "")[:300],
                "source_verified": False,
                "tier": item.get("tier") if item.get("tier") in {"MYTHIC", "LEGEND", "EPIC", "DEVELOPING", "UNRANKED"} else "UNRANKED",
                "score": max(0.0, min(100.0, float(item.get("ranking_score") or 0))),
                "performance_score": max(0.0, min(100.0, float(item.get("performance_score") or 0))),
                "requested_task_fit": max(0.0, min(100.0, float(item.get("requested_task_fit") or 0))),
                "observations": max(0, min(1000000, int(item.get("observations") or 0))),
                "success_rate": max(0.0, min(100.0, float(item.get("success_rate") or 0))),
                "average_task_fit": max(0.0, min(100.0, float(item.get("average_task_fit") or 0))),
                "average_quality": item.get("average_quality"),
                "average_duration_seconds": item.get("average_duration_seconds"),
                "status": str(item.get("status") or "")[:60],
                "evidence": str(item.get("evidence") or "")[:60],
            })
        broadcast_plugin_event("rariflat", "agent_rank", {"recommended": rows})
    except Exception as exc:
        logger.debug("Rariflat agent ranking Desktop event unavailable: %s", exc)


def _guard_threshold() -> int:
    try:
        return max(1, min(100, int(os.getenv("RARIFLAT_FAIL_STREAK", "3"))))
    except ValueError:
        return 3


def _cooldown() -> int:
    try:
        return max(0, min(3600, int(os.getenv("RARIFLAT_COOLDOWN", "30"))))
    except ValueError:
        return 30


def _is_own_tool(tool_name: str) -> bool:
    return tool_name in OWN_TOOLS or tool_name.startswith("rariflat_")


def register(ctx):
    store = _get_store()
    store.record_session_start()

    # Load the optional agent-ranking module from this plugin directory.
    # It performs local bookkeeping only: no network fetch, agent execution, or install.
    agent_registry = None
    try:
        agent_module_path = Path(__file__).with_name("agent_ranking.py")
        agent_spec = importlib.util.spec_from_file_location("rariflat_agent_ranking", agent_module_path)
        if agent_spec and agent_spec.loader:
            agent_module = importlib.util.module_from_spec(agent_spec)
            agent_spec.loader.exec_module(agent_module)
            agent_registry = agent_module.AgentRegistry(store.data_dir)
    except Exception as exc:
        logger.warning("Rariflat agent ranking unavailable: %s", exc)

    def agent_register(args, **kwargs):
        args = args if isinstance(args, dict) else {}
        if agent_registry is None:
            return json.dumps({"error": "Agent ranking module unavailable."})
        try:
            item = agent_registry.register(
                args.get("agent_id"), args.get("name"), args.get("kind"),
                args.get("capabilities"), args.get("source"),
                endpoint=args.get("endpoint", ""), install_ref=args.get("install_ref", ""),
                description=args.get("description", ""),
            )
            _emit_agent_rank(agent_registry.rank(""))
            return json.dumps({"registered": True, "agent": item,
                               "message": "Registered only; no install or connection was performed."})
        except (TypeError, ValueError, RuntimeError) as exc:
            return json.dumps({"registered": False, "error": str(exc)})

    def agent_complete(args, **kwargs):
        args = args if isinstance(args, dict) else {}
        if agent_registry is None:
            return json.dumps({"error": "Agent ranking module unavailable."})
        try:
            item = agent_registry.record(
                args.get("agent_id"), args.get("task"), args.get("success"),
                quality=args.get("quality"), duration_seconds=args.get("duration_seconds"),
            )
            _emit_agent_rank(agent_registry.rank(""))
            return json.dumps({"recorded": True, "agent": item,
                               "message": "Completion recorded from the supplied outcome; Desktop agent ranking refreshed."})
        except (TypeError, ValueError, RuntimeError) as exc:
            return json.dumps({"recorded": False, "error": str(exc)})

    def agent_rank(args, **kwargs):
        args = args if isinstance(args, dict) else {}
        if agent_registry is None:
            return json.dumps({"error": "Agent ranking module unavailable."})
        recommended = agent_registry.rank(str(args.get("task") or ""))
        _emit_agent_rank(recommended)
        return json.dumps({
            "router_type": "hermes_and_a2a_agent_recommender",
            "dispatches_to_agent": False,
            "installs_agent": False,
            "recommended": recommended,
            "message": "Advisory ranking only. Unranked agents lack five observed completed tasks.",
        })

    active_subagents = {}

    def on_subagent_start(child_session_id=None, child_subagent_id=None,
                          child_role=None, child_goal=None, **kwargs):
        key = str(child_session_id or child_subagent_id or "").strip()
        if not key:
            return None
        role = str(child_role or "unassigned").strip()[:60] or "unassigned"
        active_subagents[key] = {
            "role": role,
            "task": str(child_goal or role)[:1000],
        }
        # Bound transient lifecycle state if a runtime fails to emit stop events.
        while len(active_subagents) > 2000:
            active_subagents.pop(next(iter(active_subagents)))
        return None

    def on_subagent_stop(child_session_id=None, child_role=None,
                         child_summary=None, child_status="error",
                         duration_ms=None, **kwargs):
        if agent_registry is None:
            return None
        key = str(child_session_id or "").strip()
        started = active_subagents.pop(key, {})
        role = str(child_role or started.get("role") or "unassigned")[:60]
        task = str(started.get("task") or child_summary or role)[:1000]
        try:
            agent_id = agent_registry.register_runtime(role)
            duration = None
            if isinstance(duration_ms, (int, float)) and not isinstance(duration_ms, bool):
                duration = max(0.0, float(duration_ms) / 1000.0)
            success = str(child_status or "").lower() == "completed"
            agent_registry.record(agent_id, task, success, duration_seconds=duration)
            _emit_agent_rank(agent_registry.rank(""))
        except (TypeError, ValueError, RuntimeError) as exc:
            logger.warning("Rariflat could not record subagent completion: %s", exc)
        return None

    def route_skills(args, **kwargs):
        args = args if isinstance(args, dict) else {}
        task = str(args.get("task") or "").strip()
        ranked = _rank_tools(task, store.tools)
        recommended = ranked[:5]
        _emit_route(recommended)
        best = recommended[0]["skill"] if recommended else None
        return json.dumps({
            "router_type": "tool_skill_recommender",
            "dispatches_to_agent": False,
            "task": task,
            "recommended": recommended,
            "best": best,
            "message": (
                f"Rariflat recommends tool/skill {best}; it does not dispatch tasks to agents."
                if best else "No tool history yet."
            ),
        })
    def get_status(args=None, **kwargs):
        top = _rank_tools("", store.tools)[:5]
        return json.dumps({"characters_active": True, "tracked_tools": len(store.tools), "guard_enabled": store.guard_enabled,
                           "sessions_started": store.sessions_started,
                           "first_session_at": store.first_session_at,
                           "last_session_at": store.last_session_at,
                           "top_skills": [{"name": d["skill"], "rarity": d["rarity"], "restraint": d["restraint"],
                                           "reliability": d["reliability"], "uses": d["uses"],
                                           "successes": store.tools.get(d["skill"], {}).get("successes", 0),
                                           "failures": store.tools.get(d["skill"], {}).get("failures", 0),
                                           "first_used": d.get("first_used"), "last_used": d.get("last_used"),
                                           "recent_uses": d["recent_uses"],
                                           "repeated_calls_30s": d["repeated_calls_30s"],
                                           "repeated_calls_total": store.tools.get(d["skill"], {}).get("repeated_calls_total", store.tools.get(d["skill"], {}).get("repeated_calls", 0))}
                                          for d in top],
                           "tools_activity": [
                               {"name": name, "uses": data.get("uses", 0),
                                "successes": data.get("successes", 0), "failures": data.get("failures", 0),
                                "first_used": data.get("first_used"), "last_used": data.get("last_used"),
                                **_recent_usage_metrics(data)}
                               for name, data in sorted(store.tools.items(), key=lambda pair: pair[1].get("uses", 0), reverse=True)
                           ]})

    def guard_check(args, **kwargs):
        args = args if isinstance(args, dict) else {}
        tool = str(args.get("tool") or "")
        data = store.tools.get(tool, {})
        streak = int(data.get("fail_streak", 0))
        blocked = store.guard_enabled and not _is_own_tool(tool) and streak >= _guard_threshold()
        return json.dumps({"tool": tool, "guard_enabled": store.guard_enabled, "fail_streak": streak, "blocked": blocked,
                           "message": f"{tool} would be blocked." if blocked else f"{tool} is allowed."})

    ctx.register_tool(name="rariflat_agent_register", toolset="rariflat",
        schema={"name": "rariflat_agent_register", "description": "Register a Hermes catalog agent or A2A agent for local ranking. Does not install, connect, fetch remote cards, or execute agents.", "parameters": {"type": "object", "properties": {
            "agent_id": {"type": "string"}, "name": {"type": "string"},
            "kind": {"type": "string", "enum": ["hermes", "a2a"]},
            "capabilities": {"type": "array", "items": {"type": "string"}},
            "source": {"type": "string"}, "endpoint": {"type": "string"},
            "install_ref": {"type": "string"}, "description": {"type": "string"}},
            "required": ["agent_id", "name", "kind", "capabilities", "source"]}},
        handler=agent_register)
    ctx.register_tool(name="rariflat_agent_complete", toolset="rariflat",
        schema={"name": "rariflat_agent_complete", "description": "Record a real completed agent task outcome to update observed performance rates. Call only after completion.", "parameters": {"type": "object", "properties": {
            "agent_id": {"type": "string"}, "task": {"type": "string"},
            "success": {"type": "boolean"}, "quality": {"type": "number"},
            "duration_seconds": {"type": "number"}},
            "required": ["agent_id", "task", "success"]}},
        handler=agent_complete)
    ctx.register_tool(name="rariflat_agent_rank", toolset="rariflat",
        schema={"name": "rariflat_agent_rank", "description": "Rank registered Hermes and A2A agents by requested task fit and observed completed-task performance. Advisory only; no dispatch or installation.", "parameters": {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]}},
        handler=agent_rank)

    ctx.register_tool(name="rariflat_route", toolset="rariflat",
        schema={"name": "rariflat_route", "description": "Rank and recommend a Hermes tool/skill using task fit, reliability, rarity, and restraint. Advisory only; does not dispatch tasks to agents.", "parameters": {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]}},
        handler=route_skills)
    ctx.register_tool(name="rariflat_status", toolset="rariflat",
        schema={"name": "rariflat_status", "description": "Show Rariflat tool reliability and guard status.", "parameters": {"type": "object", "properties": {}}},
        handler=get_status)
    ctx.register_tool(name="rariflat_guard", toolset="rariflat",
        schema={"name": "rariflat_guard", "description": "Inspect whether the opt-in Rariflat guard would block a tool.", "parameters": {"type": "object", "properties": {"tool": {"type": "string"}}, "required": ["tool"]}},
        handler=guard_check)

    def on_pre_tool(tool_name, args=None, **kwargs):
        tool = str(tool_name or "")
        if _is_own_tool(tool):
            return None
        data = store.tools.get(tool, {})
        streak = int(data.get("fail_streak", 0))
        cooldown = _cooldown()
        if streak >= _guard_threshold() and (
            cooldown == 0 or time.time() - float(data.get("last_failure", 0)) >= cooldown
        ):
            data["fail_streak"] = 0
            store.save()
            streak = 0
        looped = store.loop_detected(tool, args) if store.guard_enabled else False
        if store.guard_enabled and (streak >= _guard_threshold() or looped):
            reason = "repeated identical calls" if looped else f"{streak} consecutive failures"
            message = f"Rariflat guard blocked {tool}: {reason}."
            _emit("blocked", tool, False, message)
            logger.warning(message)
            return {"action": "block", "message": message}
        char = _get_character(tool)
        if _VERBOSE:
            logger.info("%s %s is ready.", char["emoji"], char["name"])
        _emit("started", tool, None)
        return None

    def on_post_tool(tool_name, args=None, result=None, **kwargs):
        tool = str(tool_name or "")
        if _is_own_tool(tool):
            return None
        success = judge_result(result)
        store.record_result(tool, args, success)
        char = _get_character(tool)
        reaction = (char.get("success") if success else char.get("fail") or ["completed"])[0]
        if _VERBOSE:
            logger.info("%s %s: %s", char["emoji"], char["name"], reaction)
        # Tool output can contain credentials or user data; the Desktop event only
        # needs a safe status signal, not a copy of the raw failure payload.
        _emit("done", tool, success, "" if success else "Tool failed; details withheld to protect sensitive output.")
        return None

    ctx.register_hook("pre_tool_call", on_pre_tool)
    ctx.register_hook("post_tool_call", on_post_tool)
    ctx.register_hook("subagent_start", on_subagent_start)
    ctx.register_hook("subagent_stop", on_subagent_stop)

    def status_cmd(raw_args="", **kwargs):
        command = raw_args.strip().lower() if isinstance(raw_args, str) else ""
        if command in {"guard on", "guard off"}:
            enabled = command == "guard on"
            store.set_guard(enabled)
            return "Rariflat guard ON." if enabled else "Rariflat guard OFF."
        if command == "reset":
            with store._lock:
                store.tools.clear()
                store._recent_calls.clear()
            store.save(force=True)
            return "Rariflat scores cleared."
        lines = ["Rariflat — Tool Reliability", f"Guard: {'ON' if store.guard_enabled else 'OFF'}"]
        if not store.tools:
            lines.append("No tools tracked yet. Make some calls!")
        else:
            for i, (name, data) in enumerate(sorted(store.tools.items(), key=lambda x: x[1].get("uses", 0), reverse=True), 1):
                lines.append(f"{i}. {name} · success {data.get('successes', 0)}/{data.get('uses', 0)} · fail streak {data.get('fail_streak', 0)}")
        return "\n".join(lines)

    ctx.register_command(name="rariflat", handler=status_cmd, description="Show Rariflat reliability and guard status")


atexit.register(lambda: _get_store().save(force=True))
