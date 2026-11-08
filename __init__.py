"""Rariflat — status characters, reliability-aware routing, and opt-in loop guard."""
from __future__ import annotations

import atexit
import hashlib
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

OWN_TOOLS = {"rariflat_route", "rariflat_status", "rariflat_guard"}
STOP_WORDS = {"a", "an", "and", "are", "as", "at", "by", "for", "from", "how", "i", "in", "into", "is", "it", "of", "on", "or", "please", "the", "to", "use", "with", "check", "find", "do", "this", "that", "me", "my"}
FAILURE_PREFIXES = ("error:", "error ", "failed:", "failed ", "failure:", "failure ", "command not found", "no such file or directory", "permission denied", "traceback (most recent call last)", "exception:", "timed out", "timeout:")

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


def _tokens(value: Any) -> set[str]:
    """Extract useful routing tokens without retaining credential values."""
    parts = _safe_token_parts(value)
    text = " ".join(parts)
    return {t for t in re.findall(r"[a-z0-9_+-]{2,}", text.lower()) if t not in STOP_WORDS}


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
        # Restraint penalizes repeated identical calls within the 30-second observation window.
        repeated_calls = max(0, min(uses, int(data.get("repeated_calls", 0))))
        restraint = (1.0 - repeated_calls / uses) * 100 if uses else 100.0
        score = match * 0.40 + reliability * 0.25 + rarity * 0.20 + restraint * 0.15
        ranked.append({
            "skill": name,
            "score": round(score, 2),
            "rarity": round(rarity, 2),
            "restraint": round(restraint, 2),
            "reliability": round(reliability, 2),
            "task_match": overlap,
            "task_match_score": round(match, 2),
            "uses": uses,
            "repeated_calls": repeated_calls,
            "reason": (
                f"Task fit {match:.1f}/100 (overlap {overlap}); "
                f"reliability {reliability:.1f}/100 ({successes}/{uses} successes); "
                f"rarity {rarity:.1f}/100 (observed uses: {uses}); "
                f"restraint {restraint:.1f}/100 ({repeated_calls} repeated calls in 30s). "
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
            except (OSError, ValueError, TypeError) as exc:
                damaged = self.path.with_name(f"scores.json.corrupt-{int(time.time() * 1000)}")
                try:
                    self.path.replace(damaged)
                    logger.warning("Rariflat quarantined corrupt score data: %s", exc)
                except OSError:
                    logger.warning("Rariflat could not quarantine corrupt score data: %s", exc)

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
            item["last_args_fingerprint"] = fingerprint
            item["uses"] = int(item.get("uses", 0)) + 1
            item["last_used"] = now
            if success:
                item["successes"] = int(item.get("successes", 0)) + 1
                item["fail_streak"] = 0
            else:
                item["fail_streak"] = int(item.get("fail_streak", 0)) + 1
                item["last_failure"] = now
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
                payload = json.dumps({"tools": self.tools}, ensure_ascii=False, indent=2, sort_keys=True)
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

    def route_skills(args, **kwargs):
        args = args if isinstance(args, dict) else {}
        task = str(args.get("task") or "").strip()
        ranked = _rank_tools(task, store.tools)
        recommended = ranked[:5]
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
                           "top_skills": [{"name": d["skill"], "rarity": d["rarity"], "restraint": d["restraint"],
                                           "reliability": d["reliability"], "uses": d["uses"],
                                           "repeated_calls": d["repeated_calls"]} for d in top]})

    def guard_check(args, **kwargs):
        args = args if isinstance(args, dict) else {}
        tool = str(args.get("tool") or "")
        data = store.tools.get(tool, {})
        streak = int(data.get("fail_streak", 0))
        blocked = store.guard_enabled and not _is_own_tool(tool) and streak >= _guard_threshold()
        return json.dumps({"tool": tool, "guard_enabled": store.guard_enabled, "fail_streak": streak, "blocked": blocked,
                           "message": f"{tool} would be blocked." if blocked else f"{tool} is allowed."})

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
        if streak >= _guard_threshold() and _cooldown() and time.time() - float(data.get("last_failure", 0)) >= _cooldown():
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
        _emit("done", tool, success, "" if success else str(result)[:240])
        return None

    ctx.register_hook("pre_tool_call", on_pre_tool)
    ctx.register_hook("post_tool_call", on_post_tool)

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
            for i, (name, data) in enumerate(sorted(store.tools.items(), key=lambda x: x[1].get("uses", 0), reverse=True)[:10], 1):
                lines.append(f"{i}. {name} · success {data.get('successes', 0)}/{data.get('uses', 0)} · fail streak {data.get('fail_streak', 0)}")
        return "\n".join(lines)

    ctx.register_command(name="rariflat", handler=status_cmd, description="Show Rariflat reliability and guard status")


atexit.register(lambda: _get_store().save(force=True))
