import math
import random

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
    `shadow` (px) draws a soft dark strip on the ground along the
    image's bottom edge so a building looks grounded. It follows the
    opaque stretches of the bottom row (skipping doorways and gaps);
    `shadow_under` instead spans the whole width and tucks 1px up under
    the sprite, for buildings on stilts.
    `spin={"sprite": path, "speed": deg_per_sec}` overlays a second image
    (same canvas size as the main sprite) that rotates about the centre
    of its opaque pixels - e.g. windmill sails on top of the tower.
    """

    SHADOW_ALPHA = 120
    SPIN_STEP = 10  # degrees between pre-rendered rotation frames

    def __init__(self, name, tx, ty, w=1, h=1, color=(120, 90, 60),
                 sprite_h=None, interact=None, sprite=None, frame=0,
                 frame_w=None, anchor="left", shadow=0, shadow_under=False,
                 spin=None):
        self.name = name
        self.tx, self.ty = tx, ty
        self.w, self.h = w, h
        self.color = color
        self.anchor = anchor  # "left": image's bottom-left on footprint; "center": centered over it
        self.sprite_h = sprite_h if sprite_h is not None else h * TILE_SIZE
        interact = interact or []
        self.interact = [interact] if isinstance(interact, dict) else interact

        self.image = None
        if sprite:
            sheet = assets.load_image(sprite)
            fw = frame_w or sheet.get_width()
            self.image = sheet.subsurface((frame * fw, 0, fw, sheet.get_height()))
        self.spin = None
        if spin and self.image:
            overlay = assets.load_image(spin["sprite"])
            bounds = overlay.get_bounding_rect()
            self.spin_pivot = bounds.center
            # Crop to a square around the pivot so rotation keeps it centred.
            r = max(bounds.width, bounds.height) // 2 + 1
            square = pygame.Surface((2 * r + 1, 2 * r + 1), pygame.SRCALPHA)
            square.blit(overlay, (r - bounds.centerx, r - bounds.centery))
            self.spin_frames = [
                pygame.transform.rotate(square, -a)
                for a in range(0, 360, self.SPIN_STEP)
            ]
            self.spin = spin.get("speed", 45)
            self.spin_angle = 0.0
        self.shadow = None
        if shadow and self.image:
            # Shadow only the opaque stretches of the image's bottom row, so
            # it hugs the walls and skips transparent margins and doorways.
            bottom_row, iw = self.image.get_height() - 1, self.image.get_width()
            self.shadow = pygame.Surface((iw, shadow), pygame.SRCALPHA)
            runs, start = [], None
            for x in range(iw + 1):
                opaque = x < iw and self.image.get_at((x, bottom_row)).a > 0
                if opaque and start is None:
                    start = x
                elif not opaque and start is not None:
                    runs.append((start, x - 1))
                    start = None
            if shadow_under and runs:
                runs = [(runs[0][0], runs[-1][1])]
            self.shadow_dy = -1 if shadow_under else 0
            for x0, x1 in runs:
                for row in range(shadow):
                    # Fade out and pull the ends in as the shadow gets further from the wall.
                    a = round(self.SHADOW_ALPHA * (1 - row / shadow))
                    if x0 + row <= x1 - row:
                        pygame.draw.line(self.shadow, (0, 0, 0, a), (x0 + row, row), (x1 - row, row))

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

    def update(self, dt):
        if self.spin:
            self.spin_angle = (self.spin_angle + self.spin * dt) % 360

    def draw(self, surface, offset):
        x = round(self.tx * TILE_SIZE - offset.x)
        bottom = round((self.ty + self.h) * TILE_SIZE - offset.y)
        if self.image:
            if self.anchor == "center":
                x += (self.w * TILE_SIZE - self.image.get_width()) // 2
            if self.shadow:
                surface.blit(self.shadow, (x, bottom + self.shadow_dy))
            top = bottom - self.image.get_height()
            surface.blit(self.image, (x, top))
            if self.spin:
                frame = self.spin_frames[int(self.spin_angle // self.SPIN_STEP)]
                px, py = self.spin_pivot
                surface.blit(frame, (x + px - frame.get_width() // 2, top + py - frame.get_height() // 2))
            return
        rect = pygame.Rect(x, bottom - self.sprite_h, self.w * TILE_SIZE, self.sprite_h)
        pygame.draw.rect(surface, self.color, rect)
        pygame.draw.rect(surface, (0, 0, 0), rect, 1)


class NPC:
    """A character the player can talk to.

    With `patrol=[a, b]` (two tiles on a straight horizontal or vertical
    line) the NPC walks back and forth between them, pausing at each end.
    With `wander=[x0, y0, x1, y1]` it moves one tile at a time in random
    directions, staying inside that tile rectangle (inclusive); `idle=(lo, hi)`
    is the random pause between moves and `hop=True` adds a little jump arc.
    With `fly=[x0, y0, x1, y1]` it flies in straight lines (not tile by tile)
    to random free tiles inside that rectangle, perching for `idle` seconds
    between flights. In the air it is neither solid nor talkable.
    `sprite_moving` is an optional second walk frame. Sprites are assumed
    to face left; set `faces_right` for art drawn the other way. Without
    `patrol` or `wander` it stays put.
    """

    SPRITE_HEIGHT = 24
    SPEED = 2.0        # tiles per second
    PAUSE = 1.0        # seconds waiting at each patrol endpoint
    WANDER_PAUSE = (0.4, 2.0)  # random idle range between hops
    HOP_HEIGHT = 4     # px the sprite lifts mid-hop when wandering
    FLY_SPEED = 2.5    # tiles per second in flight (average)
    FLY_HEIGHT = 14    # px altitude at the top of a flight arc
    FLY_PAUSE = (2.0, 6.0)  # default perch time between flights
    SHOO_RANGE = 5     # max tiles a startled flyer relocates, so it's easy to catch up
    FRAME_TIME = 0.15  # seconds per walk-animation frame

    def __init__(self, name, dialogue_id, tx, ty, color=(180, 180, 200),
                 sprite=None, sprite_moving=None, patrol=None, wander=None,
                 faces_right=False, w=1, idle=None, hop=False, fly=None,
                 look="left"):
        self.name = name
        self.dialogue_id = dialogue_id
        self.tx, self.ty = tx, ty
        self.w = w  # footprint width in tiles; sprite is centered over it
        self.pos = pygame.Vector2(tx * TILE_SIZE, ty * TILE_SIZE)
        self.color = color
        self.patrol = [tuple(p) for p in patrol] if patrol else None
        self.wander = tuple(wander) if wander else None
        self.fly = tuple(fly) if fly else None
        default_idle = self.FLY_PAUSE if fly else self.WANDER_PAUSE
        self.idle = tuple(idle) if idle else default_idle
        self.hop = hop
        self.mobile = any(x is not None for x in (self.patrol, self.wander, self.fly))
        # Wanderers and flyers are small animals: the player can walk into
        # their tile and they scatter (see `shoo`) instead of blocking the way.
        self.passable = self.wander is not None or self.fly is not None

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

        self.facing_left = look != "right"
        self.moving = False
        self._pause = 0.0
        self._target = 0 if patrol and tuple(patrol[0]) != (tx, ty) else 1
        self._step_dir = (0, 0)
        self._prev_tile = (tx, ty)
        self._anim_t = 0.0
        self.flying = False
        self._fly_from = self.pos.copy()
        self._fly_to = self.pos.copy()
        self._fly_t = 0.0
        self._fly_duration = 1.0

    @property
    def foot_y(self):
        if self.flying:
            return float("inf")  # airborne: draw over everything
        return self.pos.y + TILE_SIZE

    @property
    def occupied_tiles(self):
        if self.flying:
            return set()
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
        if not self.mobile:
            return
        if self.flying:
            self._glide(dt)
            return
        if self.moving:
            self._advance(dt)
            return
        if self._pause > 0:
            self._pause -= dt
            return
        if self.patrol is not None:
            self._step_toward(blocked)
        elif self.fly is not None:
            self._take_off(blocked)
        else:
            self._hop_randomly(blocked)

    def _take_off(self, blocked, tries=20, max_dist=None, away_from=None):
        x0, y0, x1, y1 = self.fly
        if max_dist is not None:
            # Only look at nearby tiles (a short startled hop, not a full flight).
            x0, x1 = max(x0, self.tx - max_dist), min(x1, self.tx + max_dist)
            y0, y1 = max(y0, self.ty - max_dist), min(y1, self.ty + max_dist)
        for _ in range(tries):
            tx, ty = random.randint(x0, x1), random.randint(y0, y1)
            if (tx, ty) == (self.tx, self.ty) or (tx, ty) in blocked:
                continue
            if max_dist is not None and math.hypot(tx - self.tx, ty - self.ty) > max_dist:
                continue
            if away_from is not None and max(abs(tx - away_from[0]), abs(ty - away_from[1])) < 2:
                continue  # don't land right next to whoever startled us
            break
        else:
            self._pause = random.uniform(*self.idle)
            return
        self.facing_left = tx < self.tx
        self.tx, self.ty = tx, ty
        self._fly_from.update(self.pos)
        self._fly_to.update(tx * TILE_SIZE, ty * TILE_SIZE)
        dist = (self._fly_to - self._fly_from).length()
        self._fly_duration = max(dist / (self.FLY_SPEED * TILE_SIZE), 0.6)
        self._fly_t = 0.0
        self._anim_t = 0.0
        self.flying = True

    def _glide(self, dt):
        self._fly_t = min(self._fly_t + dt / self._fly_duration, 1.0)
        self._anim_t += dt
        # Smoothstep: gentle take-off and landing instead of a linear dart.
        t = self._fly_t * self._fly_t * (3 - 2 * self._fly_t)
        self.pos = self._fly_from.lerp(self._fly_to, t)
        if self._fly_t >= 1.0:
            self.pos.update(self._fly_to)
            self.flying = False
            self._pause = random.uniform(*self.idle)

    def _step_toward(self, blocked):
        # Pick the next patrol endpoint and take one step along the line.
        gx, gy = self.patrol[self._target]
        dx = (gx > self.tx) - (gx < self.tx)
        dy = (gy > self.ty) - (gy < self.ty)
        if dx == 0 and dy == 0:
            self._target = 1 - self._target
            self._pause = self.PAUSE
            return
        self._step((dx, dy), blocked)

    def _hop_randomly(self, blocked, away_from=None):
        x0, y0, x1, y1 = self.wander
        options = [
            (dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if x0 <= self.tx + dx <= x1 and y0 <= self.ty + dy <= y1
        ]
        random.shuffle(options)
        if away_from is not None:
            fx, fy = away_from
            options.sort(key=lambda d: -abs(self.tx + d[0] - fx) - abs(self.ty + d[1] - fy))
        for d in options:
            if self._step(d, blocked):
                break
        self._pause = random.uniform(*self.idle)

    def shoo(self, blocked, from_tile):
        """Move away right now (wanderers hop, flyers take off), preferring
        tiles farther from `from_tile`. Called when the player steps into
        this NPC."""
        if self.moving or self.flying:
            return
        if self.fly is not None:
            self._take_off(blocked, max_dist=self.SHOO_RANGE, away_from=from_tile)
        elif self.wander is not None:
            self._hop_randomly(blocked, away_from=from_tile)

    def _step(self, direction, blocked):
        dx, dy = direction
        nx, ny = self.tx + dx, self.ty + dy
        if any((nx + i, ny) in blocked for i in range(self.w)):
            return False  # wait and retry next frame
        self._prev_tile = (self.tx, self.ty)
        self.tx, self.ty = nx, ny
        self._step_dir = (dx, dy)
        self.facing_left = dx < 0 or (dx == 0 and self.facing_left)
        self.moving = True
        return True

    def _advance(self, dt):
        step = self.SPEED * TILE_SIZE * dt
        self.pos.x += self._step_dir[0] * step
        self.pos.y += self._step_dir[1] * step
        self._anim_t += dt
        target = pygame.Vector2(self.tx * TILE_SIZE, self.ty * TILE_SIZE)
        if (target - self.pos).length() <= step:
            self.pos.update(target)
            self.moving = False

    def _hop_offset(self):
        # Returned unrounded: the caller rounds once on the final screen y,
        # since rounding position and lift separately makes them jitter.
        if self.flying:
            return self.FLY_HEIGHT * math.sin(math.pi * self._fly_t)
        # Hopping wanderers arc upward over the step; others walk flat.
        if not self.hop or not self.moving:
            return 0.0
        target = pygame.Vector2(self.tx * TILE_SIZE, self.ty * TILE_SIZE)
        progress = 1 - (target - self.pos).length() / TILE_SIZE
        return self.HOP_HEIGHT * math.sin(math.pi * progress)

    def _current_frame(self):
        if not self._frames:
            return None
        pair = self._frames[0]
        if (self.moving or self.flying) and len(self._frames) > 1:
            pair = self._frames[int(self._anim_t / self.FRAME_TIME) % 2]
        return pair[0 if self.facing_left else 1]

    def draw(self, surface, offset):
        x = round(self.pos.x - offset.x)
        bottom = round(self.pos.y + TILE_SIZE - offset.y)
        sprite = self._current_frame()
        if sprite:
            # Anchored bottom-center of the footprint, like everything else.
            sprite_bottom = round(self.pos.y + TILE_SIZE - offset.y - self._hop_offset())
            surface.blit(
                sprite,
                (x + (self.w * TILE_SIZE - sprite.get_width()) // 2,
                 sprite_bottom - sprite.get_height()),
            )
            return
        body = pygame.Rect(x, bottom - self.SPRITE_HEIGHT, TILE_SIZE, self.SPRITE_HEIGHT)
        pygame.draw.rect(surface, self.color, body)
        head = pygame.Rect(x + 2, bottom - self.SPRITE_HEIGHT, TILE_SIZE - 4, 8)
        pygame.draw.rect(surface, (240, 220, 190), head)
        pygame.draw.rect(surface, (0, 0, 0), body, 1)
