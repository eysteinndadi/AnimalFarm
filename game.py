import asyncio

import pygame

import assets
import events
import ui
from camera import Camera
from dialogue import DialogueSession
from entities import NPC, Prop
from player import Player, TILE_SIZE
from tilemap import TileMap

# Pokemon White 2 runs on the DS at 256x192 per screen.
# We render to a small logical surface and scale it up for chunky pixels.
LOGICAL_WIDTH = 256
LOGICAL_HEIGHT = 192
SCALE = 3

WINDOW_WIDTH = LOGICAL_WIDTH * SCALE
WINDOW_HEIGHT = LOGICAL_HEIGHT * SCALE

FPS = 60

INTERACT_KEYS = (pygame.K_e, pygame.K_SPACE)
CONFIRM_OPTIONS = ("Yes", "Not yet")
DEFAULT_PHASE_QUESTION = "Go to the next phase?"


class Game:
    CREDITS_SPEED = 20       # logical px per second the credits roll
    ALLEGORY_SLIDE_TIME = 0.25

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("AnimalFarm")

        # SCALED lets pygame stretch the fixed-size window to the display
        # (letterboxed) so fullscreen needs no changes to the rendering.
        self.window = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED
        )
        self.screen = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.dt = 0.0

        self.map = TileMap("data/farm_map_v2.json")
        self.phases = assets.load_json("data/phases.json")
        self.dialogues = assets.load_json("data/dialogue.json")
        self.credits = assets.load_json("data/credits.json")
        self.credits_scroll = 0.0
        self.allegory = assets.load_json("data/allegory.json")
        self.allegory_key = None
        self.allegory_open = False
        self.allegory_t = 0.0        # 0 = closed, 1 = fully slid in
        self.allegory_scroll = 0
        self.allegory_overflow = 0
        self.camera = Camera(
            LOGICAL_WIDTH, LOGICAL_HEIGHT,
            self.map.pixel_width, self.map.pixel_height,
        )
        self.player = Player(0, 0, self.map.width, self.map.height)

        self.phase = 1
        self.state = "explore"
        self.dialogue = None
        self.scene = None          # (title, lines) for close-up panels
        self.after_scene = None    # state to enter when the scene closes
        self.after_dialogue = None # "confirm" to ask about advancing after a message
        self.confirm_question = DEFAULT_PHASE_QUESTION
        self.confirm_choice = 0
        self.transition_text = ""
        self.load_phase(1)

    def load_phase(self, phase):
        cfg = self.phases[str(phase)]
        self.phase = phase

        self.props = [
            Prop(
                p["name"], p["at"][0], p["at"][1],
                w=p.get("w", 1), h=p.get("h", 1),
                color=tuple(p.get("color", (120, 90, 60))),
                sprite_h=p.get("sprite_h"),
                interact=p.get("interact"),
                sprite=p.get("sprite"),
                frame=p.get("frame", 0),
                frame_w=p.get("frame_w"),
                anchor=p.get("anchor", "left"),
                shadow=p.get("shadow", 0),
                shadow_under=p.get("shadow_under", False),
                spin=p.get("spin"),
            )
            for p in cfg["props"]
        ]
        self.npcs = [
            NPC(
                n["name"], n["id"], n["at"][0], n["at"][1],
                color=tuple(n.get("color", (180, 180, 200))),
                sprite=n.get("sprite"),
                sprite_moving=n.get("sprite_moving"),
                patrol=n.get("patrol"),
                wander=n.get("wander"),
                idle=n.get("idle"),
                hop=n.get("hop", False),
                fly=n.get("fly"),
                faces_right=n.get("faces_right", False),
                w=n.get("w", 1),
                look=n.get("look", "left"),
            )
            for n in cfg["npcs"]
        ]
        self.commandments = cfg.get("commandments", [])
        self.ending_lines = cfg.get("ending", [])

        # Static solidity never changes; mobile NPCs block via their
        # occupied tiles, recomputed each frame in update().
        self.static_solid = set(self.map.solid)
        for entity in self.props:
            self.static_solid |= entity.solid_tiles
        for npc in self.npcs:
            if not npc.mobile:
                self.static_solid |= npc.solid_tiles
        self.player.solid = set(self.static_solid)
        self.player.teleport(*cfg["spawn"])
        self.camera.update(self._camera_target())
        self.registry = events.build_registry(self.props, self.npcs)

    def _camera_target(self):
        return pygame.Vector2(
            self.player.pos.x + TILE_SIZE / 2, self.player.foot_y
        )

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._on_key(event.key)

    def _set_allegory(self, key):
        self.allegory_key = key if key in self.allegory else None
        self.allegory_open = False
        self.allegory_t = 0.0
        self.allegory_scroll = 0

    def _lines_for(self, dialogue_id):
        # Like the allegory text: use the most recent phase that has lines,
        # so a character need not repeat unchanged dialogue in every phase.
        by_phase = self.dialogues.get(dialogue_id, {})
        phases = sorted(int(p) for p in by_phase)
        pick = max((p for p in phases if p <= self.phase), default=None)
        return by_phase[str(pick)] if pick is not None else ["..."]

    def _allegory_content(self):
        entry = self.allegory.get(self.allegory_key)
        if entry is None:
            return None
        text = entry["text"]
        if isinstance(text, dict):
            phases = sorted(int(p) for p in text)
            pick = max((p for p in phases if p <= self.phase),
                       default=phases[0])
            text = text[str(pick)]
        return entry["title"], text

    def _on_key(self, key):
        if key in (pygame.K_f, pygame.K_F11):
            pygame.display.toggle_fullscreen()
            return
        # While the allegory panel is open it swallows input: Q or Esc
        # closes it, Up/Down scrolls, E must not advance the dialogue.
        if self.allegory_open:
            if key in (pygame.K_q, pygame.K_ESCAPE):
                self.allegory_open = False
            elif key in (pygame.K_UP, pygame.K_w):
                self.allegory_scroll = max(
                    0, self.allegory_scroll - 24 * SCALE)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.allegory_scroll = min(
                    self.allegory_overflow,
                    self.allegory_scroll + 24 * SCALE)
            return
        if key == pygame.K_q:
            if self.state in ("dialogue", "scene") and self.allegory_key:
                self.allegory_open = True
                self.allegory_scroll = 0
            return
        if key in INTERACT_KEYS:
            if self.state == "explore":
                self._interact()
            elif self.state == "dialogue":
                self.dialogue.advance()
                if self.dialogue.done:
                    self.dialogue = None
                    self._set_allegory(None)
                    if self.after_dialogue == "confirm":
                        self.after_dialogue = None
                        self._open_confirm()
                    else:
                        self.state = "explore"
            elif self.state == "confirm":
                if self.confirm_choice == 0:
                    self._advance_phase()
                else:
                    self.state = "explore"
            elif self.state == "scene":
                self._close_scene()
            elif self.state == "transition":
                self.state = "explore"
        elif self.state == "confirm" and key in (
            pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d,
            pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s,
        ):
            self.confirm_choice = 1 - self.confirm_choice
        elif key == pygame.K_ESCAPE:
            if self.state in ("explore", "end"):
                self.running = False
            elif self.state == "scene":
                self._close_scene()
            elif self.state in ("dialogue", "transition", "confirm"):
                self.state = "explore"
                self.after_dialogue = None
                self._set_allegory(None)

    def _close_scene(self):
        self.scene = None
        self.state = self.after_scene or "explore"
        self.after_scene = None
        self._set_allegory(None)

    def _interact(self):
        front = self.player.tile_in_front()
        # Mobile NPCs aren't in the registry (they move); check them
        # by position before the static lookup.
        for npc in self.npcs:
            if npc.mobile and front in npc.occupied_tiles:
                npc.face_toward(self.player.tile_x)
                lines = self._lines_for(npc.dialogue_id)
                self.dialogue = DialogueSession(npc.name, lines)
                self.state = "dialogue"
                self._set_allegory(npc.dialogue_id)
                return
        action = self.registry.get(front)
        if action is None:
            return
        kind = action["type"]
        if kind == "dialogue":
            lines = self._lines_for(action["id"])
            self.dialogue = DialogueSession(action["speaker"], lines)
            self.state = "dialogue"
            self._set_allegory(action["id"])
        elif kind == "message":
            self.dialogue = DialogueSession("", [action["text"]])
            self.state = "dialogue"
            self._set_allegory(action.get("allegory"))
        elif kind == "commandments":
            self.scene = ("The Seven Commandments", self.commandments)
            self.state = "scene"
            self._set_allegory("commandments")
        elif kind == "ending":
            self.scene = ("The Farmhouse Window", self.ending_lines)
            self.after_scene = "end"
            self.state = "scene"
            self._set_allegory("farmhouse")
        elif kind == "advance_phase":
            self.confirm_question = action.get("question", DEFAULT_PHASE_QUESTION)
            text = action.get("text")
            if text:
                lines = text if isinstance(text, list) else [text]
                self.dialogue = DialogueSession("", lines)
                self.state = "dialogue"
                self.after_dialogue = "confirm"
                self._set_allegory(action.get("allegory"))
            else:
                self._open_confirm()

    def _open_confirm(self):
        self.confirm_choice = 0
        self.state = "confirm"

    def _advance_phase(self):
        next_phase = self.phase + 1
        if str(next_phase) not in self.phases:
            return
        self.load_phase(next_phase)
        cfg = self.phases[str(next_phase)]
        self.transition_text = cfg.get("transition", "Time passed...")
        self.state = "transition"

    def update(self):
        for prop in self.props:
            prop.update(self.dt)
        target = 1.0 if self.allegory_open else 0.0
        step = self.dt / self.ALLEGORY_SLIDE_TIME
        if self.allegory_t < target:
            self.allegory_t = min(target, self.allegory_t + step)
        elif self.allegory_t > target:
            self.allegory_t = max(target, self.allegory_t - step)
        if self.state == "end":
            # Roll the credits up until the last line rests mid-screen.
            end = ui.credits_height(self.credits, SCALE) + WINDOW_HEIGHT / 2
            self.credits_scroll = min(
                self.credits_scroll + self.CREDITS_SPEED * SCALE * self.dt, end
            )
        if self.state != "explore":
            return
        patrolling = [npc for npc in self.npcs if npc.mobile]
        player_tile = (self.player.tile_x, self.player.tile_y)
        for i, npc in enumerate(patrolling):
            blocked = set(self.static_solid) | {player_tile}
            for j, other in enumerate(patrolling):
                if i != j:
                    blocked |= other.occupied_tiles
            if npc.passable and player_tile in npc.occupied_tiles:
                npc.shoo(blocked, player_tile)
            npc.update(self.dt, blocked)
        self.player.solid = set(self.static_solid)
        for npc in patrolling:
            if not npc.passable:
                self.player.solid |= npc.occupied_tiles
        keys = pygame.key.get_pressed()
        self.player.update(self.dt, keys)
        self.player.can_interact = self._has_interaction()
        self.camera.update(self._camera_target())

    def _has_interaction(self):
        front = self.player.tile_in_front()
        return front in self.registry or any(
            npc.mobile and front in npc.occupied_tiles for npc in self.npcs
        )

    def render(self):
        self.map.draw_ground(self.screen, self.camera.offset)

        # Y-sorted pass: tall things draw back-to-front by their foot y.
        # On equal foot y (standing side by side) the player wins the tie.
        drawables = [(self.player.foot_y, 1, self.player.draw)]
        for entity in (*self.props, *self.npcs):
            drawables.append((entity.foot_y, 0, entity.draw))
        for _, _, draw in sorted(drawables, key=lambda item: item[:2]):
            draw(self.screen, self.camera.offset)

        scaled = pygame.transform.scale(
            self.screen, (WINDOW_WIDTH, WINDOW_HEIGHT)
        )
        self.window.blit(scaled, (0, 0))

        # UI draws at window resolution so text stays crisp
        # instead of being upscaled with the world.
        hint = "[Q] Soviet allegory" if self.allegory_key else None
        if self.state == "dialogue" and self.dialogue:
            ui.draw_dialogue_box(
                self.window, self.dialogue.speaker,
                self.dialogue.current_line, SCALE, hint=hint,
            )
        elif self.state == "scene" and self.scene:
            ui.draw_scene_panel(self.window, *self.scene, scale=SCALE,
                                hint=hint)
        elif self.state == "confirm":
            ui.draw_confirm_box(
                self.window, self.confirm_question, CONFIRM_OPTIONS,
                self.confirm_choice, SCALE,
            )
        elif self.state == "transition":
            ui.draw_transition(self.window, self.transition_text, SCALE)
        elif self.state == "end":
            ui.draw_credits(self.window, self.credits, self.credits_scroll, SCALE)

        if self.allegory_t > 0:
            content = self._allegory_content()
            if content:
                self.allegory_overflow = ui.draw_allegory_panel(
                    self.window, *content, self.allegory_t,
                    self.allegory_scroll, SCALE,
                )

        pygame.display.flip()

    async def run(self):
        while self.running:
            self.dt = self.clock.tick(FPS) / 1000.0

            self.handle_events()
            self.update()
            self.render()

            # Required for pygbag: yields control to the browser each frame.
            await asyncio.sleep(0)

        pygame.quit()
