"""Interaction registry: maps a tile the player faces to an action.

Action types:
  dialogue      - {"type": "dialogue", "id": <id>, "speaker": <name>}
  commandments  - {"type": "commandments"}
  advance_phase - {"type": "advance_phase"}
  ending        - {"type": "ending"}
  message       - {"type": "message", "text": "..."}
"""


def build_registry(props, npcs):
    registry = {}
    for prop in props:
        for spec in prop.interact:
            action = {"type": spec["event"]}
            for key in ("id", "text"):
                if key in spec:
                    action[key] = spec[key]
            tiles = {tuple(t) for t in spec.get("tiles", [])}
            for tile in tiles or prop.solid_tiles:
                registry[tile] = action
    for npc in npcs:
        registry[(npc.tx, npc.ty)] = {
            "type": "dialogue",
            "id": npc.dialogue_id,
            "speaker": npc.name,
        }
    return registry
