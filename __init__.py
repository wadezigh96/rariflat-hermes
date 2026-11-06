"""Rariflat — Visual Agent Status + Multi-Agent Router for Hermes."""

import json
import random
from pathlib import Path

DATA_DIR = Path.home() / ".hermes" / "plugin-data" / "rariflat"
SCORES_FILE = DATA_DIR / "scores.json"

CHARACTERS = {
    "web": {
        "name": "Owl",
        "emoji": "🦉",
        "awaken": ["opens its eyes and scans the horizon", "tilts its head, listening for signals", "spreads its wings over the search"],
        "success": ["hoots softly — knowledge found", "lands with a scroll in its talons", "nods wisely"],
        "fail": ["ruffles its feathers in frustration", "circles once more, then perches"],
    },
    "search": {
        "name": "Owl",
        "emoji": "🦉",
        "awaken": ["hunts for knowledge in the dark", "locks onto a faint trail"],
        "success": ["returns with what it sought", "shares a quiet hoot of victory"],
        "fail": ["the trail goes cold", "returns empty-taloned"],
    },
    "browser": {
        "name": "Scout",
        "emoji": "🔍",
        "awaken": ["steps into the unknown", "maps the path ahead"],
        "success": ["marks the territory", "reports back with findings"],
        "fail": ["the path is blocked", "retreats to regroup"],
    },
    "terminal": {
        "name": "Hephaestus",
        "emoji": "⚒️",
        "awaken": ["stokes the forge", "raises the hammer", "sparks fly as the anvil heats"],
        "success": ["strikes true — the command is forged", "quenches the blade with a satisfied grunt"],
        "fail": ["the metal cracks", "sets the hammer down, muttering"],
    },
    "code": {
        "name": "Hephaestus",
        "emoji": "⚒️",
        "awaken": ["shapes the code on the anvil", "measures twice"],
        "success": ["the artifact takes form", "admires the work"],
        "fail": ["the form collapses", "starts over with fresh metal"],
    },
    "file": {
        "name": "Archivist",
        "emoji": "📜",
        "awaken": ["unrolls an ancient scroll", "dusts off the shelves"],
        "success": ["files the knowledge precisely", "seals the archive"],
        "fail": ["the page is missing", "searches the stacks again"],
    },
    "memory": {
        "name": "Mnemosyne",
        "emoji": "🧠",
        "awaken": ["stirs the waters of memory", "reaches into the past"],
        "success": ["the memory surfaces clearly", "weaves it into the present"],
        "fail": ["the memory slips away", "the waters grow still"],
    },
    "skills": {
        "name": "Mentor",
        "emoji": "🎓",
        "awaken": ["opens the lesson", "gestures for attention"],
        "success": ["the student understands", "nods with quiet pride"],
        "fail": ["the lesson needs repeating", "tries another approach"],
    },
    "image": {
        "name": "Muse",
        "emoji": "🎨",
        "awaken": ["dips the brush", "studies the blank canvas"],
        "success": ["the vision appears", "steps back to admire"],
        "fail": ["the colors run", "scrapes the canvas clean"],
    },
    "vision": {
        "name": "Seer",
        "emoji": "👁️",
        "awaken": ["opens the third eye", "gazes beyond the veil"],
        "success": ["the truth is revealed", "the vision clears"],
        "fail": ["the veil thickens", "blinks and tries again"],
    },
    "tts": {
        "name": "Bard",
        "emoji": "🎵",
        "awaken": ["tunes the instrument", "clears the throat"],
        "success": ["the song carries", "the last note hangs in the air"],
        "fail": ["a string snaps", "retunes quietly"],
    },
    "error": {
        "name": "Cerberus",
        "emoji": "🐾",
        "awaken": ["all three heads rise", "growls low"],
        "success": ["the threat is contained", "one head settles"],
        "fail": ["the guardians bark in warning", "the gate holds"],
    },
    "default": {
        "name": "Hermes",
        "emoji": "🚀",
        "awaken": ["laces the winged sandals", "checks the caduceus"],
        "success": ["delivers the message", "already moving to the next"],
        "fail": ["the wind shifts", "adjusts course"],
    },
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
        s["rarity"] = min(100, s.get("rarity", 50) + 2)
    else:
        s["rarity"] = max(10, s.get("rarity", 50) - 3)
    if restrained:
        s["restraint"] = min(100, s.get("restraint", 50) + 6)
    else:
        s["restraint"] = max(15, s.get("restraint", 50) - 1)
    _save_scores(_scores)

def register(ctx):
    def route_skills(args, **kwargs):
        task = (args.get("task") or "").strip()
        ranked = sorted(
            _scores.items(),
            key=lambda x: (x[1].get("rarity", 50) * 0.55 + x[1].get("restraint", 50) * 0.45),
            reverse=True,
        )[:5]
        if not ranked:
            ranked = [("explore", {"rarity": 72, "restraint": 80, "uses": 0, "successes": 0})]
        top = ranked[0]
        result = {
            "task": task,
            "recommended": [
                {
                    "skill": name,
                    "rarity": data.get("rarity", 50),
                    "restraint": data.get("restraint", 50),
                    "uses": data.get("uses", 0),
                }
                for name, data in ranked
            ],
            "message": f"Rariflat routes to {top[0]} (rarity {top[1].get('rarity', 50)}, restraint {top[1].get('restraint', 50)}).",
        }
        return json.dumps(result)

    def get_status(args, **kwargs):
        top = sorted(_scores.items(), key=lambda x: x[1].get("rarity", 0), reverse=True)[:5]
        return json.dumps(
            {
                "characters_active": True,
                "tracked_tools": len(_scores),
                "top_skills": [
                    {
                        "name": n,
                        "rarity": d.get("rarity", 50),
                        "restraint": d.get("restraint", 50),
                        "uses": d.get("uses", 0),
                    }
                    for n, d in top
                ],
            }
        )

    ctx.register_tool(
        name="rariflat_route",
        toolset="rariflat",
        schema={
            "name": "rariflat_route",
            "description": "Route a task to the best skill based on rarity and restraint scores.",
            "parameters": {
                "type": "object",
                "properties": {"task": {"type": "string", "description": "The task to route"}},
                "required": ["task"],
            },
        },
        handler=route_skills,
    )

    ctx.register_tool(
        name="rariflat_status",
        toolset="rariflat",
        schema={
            "name": "rariflat_status",
            "description": "Get current Rariflat visual status and skill scores.",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=get_status,
    )

    def on_pre_tool(tool_name, args, **kwargs):
        char = _get_character(tool_name)
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
        top = sorted(_scores.items(), key=lambda x: x[1].get("rarity", 0), reverse=True)[:5]
        lines = ["Rariflat — Skill Rankings"]
        if not top:
            lines.append("No tools tracked yet. Make some calls!")
        else:
            for i, (name, data) in enumerate(top, 1):
                lines.append(
                    f"{i}. {name}  ·  rarity {data.get('rarity', 50)}  ·  restraint {data.get('restraint', 50)}  ·  uses {data.get('uses', 0)}"
                )
        return "\n".join(lines)

    ctx.register_command(
        name="rariflat",
        handler=status_cmd,
        description="Show Rariflat skill rankings and status",
    )
