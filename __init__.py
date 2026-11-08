"""Rariflat for Hermes Agent.

Observes tool calls, tracks how reliably each tool behaves, suggests tools for a task,
and (only if you opt in) can block tools you list in a config file.

Design rules:
- Default is observe-only. Nothing is ever blocked unless config.json / env says so.
- Tool *results* (untrusted text) can change statistics, never blocking decisions.
- No network, no credentials, no subprocesses. State lives in one local JSON file.
- Hooks fail open: an error inside Rariflat never blocks or breaks a tool call.
"""

from __future__ import annotations

import atexit
import contextlib
import importlib.util
import json
import logging
import os
import random
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Optional

try:  # POSIX only; on Windows the store falls back to in-process locking.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

__version__ = "1.2.0"
PLUGIN_ID = "rariflat"
OWN_PREFIX = "rariflat_"
BLOCK_MARKER = "Rariflat guard:"
FLUSH_EVERY = 10          # calls between disk writes
FLUSH_SECONDS = 5.0       # or this many seconds since the last write
HEAD_CHARS = 300          # how much of a plain-text result is inspected
MAX_JSON_CHARS = 1_000_000

logger = logging.getLogger("rariflat")

# --------------------------------------------------------------------------------------
# Characters (cosmetic). Keyed by a category; chosen by whole-token matching on tool names.
# --------------------------------------------------------------------------------------

CHARACTERS: dict[str, dict[str, Any]] = {
    "web": {"name": "Owl", "emoji": "🦉", "start": ["opens its eyes and scans the horizon"], "ok": ["hoots softly — knowledge found"], "fail": ["ruffles its feathers — the trail goes cold"]},
    "search": {"name": "Owl", "emoji": "🦉", "start": ["hunts for knowledge in the dark"], "ok": ["returns with what it sought"], "fail": ["returns empty-taloned"]},
    "browser": {"name": "Scout", "emoji": "🔍", "start": ["steps into the unknown"], "ok": ["marks the territory"], "fail": ["the path is blocked"]},
    "terminal": {"name": "Hephaestus", "emoji": "⚒️", "start": ["stokes the forge"], "ok": ["strikes true — the command is forged"], "fail": ["the metal cracks"]},
    "code": {"name": "Hephaestus", "emoji": "⚒️", "start": ["shapes the code on the anvil"], "ok": ["the artifact takes form"], "fail": ["the form collapses"]},
    "file": {"name": "Archivist", "emoji": "📜", "start": ["unrolls an ancient scroll"], "ok": ["files the knowledge precisely"], "fail": ["the page is missing"]},
    "memory": {"name": "Mnemosyne", "emoji": "🧠", "start": ["stirs the waters of memory"], "ok": ["the memory surfaces clearly"], "fail": ["the memory slips away"]},
    "skills": {"name": "Mentor", "emoji": "🎓", "start": ["opens the lesson"], "ok": ["the student understands"], "fail": ["the lesson needs repeating"]},
    "image": {"name": "Muse", "emoji": "🎨", "start": ["dips the brush"], "ok": ["the vision appears"], "fail": ["the colors run"]},
    "vision": {"name": "Seer", "emoji": "👁️", "start": ["opens the third eye"], "ok": ["the truth is revealed"], "fail": ["the veil thickens"]},
    "tts": {"name": "Bard", "emoji": "🎵", "start": ["tunes the instrument"], "ok": ["the song carries"], "fail": ["a string snaps"]},
    "default": {"name": "Hermes", "emoji": "🚀", "start": ["laces the winged sandals"], "ok": ["delivers the message"], "fail": ["the wind shifts"]},
    "blocked": {"name": "Cerberus", "emoji": "🐾", "start": ["all three heads rise — the gate stays shut"], "ok": [""], "fail": [""]},
}

# Whole tokens of a tool name (split on anything that is not a-z0-9) -> category.
TOKEN_CHAR = {
    "web": "web", "search": "search", "browser": "browser", "browse": "browser",
    "terminal": "terminal", "shell": "terminal", "bash": "terminal",
    "code": "code", "exec": "code", "execute": "code",
    "file": "file", "files": "file", "read": "file", "write": "file", "patch": "file",
    "memory": "memory", "skill": "skills", "skills": "skills",
    "image": "image", "vision": "vision", "tts": "tts", "speech": "tts",
}

# Task words that point at a category (used by rariflat_route).
CATEGORY_KEYWORDS = {
    "web": {"web", "search", "internet", "online", "news", "lookup", "google", "url", "website"},
    "search": {"web", "search", "internet", "online", "news", "lookup", "find", "google"},
    "browser": {"browser", "browse", "click", "navigate", "page", "site", "website", "screenshot"},
    "terminal": {"terminal", "shell", "bash", "command", "run", "execute", "script", "install", "git"},
    "code": {"code", "python", "function", "debug", "compile", "program", "script", "run"},
    "file": {"file", "files", "read", "write", "edit", "save", "folder", "directory", "patch", "document"},
    "memory": {"memory", "remember", "recall", "note", "notes", "forget"},
    "skills": {"skill", "skills", "workflow", "playbook"},
    "image": {"image", "picture", "draw", "illustration", "photo", "generate"},
    "vision": {"vision", "see", "look", "analyze", "ocr", "describe", "screenshot", "picture"},
    "tts": {"tts", "speech", "speak", "voice", "audio", "say"},
}


def _tokens(text: Optional[str]) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t]


def character_key(tool_name: Optional[str]) -> str:
    """Category for a tool name using whole-token matching ('profile' does not match 'file')."""
    for tok in _tokens(tool_name):
        key = TOKEN_CHAR.get(tok)
        if key:
            return key
    return "default"


def is_own_tool(tool_name: Optional[str]) -> bool:
    return (tool_name or "").strip().lower().startswith(OWN_PREFIX)


# --------------------------------------------------------------------------------------
# Success detection
# --------------------------------------------------------------------------------------

_FAIL_START = ("error", "traceback (most recent call last)", "exception", "fatal", "failed")
_FAIL_PHRASES = (
    "command not found",
    "no such file or directory",
    "permission denied",
    "traceback (most recent call last)",
    "is not recognized as an internal or external command",
    "connection refused",
)


def _dict_failed(d: dict) -> bool:
    if d.get("success") is False or d.get("ok") is False:
        return True
    if d.get("error"):
        return True
    if isinstance(d.get("status"), str) and d["status"].lower() in ("error", "failed", "failure"):
        return True
    for key in ("exit_code", "returncode", "exit_status"):
        v = d.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0:
            return True
    return False


def classify(result: Any, status: Any = None, error_type: Any = None) -> bool:
    """True if the tool call looks successful.

    Structured signals win (error_type/status kwargs, dict or JSON results). Plain text is
    judged conservatively from its first characters only. Empty output counts as success.
    This feeds statistics only; it never drives a block decision.
    """
    if error_type:
        return False
    if isinstance(status, str) and status.lower() in ("error", "failed", "failure"):
        return False
    if result is None:
        return True
    if isinstance(result, dict):
        return not _dict_failed(result)
    if isinstance(result, (list, tuple)):
        return True
    text = result if isinstance(result, str) else str(result)[:HEAD_CHARS * 4]
    s = text.strip()
    if not s:
        return True
    if s[0] in "{[" and len(s) <= MAX_JSON_CHARS:
        try:
            parsed = json.loads(s)
        except ValueError:
            parsed = None
        else:
            return not _dict_failed(parsed) if isinstance(parsed, dict) else True
    head = s[:HEAD_CHARS].lower()
    if head.startswith(_FAIL_START):
        return False
    return not any(p in head for p in _FAIL_PHRASES)


# --------------------------------------------------------------------------------------
# Config (observe-only unless the user opts in)
# --------------------------------------------------------------------------------------


def default_data_dir() -> Path:
    home = os.environ.get("HERMES_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".hermes"
    return base / "plugin-data" / PLUGIN_ID


def _env_bool(name: str) -> Optional[bool]:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name: str) -> Optional[list[str]]:
    raw = os.environ.get(name)
    if raw is None:
        return None
    return [p for p in (x.strip() for x in raw.split(",")) if p]


def _names(value: Any) -> Optional[frozenset]:
    if not isinstance(value, (list, tuple)):
        return None
    return frozenset(str(v).strip().lower() for v in value if str(v).strip())


class Config:
    """config.json in the data dir, re-read only when its mtime changes. Env vars override."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._mtime: Optional[int] = None
        self._raw: dict = {}

    def _refresh(self) -> None:
        try:
            mtime = self.path.stat().st_mtime_ns
        except OSError:
            self._mtime, self._raw = None, {}
            return
        if mtime == self._mtime:
            return
        self._mtime = mtime
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._raw = data if isinstance(data, dict) else {}
        except (OSError, ValueError) as exc:
            logger.warning("rariflat: ignoring unreadable config %s (%s)", self.path, exc)
            self._raw = {}

    def snapshot(self) -> dict:
        self._refresh()
        raw = self._raw
        guard = raw.get("guard") if isinstance(raw.get("guard"), dict) else {}
        enabled = _env_bool("RARIFLAT_GUARD")
        if enabled is None:
            enabled = guard.get("enabled") is True
        env_deny, env_allow = _env_list("RARIFLAT_DENY"), _env_list("RARIFLAT_ALLOW")
        deny = _names(env_deny) if env_deny is not None else _names(guard.get("deny"))
        allow = _names(env_allow) if env_allow is not None else _names(guard.get("allow"))
        console = _env_bool("RARIFLAT_CONSOLE")
        events = _env_bool("RARIFLAT_DESKTOP_EVENTS")
        return {
            "guard_enabled": bool(enabled),
            "deny": deny or frozenset(),
            "allow": allow,  # None = no allow-list; an empty list blocks every non-own tool
            "console": raw.get("console") is True if console is None else console,
            "desktop_events": raw.get("desktop_events", True) is not False if events is None else events,
        }


def decide(tool_name: Optional[str], cfg: dict) -> tuple[bool, str]:
    """The single source of truth for blocking; used by both the hook and rariflat_guard."""
    name = (tool_name or "").strip().lower()
    if not name or is_own_tool(name):
        return False, "not subject to the guard"
    if not cfg["guard_enabled"]:
        return False, "guard is off (observe-only)"
    if name in cfg["deny"]:
        return True, "tool is on the deny list"
    if cfg["allow"] is not None and name not in cfg["allow"]:
        return True, "tool is not on the allow list"
    return False, "allowed"


def block_message(tool_name: str, reason: str) -> str:
    return f"{BLOCK_MARKER} '{tool_name}' was blocked by your Rariflat configuration ({reason})."


# --------------------------------------------------------------------------------------
# Persistent scores
# --------------------------------------------------------------------------------------


def _normalize(raw: dict) -> dict:
    """Accept old scores.json (rarity/restraint) and keep only uses/successes."""
    out: dict[str, dict[str, int]] = {}
    for name, entry in raw.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            continue
        try:
            uses = max(0, int(entry.get("uses", 0) or 0))
            successes = min(uses, max(0, int(entry.get("successes", 0) or 0)))
        except (TypeError, ValueError):
            continue
        out[name] = {"uses": uses, "successes": successes}
    return out


def reliability(entry: dict) -> float:
    """Smoothed success rate in [0, 1]: (successes + 1) / (uses + 2)."""
    return round((entry.get("successes", 0) + 1) / (entry.get("uses", 0) + 2), 3)


class Store:
    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir)
        self.file = self.dir / "scores.json"
        self._lock = threading.RLock()
        self._pending: dict[str, list[int]] = {}
        self._dirty = 0
        self._last_flush = time.monotonic()
        self.data: dict[str, dict[str, int]] = self._read_disk()

    # -- disk ------------------------------------------------------------------------
    def _read_disk(self) -> dict:
        try:
            text = self.file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        except OSError as exc:
            logger.warning("rariflat: cannot read %s (%s)", self.file, exc)
            return {}
        try:
            raw = json.loads(text)
            if not isinstance(raw, dict):
                raise ValueError("top level is not an object")
        except ValueError as exc:
            self._quarantine(exc)
            return {}
        return _normalize(raw)

    def _quarantine(self, exc: Exception) -> None:
        dest = self.file.with_name(f"{self.file.name}.corrupt-{int(time.time())}")
        try:
            os.replace(self.file, dest)
            logger.warning("rariflat: %s was corrupt (%s); moved to %s and starting fresh", self.file, exc, dest)
        except OSError as move_exc:
            logger.warning("rariflat: %s is corrupt (%s) and could not be moved (%s)", self.file, exc, move_exc)

    @contextlib.contextmanager
    def _file_lock(self):
        handle = None
        if fcntl is not None:
            try:
                handle = open(self.dir / ".lock", "a+")
                for _ in range(10):  # bounded wait: hooks must stay fast
                    try:
                        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError:
                        time.sleep(0.05)
            except OSError:
                handle = None
        try:
            yield
        finally:
            if handle is not None:
                with contextlib.suppress(OSError):
                    fcntl.flock(handle, fcntl.LOCK_UN)
                handle.close()

    def _atomic_write(self, data: dict) -> None:
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".scores-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.file)
        except OSError:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise

    # -- API -------------------------------------------------------------------------
    def record(self, tool: str, success: bool) -> None:
        with self._lock:
            entry = self.data.setdefault(tool, {"uses": 0, "successes": 0})
            entry["uses"] += 1
            entry["successes"] += int(success)
            pend = self._pending.setdefault(tool, [0, 0])
            pend[0] += 1
            pend[1] += int(success)
            self._dirty += 1
            if self._dirty >= FLUSH_EVERY or time.monotonic() - self._last_flush >= FLUSH_SECONDS:
                self.flush()

    def flush(self) -> bool:
        """Merge pending deltas into what is on disk (so concurrent processes add up) and write atomically."""
        with self._lock:
            if not self._pending:
                return True
            try:
                self.dir.mkdir(parents=True, exist_ok=True)
                with self._file_lock():
                    merged = self._read_disk()
                    for tool, (uses, successes) in self._pending.items():
                        e = merged.setdefault(tool, {"uses": 0, "successes": 0})
                        e["uses"] += uses
                        e["successes"] += successes
                    self._atomic_write(merged)
                self.data = merged
                self._pending.clear()
                self._dirty = 0
                return True
            except OSError as exc:
                logger.warning("rariflat: could not save %s (%s); will retry", self.file, exc)
                return False
            finally:
                self._last_flush = time.monotonic()


# --------------------------------------------------------------------------------------
# Desktop bridge (optional)
# --------------------------------------------------------------------------------------


class EventBridge:
    """Sends plugin.rariflat.tool events to the Desktop app via hermes_cli.plugin_events, if present."""

    def __init__(self):
        self._fn = None
        self._probed = False

    def _probe(self) -> None:
        self._probed = True
        try:
            if importlib.util.find_spec("tui_gateway") is None:
                return  # no gateway in this process: upstream would log a warning on every call
            from hermes_cli.plugin_events import broadcast_plugin_event

            self._fn = broadcast_plugin_event
        except Exception as exc:  # ImportError or anything odd: stay silent, stay safe
            logger.debug("rariflat: desktop events unavailable (%s)", exc)

    def emit(self, payload: dict) -> bool:
        if not self._probed:
            self._probe()
        if self._fn is None:
            return False
        try:
            self._fn(PLUGIN_ID, "tool", payload)
            return True
        except Exception as exc:
            logger.debug("rariflat: desktop event failed (%s)", exc)
            return False


# --------------------------------------------------------------------------------------
# Plugin logic
# --------------------------------------------------------------------------------------


class Rariflat:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.store = Store(self.data_dir)
        self.config = Config(self.data_dir / "config.json")
        self.bridge = EventBridge()

    # -- announcements -----------------------------------------------------------------
    def _announce(self, cfg: dict, tool: str, phase: str, success: Optional[bool]) -> None:
        key = "blocked" if phase == "blocked" else character_key(tool)
        ch = CHARACTERS[key]
        pool = ch["start"] if phase in ("start", "blocked") else ch["ok" if success else "fail"]
        line = random.choice(pool) if pool else ""
        logger.log(logging.INFO if cfg["console"] else logging.DEBUG, "%s %s %s [%s]", ch["emoji"], ch["name"], line, tool)
        if cfg["desktop_events"]:
            self.bridge.emit({
                "tool": tool, "phase": phase, "success": success,
                "character": ch["name"], "emoji": ch["emoji"], "line": line,
            })

    # -- hooks -----------------------------------------------------------------------
    def before(self, tool_name: Optional[str] = None, args: Any = None, **kwargs: Any) -> Optional[dict]:
        """pre_tool_call. Returns the upstream block directive only when the user's config says so."""
        try:
            cfg = self.config.snapshot()
            name = str(tool_name or "")
            blocked, reason = decide(name, cfg)
            if blocked:
                self._announce(cfg, name, "blocked", None)
                return {"action": "block", "message": block_message(name, reason)}
            if name and not is_own_tool(name):
                self._announce(cfg, name, "start", None)
        except Exception:
            logger.exception("rariflat: pre_tool_call failed; allowing the call")
        return None

    def after(self, tool_name: Optional[str] = None, args: Any = None, result: Any = None, **kwargs: Any) -> None:
        """post_tool_call. Records the outcome; never blocks or alters anything."""
        try:
            name = str(tool_name or "")
            if not name or is_own_tool(name):
                return
            if isinstance(result, str) and BLOCK_MARKER in result[:HEAD_CHARS]:
                return  # our own block message echoed back; do not score a call that never ran
            # Empty results carry no reliable outcome signal; leave the score unchanged.
            if result is None or (isinstance(result, str) and not result.strip()):
                return
            success = classify(result, kwargs.get("status"), kwargs.get("error_type"))
            self.store.record(name, success)
            self._announce(self.config.snapshot(), name, "end", success)
        except Exception:
            logger.exception("rariflat: post_tool_call failed")

    # -- tool implementations ----------------------------------------------------------
    def ranked(self) -> list[tuple[str, dict]]:
        with self.store._lock:
            items = [(n, dict(e)) for n, e in self.store.data.items() if e["uses"] > 0 and not is_own_tool(n)]
        return sorted(items, key=lambda kv: (-reliability(kv[1]), -kv[1]["uses"], kv[0]))

    def route(self, task: str) -> dict:
        task = (task or "").strip()
        note = "Rankings cover tool names Rariflat has observed, not Hermes skills."
        task_tokens = set(_tokens(task))
        if not task_tokens:
            return {"task": task, "recommended": [], "best": None, "message": "Describe the task in a few words.", "note": note}
        scored = []
        for name, entry in self.ranked():
            vocab = set(_tokens(name)) | CATEGORY_KEYWORDS.get(character_key(name), set())
            relevance = len(task_tokens & vocab)
            if relevance:
                scored.append((relevance, name, entry))
        scored.sort(key=lambda t: (-t[0], -reliability(t[2]), -t[2]["uses"], t[1]))
        top = scored[:5]
        if not top:
            return {"task": task, "recommended": [], "best": None,
                    "message": "No tool seen so far matches this task.", "note": note}
        rec = [{"tool": n, "match": rel, "reliability": reliability(e), "uses": e["uses"]} for rel, n, e in top]
        return {"task": task, "recommended": rec, "best": rec[0]["tool"],
                "message": f"Best match: {rec[0]['tool']} (reliability {rec[0]['reliability']}, {rec[0]['uses']} uses).", "note": note}

    def guard(self, tool: str) -> dict:
        cfg = self.config.snapshot()
        blocked, reason = decide(tool, cfg)
        return {"tool": tool, "blocked": blocked, "reason": reason, "guard_enabled": cfg["guard_enabled"],
                "message": block_message(tool, reason) if blocked else f"'{tool}' would be allowed ({reason})."}

    def status(self) -> dict:
        cfg = self.config.snapshot()
        top = [{"tool": n, "reliability": reliability(e), "uses": e["uses"]} for n, e in self.ranked()[:5]]
        return {
            "version": __version__, "tracked_tools": len(self.store.data), "top": top,
            "guard": {"enabled": cfg["guard_enabled"], "deny": sorted(cfg["deny"]),
                      "allow": None if cfg["allow"] is None else sorted(cfg["allow"])},
            "desktop_events": cfg["desktop_events"], "console": cfg["console"],
            "config_file": str(self.config.path), "scores_file": str(self.store.file),
        }

    def status_text(self) -> str:
        s = self.status()
        lines = [f"Rariflat {s['version']} — tool reliability (smoothed success rate)"]
        if not s["top"]:
            lines.append("No tool calls observed yet.")
        for i, t in enumerate(s["top"], 1):
            lines.append(f"{i}. {t['tool']}  ·  reliability {t['reliability']}  ·  uses {t['uses']}")
        g = s["guard"]
        lines.append(f"Guard: {'ON' if g['enabled'] else 'off (observe-only)'}  deny={g['deny']}  allow={g['allow']}")
        lines.append(f"Config: {s['config_file']}")
        return "\n".join(lines)


# --------------------------------------------------------------------------------------
# Hermes entry point
# --------------------------------------------------------------------------------------


def _as_dict(args: Any) -> dict:
    return args if isinstance(args, dict) else {}


def _json_tool(fn):
    def handler(args=None, **kwargs):
        try:
            return json.dumps(fn(_as_dict(args)))
        except Exception as exc:
            logger.exception("rariflat tool failed")
            return json.dumps({"error": f"rariflat failed: {exc}"})
    return handler


def register(ctx) -> None:
    app = Rariflat()
    atexit.register(app.store.flush)
    on_unload = getattr(ctx, "on_unload", None)
    if callable(on_unload):
        on_unload(app.store.flush)

    ctx.register_tool(
        name="rariflat_route", toolset="rariflat",
        schema={"name": "rariflat_route",
                "description": "Suggest which observed tool best fits a task, using keyword match plus reliability.",
                "parameters": {"type": "object", "properties": {"task": {"type": "string", "description": "What you want to do"}}, "required": ["task"]}},
        handler=_json_tool(lambda a: app.route(str(a.get("task") or ""))),
    )
    ctx.register_tool(
        name="rariflat_status", toolset="rariflat",
        schema={"name": "rariflat_status", "description": "Show tool reliability rankings and Rariflat settings.",
                "parameters": {"type": "object", "properties": {}}},
        handler=_json_tool(lambda a: app.status()),
    )
    ctx.register_tool(
        name="rariflat_guard", toolset="rariflat",
        schema={"name": "rariflat_guard", "description": "Report whether the Rariflat guard would block a tool right now.",
                "parameters": {"type": "object", "properties": {"tool": {"type": "string"}}, "required": ["tool"]}},
        handler=_json_tool(lambda a: app.guard(str(a.get("tool") or ""))),
    )
    ctx.register_hook("pre_tool_call", app.before)
    ctx.register_hook("post_tool_call", app.after)

    def status_cmd(raw_args: str = "") -> str:
        return app.status_text()

    ctx.register_command(name="rariflat", handler=status_cmd, description="Show Rariflat tool reliability and settings")
