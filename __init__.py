"""Rariflat — Visual Agent Status + Multi-Agent Router for Hermes."""

import json
import random
from pathlib import Path

CHARACTERS = {
    "web": {
        "name": "Owl",
        "emoji": "🦉",
        "awaken": ["opens its eyes and scans the horizon", "tilts its head, listening for signals", "spreads its wings over the search"],
        "success": ["hoots softly — knowledge found", "lands with a scroll in its talons", "nods wisely"],
        "fail": ["ruffles its feathers in frustration", "circles once more, then perches"],
        "color": "blue",
    },
    "search": {
        "name": "Owl",
        "emoji": "🦉",
        "awaken": ["hunts for knowledge in the dark", "locks onto a faint trail"],
        "success": ["returns with what it sought", "shares a quiet hoot of victory"],
        "fail": ["the trail goes cold", "returns empty-taloned"],
        "color": "blue",
    },
    "browser": {
        "name": "Scout",
        "emoji": "🔍",
        "awaken": ["steps into the unknown", "maps the path ahead"],
        "success": ["marks the territory", "reports back with findings"],
        "fail": ["the path is blocked", "retreats to regroup"],
        "color": "cyan",
    },
    "terminal": {
        "name": "Hephaestus",
        "emoji": "⚒️",
        "awaken": ["stokes the forge", "raises the hammer", "sparks fly as the anvil heats"],
        "success": ["strikes true — the command is forged", "quenches the blade with a satisfied grunt"],
        "fail": ["the metal cracks", "sets the hammer down, muttering"],
        "color": "orange",
    },
    "code": {
        "name": "Hephaestus",
        "emoji": "⚒️",
        "awaken": ["shapes the code on the anvil", "measures twice"],
        "success": ["the artifact takes form", "admires the work"],
        "fail": ["the form collapses", "starts over with fresh metal"],
        "color": "orange",
    },
    "file": {
        "name": "Archivist",
        "emoji": "📜",
        "awaken": ["unrolls an ancient scroll", "dusts off the shelves"],
        "success": ["files the knowledge precisely", "seals the archive"],
        "fail": ["the page is missing", "searches the stacks again"],
        "color": "gold",
    },
    "memory": {
        "name": "Mnemosyne",
        "emoji": "🧠",
        "awaken": ["stirs the waters of memory", "reaches into the past"],
        "success": ["the memory surfaces clearly", "weaves it into the present"],
        "fail": ["the memory slips away", "the waters grow still"],
        "color": "purple",
    },
    "skills": {
        "name": "Mentor",
        "emoji": "🎓",
        "awaken": ["opens the lesson", "gestures for attention"],
        "success": ["the student understands", "nods with quiet pride"],
        "fail": ["the lesson needs repeating", "tries another approach"],
        "color": "green",
    },
    "image": {
        "name": "Muse",
        "emoji": "🎨",
        "awaken": ["dips the brush", "studies the blank canvas"],
        "success": ["the vision appears", "steps back to admire"],
        "fail": ["the colors run", "scrapes the canvas clean"],
        "color": "pink",
    },
    "vision": {
        "name": "Seer",
        "emoji": "👁️",
        "awaken": ["opens the third eye", "gazes beyond the veil"],
        "success": ["the truth is revealed", "the vision clears"],
        "fail": ["the veil thickens", "blinks and tries again"],
        "color": "indigo",
    },
    "tts": {
        "name": "Bard",
        "emoji": "🎵",
        "awaken": ["tunes the instrument", "clears the throat"],
        "success": ["the song carries", "the last note hangs in the air"],
        "fail": ["a string snaps", "retunes quietly"],
        "color": "yellow",
    },
    "error": {
        "name": "Cerberus",
        "emoji": "🐾",
        "awaken": ["all three heads rise", "growls low"],
        "success": ["the threat is contained", "one head settles"],
        "fail": ["the guardians bark in warning", "the gate holds"],
        "color": "red",
    },
    "default": {
        "name": "Hermes",
        "emoji": "🚀",
        "awaken": ["laces the winged sandals", "checks the caduceus"],
        "success": ["delivers the message", "already moving to the next"],
        "fail": ["the wind shifts", "adjusts course"],
        "color": "green",
    },
}

_scores = {}

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
    s["uses"] += 1
    if success:
        s["successes"] += 1
        s["rarity"] = min(100, s["rarity"] + 2)
    else:
        s["rarity"] = max(10, s["rarity"] - 3)
    if restrained:
        s["restraint"] = min(100, s["restraint"] + 6)
    else:
        s["restraint"] = max(15, s["restraint"] - 1)

def register(ctx):
    def route_skills(args, **kwargs):
        task = args.get("task", "")
        ranked = sorted(
            _scores.items(),
            key=lambda x: (x[1]["rarity"] * 0.55 + x[1]["restraint"] * 0.45),
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
                    "rarity": data["rarity"],
                    "restraint": data["restraint"],
                    "uses": data["uses"],
                }
                for name, data in ranked
            ],
            "message": f"Rariflat routes to {top[0]} (rarity {top[1]['rarity']}, restraint {top[1]['restraint']}).",
        }
        return json.dumps(result)

    def get_status(args, **kwargs):
        top = sorted(_scores.items(), key=lambda x: x[1]["rarity"], reverse=True)[:5]
        return json.dumps(
            {
                "characters_active": True,
                "tracked_tools": len(_scores),
                "top_skills": [
                    {"name": n, "rarity": d["rarity"], "restraint": d["restraint"], "uses": d["uses"]}
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
        success = result and "error" not in text and "fail" not in text
        restrained = any(w in text for w in ("blocked", "denied", "restrain", "refuse"))
        _update_scores(tool_name, success, restrained)
        reactions = char.get("success" if success else "fail", ["finishes"])
        line = _pick(reactions)
        print(f"[Rariflat] {char['emoji']} {char['name']} {line}.")
        return None

    ctx.register_hook("pre_tool_call", on_pre_tool)
    ctx.register_hook("post_tool_call", on_post_tool)

    def status_cmd(raw_args, **kwargs):
        top = sorted(_scores.items(), key=lambda x: x[1]["rarity"], reverse=True)[:5]
        lines = ["Rariflat — Skill Rankings"]
        if not top:
            lines.append("No tools tracked yet. Make some calls!")
        else:
            for i, (name, data) in enumerate(top, 1):
                lines.append(
                    f"{i}. {name}  ·  rarity {data['rarity']}  ·  restraint {data['restraint']}  ·  uses {data['uses']}"
                )
        return "\n".join(lines)

    ctx.register_command(
        name="rariflat",
        handler=status_cmd,
        description="Show Rariflat skill rankings and status",
    )
