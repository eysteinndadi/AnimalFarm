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
    """A character the player can talk to.

    With `patrol=[a, b]` (two tiles on a straight horizontal or vertical
    line) the NPC walks back and forth between them, pausing at each end.
    `sprite_moving` is an optional second walk frame. Sprites are assumed
    to face left; set `faces_right` for art drawn the other way. Without
    `patrol` it stays put.
    """

    SPRITE_HEIGHT = 24
    SPEED = 2.0        # tiles per second
    PAUSE = 1.0        # seconds waiting at each patrol endpoint
    FRAME_TIME = 0.15  # seconds per walk-animation frame

    def __init__(self, name, dialogue_id, tx, ty, color=(180, 180, 200),
                 sprite=None, sprite_moving=None, patrol=None,
                 faces_right=False, w=1):
        self.name = name
        self.dialogue_id = dialogue_id
        self.tx, self.ty = tx, ty
        self.w = w  # footprint width in tiles; sprite is centered over it
        self.pos = pygame.Vector2(tx * TILE_SIZE, ty * TILE_SIZE)
        self.color = color
        self.patrol = [tuple(p) for p in patrol] if patrol else None

        self.sprite = assets.load_image(sprite) if sprite else None
        self.sprite_moving = (
            assets.load_image(sprite_moving) if sprite_moving else None
        )
        # Cache (left-facing, right-facing) pairs; `faces_right` says
        # which way the source art points so the flip goes the right way.
        self._frames = []
        for img in (self.sprite, self.sprite_moving or self.sprite):
            if img is None:
                continue
            flipped = pygame.transform.flip(img, True, False)
            self._frames.append((flipped, img) if faces_right else (img, flipped))

        self.facing_left = True
        self.moving = False
        self._pause = 0.0
        self._target = 0 if patrol and tuple(patrol[0]) != (tx, ty) else 1
        self._step_dir = (0, 0)
        self._prev_tile = (tx, ty)
        self._anim_t = 0.0

    @property
    def foot_y(self):
        return self.pos.y + TILE_SIZE

    @property
    def occupied_tiles(self):
        anchors = [(self.tx, self.ty)]
        if self.moving:
            anchors.append(self._prev_tile)
        return {(ax + i, ay) for ax, ay in anchors for i in range(self.w)}

    @property
    def solid_tiles(self):
        return self.occupied_tiles

    def face_toward(self, tile_x):
        self.facing_left = tile_x < self.tx

    def update(self, dt, blocked):
        if self.patrol is None:
            return
        if self.moving:
            self._advance(dt)
            return
        if self._pause > 0:
            self._pause -= dt
            return
        self._step_toward(blocked)

    def _step_toward(self, blocked):
        # Pick the next patrol endpoint and take one step along the line.
        gx, gy = self.patrol[self._target]
        dx = (gx > self.tx) - (gx < self.tx)
        dy = (gy > self.ty) - (gy < self.ty)
        if dx == 0 and dy == 0:
            self._target = 1 - self._target
            self._pause = self.PAUSE
            return
        nx, ny = self.tx + dx, self.ty + dy
        if (nx, ny) in blocked:
            return  # wait and retry next frame
        self._prev_tile = (self.tx, self.ty)
        self.tx, self.ty = nx, ny
        self._step_dir = (dx, dy)
        self.facing_left = dx < 0 or (dx == 0 and self.facing_left)
        self.moving = True

    def _advance(self, dt):
        step = self.SPEED * TILE_SIZE * dt
        self.pos.x += self._step_dir[0] * step
        self.pos.y += self._step_dir[1] * step
        self._anim_t += dt
        target = pygame.Vector2(self.tx * TILE_SIZE, self.ty * TILE_SIZE)
        if (target - self.pos).length() <= step:
            self.pos.update(target)
            self.moving = False

    def _current_frame(self):
        if not self._frames:
            return None
        pair = self._frames[0]
        if self.moving and len(self._frames) > 1:
            pair = self._frames[int(self._anim_t / self.FRAME_TIME) % 2]
        return pair[0 if self.facing_left else 1]

    def draw(self, surface, offset):
        x = round(self.pos.x - offset.x)
        bottom = round(self.pos.y + TILE_SIZE - offset.y)
        sprite = self._current_frame()
        if sprite:
            # Anchored bottom-center of the footprint, like everything else.
            surface.blit(
                sprite,
                (x + (self.w * TILE_SIZE - sprite.get_width()) // 2,
                 bottom - sprite.get_height()),
            )
            return
        body = pygame.Rect(x, bottom - self.SPRITE_HEIGHT, TILE_SIZE, self.SPRITE_HEIGHT)
        pygame.draw.rect(surface, self.color, body)
        head = pygame.Rect(x + 2, bottom - self.SPRITE_HEIGHT, TILE_SIZE - 4, 8)
        pygame.draw.rect(surface, (240, 220, 190), head)
        pygame.draw.rect(surface, (0, 0, 0), body, 1)
