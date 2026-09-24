import pygame

import assets

TILE_SIZE = 16

# Benjamin's sheet: 54 frames of 30x27 in one row, three views of 18 -
# side (0-17), looking down (18-35), looking up (36-53). Within each view,
# 0-8 are mouth closed and 9-17 mouth open; frame 0 of each set is standing
# and 1-8 are the walk cycle. The body always faces left in the art.
BENJAMIN_SHEET = "assets/characters/Benjamin/Benjamin_sprite_sheet.png"
FRAME_W, FRAME_H = 30, 27
FRAMES_PER_SET = 9
VIEWS = ("side", "down", "up")
WALK_PX_PER_FRAME = 4  # advance one walk frame every 4px travelled


def ease_out(t):
    return 1.0 - (1.0 - t) * (1.0 - t)


class Player:
    SPEED = 6.5        # tiles per second at full walk speed
    TURN_TIME = 0.1    # seconds a new direction must be held before stepping

    def __init__(self, tile_x, tile_y, map_width, map_height, solid=None):
        self.solid = solid if solid is not None else set()
        self.map_width = map_width
        self.map_height = map_height
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.pos = pygame.Vector2(tile_x * TILE_SIZE, tile_y * TILE_SIZE)
        self.facing = "down"
        # The art is side-view only, so up/down keep the last horizontal facing.
        self.facing_left = True
        self.can_interact = False  # set by Game; shows the mouth-open frames
        self._walk_px = 0.0
        self._last_pos = self.pos.copy()

        # frames[view][mouth_open][index] -> (left-facing, right-facing)
        sheet = assets.load_image(BENJAMIN_SHEET)
        self._frames = {}
        for v, view in enumerate(VIEWS):
            sets = []
            for mouth in range(2):
                frame_set = []
                for i in range(FRAMES_PER_SET):
                    n = (v * 2 + mouth) * FRAMES_PER_SET + i
                    img = sheet.subsurface((n * FRAME_W, 0, FRAME_W, FRAME_H))
                    frame_set.append((img, pygame.transform.flip(img, True, False)))
                sets.append(frame_set)
            self._frames[view] = sets

        self.moving = False
        self.step_t = 0.0
        self.step_duration = 1.0 / self.SPEED
        self.step_start = self.pos.copy()
        self.step_target = self.pos.copy()
        self.move_dir = "down"
        self.stopping = False      # last step eases out
        self.stop_from = self.pos.copy()
        self.stop_t0 = 0.0

        self.turn_dir = None
        self.turn_timer = 0.0

        self._directions = {
            "down": (0, 1),
            "up": (0, -1),
            "left": (-1, 0),
            "right": (1, 0),
        }
        self._keymap = {
            "down": (pygame.K_DOWN, pygame.K_s),
            "up": (pygame.K_UP, pygame.K_w),
            "left": (pygame.K_LEFT, pygame.K_a),
            "right": (pygame.K_RIGHT, pygame.K_d),
        }

    def _set_facing(self, direction):
        self.facing = direction
        if direction in ("left", "right"):
            self.facing_left = direction == "left"

    def update(self, dt, keys):
        self._last_pos.update(self.pos)
        if self.turn_timer > 0:
            self.turn_timer -= dt
            if not self._is_held(keys, self.turn_dir):
                # Tapped: turn only, no step.
                self.turn_timer = 0.0
            elif self.turn_timer <= 0:
                self._begin_step(self.turn_dir)

        if self.moving:
            self._advance(dt, keys)
        elif self.turn_timer <= 0:
            self._idle_input(keys)
        self._walk_px += (self.pos - self._last_pos).length()

    def _is_held(self, keys, direction):
        return direction is not None and any(
            keys[k] for k in self._keymap[direction]
        )

    def _held_direction(self, keys, prefer=None):
        order = list(self._directions)
        if prefer in self._directions:
            order.remove(prefer)
            order.insert(0, prefer)
        for d in order:
            if self._is_held(keys, d):
                return d
        return None

    def _idle_input(self, keys):
        d = self._held_direction(keys)
        if d is None:
            return
        if d == self.facing:
            self._begin_step(d)
        else:
            # Face the new direction first; stepping starts if the key
            # is still held when the turn timer expires.
            self._set_facing(d)
            self.turn_dir = d
            self.turn_timer = self.TURN_TIME

    def _begin_step(self, direction):
        self._set_facing(direction)
        dx, dy = self._directions[direction]
        nx, ny = self.tile_x + dx, self.tile_y + dy
        if (
            not (0 <= nx < self.map_width and 0 <= ny < self.map_height)
            or (nx, ny) in self.solid
        ):
            self.moving = False
            return
        self.tile_x, self.tile_y = nx, ny
        self.move_dir = direction
        self.step_start.update((nx - dx) * TILE_SIZE, (ny - dy) * TILE_SIZE)
        self.step_target.update(nx * TILE_SIZE, ny * TILE_SIZE)
        self.step_t = 0.0
        self.stopping = False
        self.moving = True

    def _advance(self, dt, keys):
        # Releasing the movement key mid-step eases into the target tile.
        if not self.stopping and not self._is_held(keys, self.move_dir):
            self.stopping = True
            self.stop_from.update(self.pos)
            self.stop_t0 = self.step_t

        self.step_t += dt / self.step_duration
        t = min(self.step_t, 1.0)

        if self.stopping:
            remaining = max(1.0 - self.stop_t0, 1e-6)
            s = min((t - self.stop_t0) / remaining, 1.0)
            offset = self.step_target - self.stop_from
            self.pos = self.stop_from + offset * ease_out(s)
        else:
            self.pos = self.step_start + (self.step_target - self.step_start) * t

        if self.step_t >= 1.0:
            self.pos.update(self.step_target)
            d = self._held_direction(keys, prefer=self.move_dir)
            if d is None:
                self.moving = False
            else:
                self._begin_step(d)

    def tile_in_front(self):
        dx, dy = self._directions[self.facing]
        return self.tile_x + dx, self.tile_y + dy

    def teleport(self, tile_x, tile_y):
        self.tile_x, self.tile_y = tile_x, tile_y
        self.pos.update(tile_x * TILE_SIZE, tile_y * TILE_SIZE)
        self.moving = False
        self.stopping = False
        self.turn_timer = 0.0
        self.facing = "down"
        self._last_pos.update(self.pos)

    @property
    def foot_y(self):
        # Bottom edge of the tile the player stands on; used for y-sorting.
        return self.pos.y + TILE_SIZE

    def _current_frame(self):
        view = self.facing if self.facing in ("up", "down") else "side"
        frame_set = self._frames[view][1 if self.can_interact else 0]
        index = 0
        if self.moving:
            index = 1 + int(self._walk_px / WALK_PX_PER_FRAME) % (FRAMES_PER_SET - 1)
        pair = frame_set[index]
        return pair[0] if self.facing_left else pair[1]

    def draw(self, surface, offset):
        # Anchored bottom-center on the tile, like NPCs: the sprite is
        # wider and taller than 16px and overhangs above and to the sides.
        sprite = self._current_frame()
        x = round(self.pos.x - offset.x) + (TILE_SIZE - sprite.get_width()) // 2
        y = round(self.pos.y - offset.y) + TILE_SIZE - sprite.get_height()
        surface.blit(sprite, (x, y))
