"""Dev-time asset generator.

Writes:
  assets/tiles/tileset.png  - terrain tiles plus 16 autotiled fence tiles
  data/farm_map.json        - 80x60 starter map in Tiled JSON format

Run once from the project root:  python tools/generate_assets.py
Re-run any time to regenerate; edit farm_map.json in Tiled afterward.
"""

import json
import os

import pygame

TILE = 16
MAP_W, MAP_H = 80, 60

# Local tile ids (gid = id + 1 in the map data).
GRASS, DIRT, FIELD, STONE = range(4)
# Fence autotile tiles live at ids 4..19: id = FENCE_BASE + mask,
# where mask bits are L=1, R=2, U=4, D=8 (which neighbors are fence).
FENCE_BASE = 4
FENCE_COUNT = 16
TILESET_COLS = FENCE_BASE + FENCE_COUNT

# Frame order inside fence_parts.png: LEFT, RIGHT, UP, DOWN.
# Listed in draw order, back to front: UP (behind), sides, DOWN (in front).
FENCE_PARTS = [(4, 2), (1, 0), (2, 1), (8, 3)]  # (mask bit, frame index)


def make_tileset(path):
    grass = pygame.image.load("assets/tiles/grass.png")
    parts = pygame.image.load("assets/tiles/fence_parts_v2.png")
    sheet = pygame.Surface((TILE * TILESET_COLS, TILE), pygame.SRCALPHA)

    sheet.blit(grass, (GRASS * TILE, 0))

    dirt = pygame.image.load("assets/tiles/dirt.png")
    sheet.blit(dirt, (DIRT * TILE, 0))

    for mask in range(FENCE_COUNT):
        tile = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        for bit, frame in FENCE_PARTS:
            if mask & bit or (mask == 0 and bit in (1, 2)):
                tile.blit(parts, (0, 0), (frame * TILE, 0, TILE, TILE))
        sheet.blit(tile, ((FENCE_BASE + mask) * TILE, 0))

    field = pygame.Surface((TILE, TILE))
    field.fill((95, 65, 38))
    for y in (3, 8, 13):
        field.fill((70, 45, 25), (0, y, TILE, 2))
    sheet.blit(field, (FIELD * TILE, 0))

    stone = pygame.Surface((TILE, TILE))
    stone.fill((130, 130, 138))
    stone.fill((105, 105, 112), (0, 0, TILE, 1))
    stone.fill((105, 105, 112), (0, 0, 1, TILE))
    sheet.blit(stone, (STONE * TILE, 0))

    pygame.image.save(sheet, path)


def generate_map(path):
    gid = lambda t: t + 1
    # Two layers: opaque terrain on "ground", fences (which have
    # transparent gaps between rails) composited on an overlay layer.
    ground = [gid(GRASS)] * (MAP_W * MAP_H)
    overlay = [0] * (MAP_W * MAP_H)

    def fill(x, y, w, h, tile):
        for ty in range(y, y + h):
            for tx in range(x, x + w):
                if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                    ground[ty * MAP_W + tx] = gid(tile)

    # Stamp the horizontal fence variant everywhere; the loader's
    # autotile pass recomputes each cell's real mask from its neighbors.
    fence_gid = gid(FENCE_BASE + 3)

    def hfence(x0, x1, y, gaps=()):
        for x in range(x0, x1 + 1):
            if x not in gaps:
                overlay[y * MAP_W + x] = fence_gid

    def vfence(y0, y1, x, gaps=()):
        for y in range(y0, y1 + 1):
            if y not in gaps:
                overlay[y * MAP_W + x] = fence_gid

    # Perimeter fence; entrance gap in the bottom edge.
    hfence(0, MAP_W - 1, 0)
    hfence(0, MAP_W - 1, MAP_H - 1, gaps=(38, 39, 40, 41))
    vfence(0, MAP_H - 1, 0)
    vfence(0, MAP_H - 1, MAP_W - 1)

    # Orchard / crop fields (top zone).
    fill(8, 4, 18, 10, FIELD)
    fill(54, 4, 18, 10, FIELD)

    # Windmill hill: bare dirt rise.
    fill(34, 6, 12, 8, DIRT)

    # Mid-map fence separating field from the yard; gate gap on the path.
    hfence(1, MAP_W - 2, 20, gaps=(38, 39, 40, 41))

    # Sheep pasture (right side): fenced paddock with a south gap.
    hfence(52, 71, 24)
    hfence(52, 71, 37, gaps=(58, 59, 60, 61))
    vfence(24, 37, 52)
    vfence(24, 37, 71)

    # Main north-south path: entrance -> yard -> gate -> windmill hill.
    fill(39, 14, 2, 45, DIRT)

    # Yard plaza in front of the gate.
    fill(28, 32, 24, 8, STONE)

    # East-west path across the yard.
    fill(8, 35, 64, 2, DIRT)

    # Branches: cowshed (west), barn (southwest), stables (southeast).
    fill(13, 25, 2, 10, DIRT)
    fill(13, 37, 2, 7, DIRT)
    fill(63, 37, 2, 9, DIRT)

    # Farmhouse approach continues south off the plaza.
    fill(39, 40, 2, 10, DIRT)

    tilesets = [{
        "columns": TILESET_COLS,
        "firstgid": 1,
        "image": "../assets/tiles/tileset.png",
        "imageheight": TILE,
        "imagewidth": TILE * TILESET_COLS,
        "margin": 0,
        "name": "tileset",
        "spacing": 0,
        "tilecount": TILESET_COLS,
        "tileheight": TILE,
        "tilewidth": TILE,
        "tiles": [{
            "id": FENCE_BASE + mask,
            "properties": [
                {"name": "solid", "type": "bool", "value": True},
                {"name": "autotile", "type": "string", "value": "fence"},
                {"name": "mask", "type": "int", "value": mask},
            ],
        } for mask in range(FENCE_COUNT)],
    }]

    tiled_map = {
        "compressionlevel": -1,
        "height": MAP_H,
        "infinite": False,
        "layers": [
            {
                "data": ground,
                "height": MAP_H,
                "id": 1,
                "name": "ground",
                "opacity": 1,
                "type": "tilelayer",
                "visible": True,
                "width": MAP_W,
                "x": 0,
                "y": 0,
            },
            {
                "data": overlay,
                "height": MAP_H,
                "id": 2,
                "name": "fences",
                "opacity": 1,
                "type": "tilelayer",
                "visible": True,
                "width": MAP_W,
                "x": 0,
                "y": 0,
            },
        ],
        "nextlayerid": 3,
        "nextobjectid": 1,
        "orientation": "orthogonal",
        "renderorder": "right-down",
        "tiledversion": "1.10.2",
        "tileheight": TILE,
        "tilesets": tilesets,
        "tilewidth": TILE,
        "type": "map",
        "version": "1.10",
        "width": MAP_W,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(tiled_map, f)


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pygame.init()
    make_tileset("assets/tiles/tileset.png")
    generate_map("data/farm_map.json")
    print("Wrote assets/tiles/tileset.png and data/farm_map.json")


if __name__ == "__main__":
    main()
