import pygame

import assets

TILE_SIZE = 16


class Prop:
    """A static tall object: building, tree, fence structure, flagpole...

    Occupies a solid w x h tile footprint and draws a placeholder rect
    anchored at the footprint's bottom edge. `sprite_h` (px) lets the
    visual be taller than the footprint — e.g. a 1x1 tree with a 32px
    canopy that overhangs the tile above.

    With `sprite` set, an image is drawn instead, anchored so its
    bottom-left corner sits on the footprint's bottom-left tile; the
    image may be any size and overhang the footprint. `frame_w` slices
    a horizontal sprite sheet and `frame` picks which slice to show.
    """

    def __init__(self, name, tx, ty, w=1, h=1, color=(120, 90, 60),
                 sprite_h=None, interact=None, sprite=None, frame=0,
                 frame_w=None):
        self.name = name
        self.tx, self.ty = tx, ty
        self.w, self.h = w, h
        self.color = color
        self.sprite_h = sprite_h if sprite_h is not None else h * TILE_SIZE
        interact = interact or []
        self.interact = [interact] if isinstance(interact, dict) else interact

        self.image = None
        if sprite:
            sheet = assets.load_image(sprite)
            fw = frame_w or sheet.get_width()
            self.image = sheet.subsurface((frame * fw, 0, fw, sheet.get_height()))

    @property
    def foot_y(self):
        return (self.ty + self.h) * TILE_SIZE

    @property
    def solid_tiles(self):
        return {
            (self.tx + x, self.ty + y)
            for x in range(self.w) for y in range(self.h)
        }

    @property
    def interact_tiles(self):
        return {
            tuple(t)
            for spec in self.interact
            for t in spec.get("tiles", [])
        }

    def draw(self, surface, offset):
        x = round(self.tx * TILE_SIZE - offset.x)
        bottom = round((self.ty + self.h) * TILE_SIZE - offset.y)
        if self.image:
            surface.blit(self.image, (x, bottom - self.image.get_height()))
            return
        rect = pygame.Rect(x, bottom - self.sprite_h, self.w * TILE_SIZE, self.sprite_h)
        pygame.draw.rect(surface, self.color, rect)
        pygame.draw.rect(surface, (0, 0, 0), rect, 1)


class NPC:
    """A stationary character the player can talk to."""

    SPRITE_HEIGHT = 24

    def __init__(self, name, dialogue_id, tx, ty, color=(180, 180, 200),
                 sprite=None):
        self.name = name
        self.dialogue_id = dialogue_id
        self.tx, self.ty = tx, ty
        self.color = color
        self.sprite = assets.load_image(sprite) if sprite else None

    @property
    def foot_y(self):
        return (self.ty + 1) * TILE_SIZE

    @property
    def solid_tiles(self):
        return {(self.tx, self.ty)}

    def draw(self, surface, offset):
        x = round(self.tx * TILE_SIZE - offset.x)
        bottom = round((self.ty + 1) * TILE_SIZE - offset.y)
        if self.sprite:
            # Anchored bottom-center of the tile, like everything else.
            surface.blit(
                self.sprite,
                (x + (TILE_SIZE - self.sprite.get_width()) // 2,
                 bottom - self.sprite.get_height()),
            )
            return
        body = pygame.Rect(x, bottom - self.SPRITE_HEIGHT, TILE_SIZE, self.SPRITE_HEIGHT)
        pygame.draw.rect(surface, self.color, body)
        head = pygame.Rect(x + 2, bottom - self.SPRITE_HEIGHT, TILE_SIZE - 4, 8)
        pygame.draw.rect(surface, (240, 220, 190), head)
        pygame.draw.rect(surface, (0, 0, 0), body, 1)
