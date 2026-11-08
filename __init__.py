"""Rariflat — status characters, reliability-aware routing, and opt-in loop guard."""
from __future__ import annotations

import atexit
import hashlib
import json
import logging
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


def _tokens(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, dict):
        value = " ".join(f"{k} {v}" for k, v in value.items())
    elif isinstance(value, (list, tuple, set)):
        value = " ".join(map(str, value))
    else:
        value = str(value)
    return {t for t in re.findall(r"[a-z0-9_+-]{2,}", value.lower()) if t not in STOP_WORDS}


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
        for key in ("exit_code", "returncode", "status_code"):
            value = result.get(key)
            if isinstance(value, (int, float)) and value != 0:
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
            recent = [t for t in self._recent_calls.get(key, []) if stamp - t <= window]
            recent.append(stamp)
            self._recent_calls[key] = recent
            return len(recent) >= repeats

    def record_result(self, tool_name: str, args: Any, success: bool, timestamp: float | None = None) -> None:
        if not tool_name or tool_name in OWN_TOOLS:
            return
        now = float(timestamp if timestamp is not None else time.time())
        with self._lock:
            item = self.tools.setdefault(tool_name, {"rarity": 50, "restraint": 50, "uses": 0, "successes": 0, "fail_streak": 0, "tokens": [], "last_used": 0, "last_failure": 0})
            item["uses"] = int(item.get("uses", 0)) + 1
            item["last_used"] = now
            if success:
                item["successes"] = int(item.get("successes", 0)) + 1
                item["fail_streak"] = 0
                item["rarity"] = min(100, int(item.get("rarity", 50)) + 2)
                item["restraint"] = min(100, int(item.get("restraint", 50)) + 1)
            else:
                item["fail_streak"] = int(item.get("fail_streak", 0)) + 1
                item["last_failure"] = now
                item["rarity"] = max(0, int(item.get("rarity", 50)) - 1)
                item["restraint"] = max(0, int(item.get("restraint", 50)) - 3)
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
        task_tokens = _tokens(task)
        ranked = []
        for name, data in store.tools.items():
            learned = set(data.get("tokens", [])) | _tokens(name)
            overlap = len(task_tokens & learned)
            reliability = (int(data.get("successes", 0)) + 1) / (int(data.get("uses", 0)) + 2)
            score = overlap * 10 + reliability * 3 + int(data.get("rarity", 50)) / 100
            ranked.append((score, name, data, overlap))
        ranked.sort(key=lambda row: (row[0], row[2].get("uses", 0)), reverse=True)
        recommended = [{"skill": name, "rarity": data.get("rarity", 50), "restraint": data.get("restraint", 50),
                        "uses": data.get("uses", 0), "task_match": overlap,
                        "reliability": round((data.get("successes", 0) + 1) / (data.get("uses", 0) + 2), 3)}
                       for _, name, data, overlap in ranked[:5]]
        best = ranked[0][1] if ranked else None
        return json.dumps({"task": task, "recommended": recommended, "best": best,
                           "message": f"Rariflat recommends {best}." if best else "No tool history yet."})

    def get_status(args=None, **kwargs):
        top = sorted(store.tools.items(), key=lambda x: (x[1].get("successes", 0) / max(1, x[1].get("uses", 0)), x[1].get("uses", 0)), reverse=True)[:5]
        return json.dumps({"characters_active": True, "tracked_tools": len(store.tools), "guard_enabled": store.guard_enabled,
                           "top_skills": [{"name": n, "rarity": d.get("rarity", 50), "restraint": d.get("restraint", 50),
                                           "uses": d.get("uses", 0), "successes": d.get("successes", 0)} for n, d in top]})

    def guard_check(args, **kwargs):
        args = args if isinstance(args, dict) else {}
        tool = str(args.get("tool") or "")
        data = store.tools.get(tool, {})
        streak = int(data.get("fail_streak", 0))
        blocked = store.guard_enabled and not _is_own_tool(tool) and streak >= _guard_threshold()
        return json.dumps({"tool": tool, "guard_enabled": store.guard_enabled, "fail_streak": streak, "blocked": blocked,
                           "message": f"{tool} would be blocked." if blocked else f"{tool} is allowed."})

    ctx.register_tool(name="rariflat_route", toolset="rariflat",
        schema={"name": "rariflat_route", "description": "Recommend a tool for a task using learned argument tokens and reliability.", "parameters": {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]}},
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
