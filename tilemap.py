import os

import pygame

import assets

TILE_SIZE = 16


class TileMap:
    """Loads a Tiled JSON-exported map.

    Terrain is prerendered once into a single surface; entities and
    tall objects are drawn separately in the y-sorted pass.
    """

    def __init__(self, path):
        doc = assets.load_json(path)
        base = os.path.dirname(path)

        self.width = doc["width"]
        self.height = doc["height"]
        self.pixel_width = self.width * TILE_SIZE
        self.pixel_height = self.height * TILE_SIZE

        self._tiles = {}   # gid -> Surface
        self.solid = set()  # (tx, ty) terrain solidity
        solid_ids = set()

        for ts in doc["tilesets"]:
            image = assets.load_image(os.path.normpath(os.path.join(base, ts["image"])))
            for tile in ts.get("tiles", []):
                for prop in tile.get("properties", []):
                    if prop["name"] == "solid" and prop["value"]:
                        solid_ids.add(ts["firstgid"] + tile["id"])
            for i in range(ts["tilecount"]):
                sx = (i % ts["columns"]) * ts["tilewidth"]
                sy = (i // ts["columns"]) * ts["tileheight"]
                tile = image.subsurface((sx, sy, ts["tilewidth"], ts["tileheight"]))
                self._tiles[ts["firstgid"] + i] = tile

        self._ground = pygame.Surface((self.pixel_width, self.pixel_height))
        for layer in doc["layers"]:
            if layer["type"] != "tilelayer" or not layer.get("visible", True):
                continue
            for i, gid in enumerate(layer["data"]):
                if gid == 0:
                    continue
                tx, ty = i % self.width, i // self.width
                if gid in solid_ids:
                    self.solid.add((tx, ty))
                tile = self._tiles.get(gid)
                if tile is not None:
                    self._ground.blit(tile, (tx * TILE_SIZE, ty * TILE_SIZE))

    def draw_ground(self, surface, offset):
        surface.blit(self._ground, (-offset.x, -offset.y))
