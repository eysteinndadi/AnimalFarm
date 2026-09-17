import json

import pygame

ASSETS_DIR = "assets"
DATA_DIR = "data"

_image_cache = {}


def load_image(path):
    if path not in _image_cache:
        _image_cache[path] = pygame.image.load(path).convert_alpha()
    return _image_cache[path]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
