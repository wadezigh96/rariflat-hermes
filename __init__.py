"""Rariflat — Visual Agent Status + Multi-Agent Router for Hermes."""

import json
import random
from pathlib import Path

# Character map: tool category → character that "wakes up"
CHARACTERS = {
    "web": {"name": "Owl", "emoji": "🦉", "action": "scans the horizon", "color": "blue"},
    "search": {"name": "Owl", "emoji": "🦉", "action": "hunts for knowledge", "color": "blue"},
    "browser": {"name": "Scout", "emoji": "🔍", "action": "explores the web", "color": "cyan"},
    "terminal": {"name": "Hephaestus", "emoji": "⚒️", "action": "forges commands", "color": "orange"},
    "code": {"name": "Hephaestus", "emoji": "⚒️", "action": "shapes the code", "color": "orange"},
    "file": {"name": "Archivist", "emoji": "📜", "action": "organizes the scrolls", "color": "gold"},
    "memory": {"name": "Mnemosyne", "emoji": "🧠", "action": "recalls the past", "color": "purple"},
    "skills": {"name": "Mentor", "emoji": "🎓", "action": "guides the path", "color": "green"},
    "image": {"name": "Muse", "emoji": "🎨", "action": "paints the vision", "color": "pink"},
    "vision": {"name": "Seer", "emoji": "👁️", "action": "sees beyond", "color": "indigo"},
    "tts": {"name": "Bard", "emoji": "🎵", "action": "sings the words", "color": "yellow"},
    "error": {"name": "Cerberus", "emoji": "🐾", "action": "guards against failure", "color": "red"},
    "default": {"name": "Hermes", "emoji": "🚀", "action": "moves swiftly", "color": "green"},
}

# Simple in-memory rarity & restraint scores (persisted lightly via file in real use)
_scores = {
    # skill/tool name → {rarity: 0-100, restraint: 0-100, uses: int}
}

def _get_character(tool_name: str) -> dict:
    name = (tool_name or "").lower()
    for key, char in CHARACTERS.items():
        if key in name:
            return char
    return CHARACTERS["default"]

def _update_scores(tool_name: str, success: bool, restrained: bool = False):
    if tool_name not in _scores:
        _scores[tool_name] = {"rarity": 50, "restraint": 50, "uses": 0}
    s = _scores[tool_name]
    s["uses"] += 1
    # Simple adaptive scoring
    if success:
        s["rarity"] = min(100, s["rarity"] + 2)
    else:
        s["rarity"] = max(10, s["rarity"] - 3)
    if restrained:
        s["restraint"] = min(100, s["restraint"] + 5)
    else:
        s["restraint"] = max(20, s["restraint"] - 1)

def register(ctx):
    # --- Tools ---
    def route_skills(args, **kwargs):
        task = args.get("task", "")
        # Rank available skills by rarity + restraint (demo data + live scores)
        ranked = sorted(
            _scores.items(),
            key=lambda x: (x[1]["rarity"] * 0.6 + x[1]["restraint"] * 0.4),
            reverse=True
        )[:5]
        if not ranked:
            ranked = [("default-skill", {"rarity": 70, "restraint": 80, "uses": 0})]
        result = {
            "task": task,
            "recommended": [
                {"skill": name, "rarity": data["rarity"], "restraint": data["restraint"]}
                for name, data in ranked
            ],
            "message": f"Routed by Rariflat. Top pick: {ranked[0][0]} (rarity {ranked[0][1]['rarity']}, restraint {ranked[0][1]['restraint']})"
        }
        return json.dumps(result)

    def get_status(args, **kwargs):
        return json.dumps({
            "characters_active": True,
            "tracked_tools": len(_scores),
            "top_skills": sorted(_scores.items(), key=lambda x: x[1]["rarity"], reverse=True)[:3]
        })

    ctx.register_tool(
        name="rariflat_route",
        toolset="rariflat",
        schema={
            "name": "rariflat_route",
            "description": "Route a task to the best skill based on rarity and restraint scores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The task to route"}
                },
                "required": ["task"]
            }
        },
        handler=route_skills,
    )

    ctx.register_tool(
        name="rariflat_status",
        toolset="rariflat",
        schema={
            "name": "rariflat_status",
            "description": "Get current Rariflat visual status and skill scores.",
            "parameters": {"type": "object", "properties": {}}
        },
        handler=get_status,
    )

    # --- Hooks for visual reactions ---
    def on_pre_tool(tool_name, args, **kwargs):
        char = _get_character(tool_name)
        # In a real Desktop integration this would emit to the pane
        print(f"[Rariflat] {char['emoji']} {char['name']} awakens — {char['action']}...")
        return None  # don't block

    def on_post_tool(tool_name, args, result, **kwargs):
        char = _get_character(tool_name)
        success = result and "error" not in str(result).lower()
        restrained = "blocked" in str(result).lower() or "denied" in str(result).lower()
        _update_scores(tool_name, success, restrained)
        reaction = "succeeds" if success else "stumbles"
        print(f"[Rariflat] {char['emoji']} {char['name']} {reaction}.")
        return None

    ctx.register_hook("pre_tool_call", on_pre_tool)
    ctx.register_hook("post_tool_call", on_post_tool)

    # --- Slash command ---
    def status_cmd(raw_args, **kwargs):
        top = sorted(_scores.items(), key=lambda x: x[1]["rarity"], reverse=True)[:3]
        lines = ["Rariflat Status"]
        for name, data in top:
            lines.append(f"• {name}: rarity {data['rarity']} | restraint {data['restraint']}")
        if not top:
            lines.append("No tools tracked yet. Make some calls!")
        return "\n".join(lines)

    ctx.register_command(
        name="rariflat",
        handler=status_cmd,
        description="Show Rariflat skill rankings and status",
    )
