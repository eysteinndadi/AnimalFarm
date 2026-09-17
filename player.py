import pygame

TILE_SIZE = 16


def ease_out(t):
    return 1.0 - (1.0 - t) * (1.0 - t)


class Player:
    COLOR = (220, 60, 60)
    FACING_COLOR = (255, 220, 120)
    SPRITE_WIDTH = 16
    SPRITE_HEIGHT = 24               # taller than the tile: pokes out the top
    OVERHANG = SPRITE_HEIGHT - TILE_SIZE
    SPEED = 4.0        # tiles per second at full walk speed
    TURN_TIME = 0.1    # seconds a new direction must be held before stepping

    def __init__(self, tile_x, tile_y, map_width, map_height, solid=None):
        self.solid = solid if solid is not None else set()
        self.map_width = map_width
        self.map_height = map_height
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.pos = pygame.Vector2(tile_x * TILE_SIZE, tile_y * TILE_SIZE)
        self.facing = "down"

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

    def update(self, dt, keys):
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
            self.facing = d
            self.turn_dir = d
            self.turn_timer = self.TURN_TIME

    def _begin_step(self, direction):
        self.facing = direction
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

    @property
    def foot_y(self):
        # Bottom edge of the tile the player stands on; used for y-sorting.
        return self.pos.y + TILE_SIZE

    def draw(self, surface, offset):
        # The sprite is anchored at the bottom of its tile, so it
        # overhangs into the tile above (the "tall sprite" look).
        rect = pygame.Rect(
            round(self.pos.x - offset.x),
            round(self.pos.y - offset.y) - self.OVERHANG,
            self.SPRITE_WIDTH,
            self.SPRITE_HEIGHT,
        )
        pygame.draw.rect(surface, self.COLOR, rect)

        # Small marker on the edge the player is facing.
        marker = pygame.Rect(0, 0, 4, 4)
        if self.facing == "down":
            marker.center = (rect.centerx, rect.centery-self.SPRITE_HEIGHT/8)
        elif self.facing == "up":
            marker.midtop = rect.midtop
        elif self.facing == "left":
            marker.midleft = (rect.left, rect.centery-self.SPRITE_HEIGHT/4)
        else:
            marker.midright = (rect.right, rect.centery-self.SPRITE_HEIGHT/4)
        pygame.draw.rect(surface, self.FACING_COLOR, marker)
