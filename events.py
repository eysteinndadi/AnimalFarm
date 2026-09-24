"""Interaction registry: maps a tile the player faces to an action.

Action types:
  dialogue      - {"type": "dialogue", "id": <id>, "speaker": <name>}
  commandments  - {"type": "commandments"}
  advance_phase - {"type": "advance_phase", "text": ..., "question": ...}
                  (text and question optional; asks before moving on)
  ending        - {"type": "ending"}
  message       - {"type": "message", "text": "..."}
"""


def build_registry(props, npcs):
    registry = {}
    for prop in props:
        for spec in prop.interact:
            action = {"type": spec["event"]}
            for key in ("id", "text", "allegory", "question"):
                if key in spec:
                    action[key] = spec[key]
            tiles = {tuple(t) for t in spec.get("tiles", [])}
            for tile in tiles or prop.solid_tiles:
                registry[tile] = action
    for npc in npcs:
        if npc.mobile:
            continue  # checked by live position in Game._interact
        for tile in npc.solid_tiles:
            registry[tile] = {
                "type": "dialogue",
                "id": npc.dialogue_id,
                "speaker": npc.name,
            }
    return registry
