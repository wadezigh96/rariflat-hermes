"""Rariflat — Visual Agent Status + Intelligent Skill Router for Hermes."""

import json
import random
from pathlib import Path

DATA_DIR = Path.home() / ".hermes" / "plugin-data" / "rariflat"
SCORES_FILE = DATA_DIR / "scores.json"

CHARACTERS = {
    "web": {"name": "Owl", "emoji": "🦉", "awaken": ["opens its eyes and scans the horizon", "tilts its head, listening for signals"], "success": ["hoots softly — knowledge found", "lands with a scroll in its talons"], "fail": ["ruffles its feathers in frustration", "the trail goes cold"]},
    "search": {"name": "Owl", "emoji": "🦉", "awaken": ["hunts for knowledge in the dark"], "success": ["returns with what it sought"], "fail": ["returns empty-taloned"]},
    "browser": {"name": "Scout", "emoji": "🔍", "awaken": ["steps into the unknown", "maps the path ahead"], "success": ["marks the territory"], "fail": ["the path is blocked"]},
    "terminal": {"name": "Hephaestus", "emoji": "⚒️", "awaken": ["stokes the forge", "raises the hammer"], "success": ["strikes true — the command is forged"], "fail": ["the metal cracks"]},
    "code": {"name": "Hephaestus", "emoji": "⚒️", "awaken": ["shapes the code on the anvil"], "success": ["the artifact takes form"], "fail": ["the form collapses"]},
    "file": {"name": "Archivist", "emoji": "📜", "awaken": ["unrolls an ancient scroll"], "success": ["files the knowledge precisely"], "fail": ["the page is missing"]},
    "memory": {"name": "Mnemosyne", "emoji": "🧠", "awaken": ["stirs the waters of memory"], "success": ["the memory surfaces clearly"], "fail": ["the memory slips away"]},
    "skills": {"name": "Mentor", "emoji": "🎓", "awaken": ["opens the lesson"], "success": ["the student understands"], "fail": ["the lesson needs repeating"]},
    "image": {"name": "Muse", "emoji": "🎨", "awaken": ["dips the brush"], "success": ["the vision appears"], "fail": ["the colors run"]},
    "vision": {"name": "Seer", "emoji": "👁️", "awaken": ["opens the third eye"], "success": ["the truth is revealed"], "fail": ["the veil thickens"]},
    "tts": {"name": "Bard", "emoji": "🎵", "awaken": ["tunes the instrument"], "success": ["the song carries"], "fail": ["a string snaps"]},
    "error": {"name": "Cerberus", "emoji": "🐾", "awaken": ["all three heads rise"], "success": ["the threat is contained"], "fail": ["the guardians bark in warning"]},
    "default": {"name": "Hermes", "emoji": "🚀", "awaken": ["laces the winged sandals"], "success": ["delivers the message"], "fail": ["the wind shifts"]},
}

def _load_scores():
    try:
        if SCORES_FILE.exists():
            return json.loads(SCORES_FILE.read_text())
    except Exception:
        pass
    return {}

def _save_scores(scores):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SCORES_FILE.write_text(json.dumps(scores, indent=2))
    except Exception:
        pass

_scores = _load_scores()

def _get_character(tool_name: str) -> dict:
    name = (tool_name or "").lower()
    for key, char in CHARACTERS.items():
        if key in name:
            return char
    return CHARACTERS["default"]

def _pick(lst):
    return random.choice(lst) if lst else ""

def _update_scores(tool_name: str, success: bool, restrained: bool = False):
    if tool_name not in _scores:
        _scores[tool_name] = {"rarity": 50, "restraint": 50, "uses": 0, "successes": 0}
    s = _scores[tool_name]
    s["uses"] = s.get("uses", 0) + 1
    if success:
        s["successes"] = s.get("successes", 0) + 1
        s["rarity"] = min(100, s.get("rarity", 50) + 3)
    else:
        s["rarity"] = max(5, s.get("rarity", 50) - 4)
    if restrained:
        s["restraint"] = min(100, s.get("restraint", 50) + 8)
    else:
        s["restraint"] = max(10, s.get("restraint", 50) - 2)
    _save_scores(_scores)

def _rank_skills():
    return sorted(
        _scores.items(),
        key=lambda x: (x[1].get("rarity", 50) * 0.5 + x[1].get("restraint", 50) * 0.5),
        reverse=True,
    )

def register(ctx):
    def route_skills(args, **kwargs):
        task = (args.get("task") or "").strip()
        ranked = _rank_skills()[:5]
        if not ranked:
            ranked = [("explore", {"rarity": 75, "restraint": 85, "uses": 0})]
        top = ranked[0]
        result = {
            "task": task,
            "recommended": [
                {"skill": n, "rarity": d.get("rarity", 50), "restraint": d.get("restraint", 50), "uses": d.get("uses", 0)}
                for n, d in ranked
            ],
            "best": top[0],
            "message": f"Rariflat recommends {top[0]} (rarity {top[1].get('rarity', 50)}, restraint {top[1].get('restraint', 50)}).",
        }
        return json.dumps(result)

    def get_status(args, **kwargs):
        top = _rank_skills()[:5]
        return json.dumps({
            "characters_active": True,
            "tracked_tools": len(_scores),
            "top_skills": [{"name": n, "rarity": d.get("rarity", 50), "restraint": d.get("restraint", 50), "uses": d.get("uses", 0)} for n, d in top],
        })

    def guard_check(args, **kwargs):
        tool = args.get("tool", "")
        data = _scores.get(tool, {"restraint": 50})
        restraint = data.get("restraint", 50)
        blocked = restraint < 25
        return json.dumps({
            "tool": tool,
            "restraint": restraint,
            "blocked": blocked,
            "message": f"Cerberus blocks {tool} (restraint {restraint})." if blocked else f"{tool} is allowed (restraint {restraint}).",
        })

    ctx.register_tool(
        name="rariflat_route",
        toolset="rariflat",
        schema={"name": "rariflat_route", "description": "Recommend the best skill for a task based on rarity and restraint scores.", "parameters": {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]}},
        handler=route_skills,
    )
    ctx.register_tool(
        name="rariflat_status",
        toolset="rariflat",
        schema={"name": "rariflat_status", "description": "Get current skill rankings and character status.", "parameters": {"type": "object", "properties": {}}},
        handler=get_status,
    )
    ctx.register_tool(
        name="rariflat_guard",
        toolset="rariflat",
        schema={"name": "rariflat_guard", "description": "Check if a tool should be blocked due to low restraint.", "parameters": {"type": "object", "properties": {"tool": {"type": "string"}}, "required": ["tool"]}},
        handler=guard_check,
    )

    def on_pre_tool(tool_name, args, **kwargs):
        char = _get_character(tool_name)
        data = _scores.get(tool_name, {})
        restraint = data.get("restraint", 50)
        if restraint < 25:
            print(f"[Rariflat] 🐾 Cerberus blocks {tool_name} (restraint {restraint}).")
            return {"blocked": True, "reason": f"Low restraint ({restraint})"}
        line = _pick(char.get("awaken", ["awakens"]))
        print(f"[Rariflat] {char['emoji']} {char['name']} {line}...")
        return None

    def on_post_tool(tool_name, args, result, **kwargs):
        char = _get_character(tool_name)
        text = str(result or "").lower()
        success = bool(result) and "error" not in text and "fail" not in text
        restrained = any(w in text for w in ("blocked", "denied", "restrain", "refuse"))
        _update_scores(tool_name, success, restrained)
        reactions = char.get("success" if success else "fail", ["finishes"])
        line = _pick(reactions)
        print(f"[Rariflat] {char['emoji']} {char['name']} {line}.")
        return None

    ctx.register_hook("pre_tool_call", on_pre_tool)
    ctx.register_hook("post_tool_call", on_post_tool)

    def status_cmd(raw_args, **kwargs):
        ranked = _rank_skills()[:5]
        lines = ["Rariflat — Skill Rankings (rarity + restraint)"]
        if not ranked:
            lines.append("No tools tracked yet. Make some calls!")
        else:
            for i, (name, data) in enumerate(ranked, 1):
                lines.append(f"{i}. {name}  ·  rarity {data.get('rarity', 50)}  ·  restraint {data.get('restraint', 50)}  ·  uses {data.get('uses', 0)}")
        return "\n".join(lines)

    ctx.register_command(name="rariflat", handler=status_cmd, description="Show Rariflat skill rankings")
