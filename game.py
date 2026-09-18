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


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("AnimalFarm")

        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.screen = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.dt = 0.0

        self.map = TileMap("data/farm_map.json")
        self.phases = assets.load_json("data/phases.json")
        self.dialogues = assets.load_json("data/dialogue.json")
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
            )
            for p in cfg["props"]
        ]
        self.npcs = [
            NPC(
                n["name"], n["id"], n["at"][0], n["at"][1],
                color=tuple(n.get("color", (180, 180, 200))),
                sprite=n.get("sprite"),
            )
            for n in cfg["npcs"]
        ]
        self.commandments = cfg.get("commandments", [])
        self.ending_lines = cfg.get("ending", [])

        solid = set(self.map.solid)
        for entity in (*self.props, *self.npcs):
            solid |= entity.solid_tiles
        self.player.solid = solid
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

    def _on_key(self, key):
        if key in INTERACT_KEYS:
            if self.state == "explore":
                self._interact()
            elif self.state == "dialogue":
                self.dialogue.advance()
                if self.dialogue.done:
                    self.dialogue = None
                    self.state = "explore"
            elif self.state == "scene":
                self._close_scene()
            elif self.state == "transition":
                self.state = "explore"
        elif key == pygame.K_ESCAPE:
            if self.state in ("explore", "end"):
                self.running = False
            elif self.state == "scene":
                self._close_scene()
            elif self.state in ("dialogue", "transition"):
                self.state = "explore"

    def _close_scene(self):
        self.scene = None
        self.state = self.after_scene or "explore"
        self.after_scene = None

    def _interact(self):
        action = self.registry.get(self.player.tile_in_front())
        if action is None:
            return
        kind = action["type"]
        if kind == "dialogue":
            lines = self.dialogues.get(action["id"], {}).get(
                str(self.phase), ["..."]
            )
            self.dialogue = DialogueSession(action["speaker"], lines)
            self.state = "dialogue"
        elif kind == "message":
            self.dialogue = DialogueSession("", [action["text"]])
            self.state = "dialogue"
        elif kind == "commandments":
            self.scene = ("The Seven Commandments", self.commandments)
            self.state = "scene"
        elif kind == "ending":
            self.scene = ("The Farmhouse Window", self.ending_lines)
            self.after_scene = "end"
            self.state = "scene"
        elif kind == "advance_phase":
            self._advance_phase()

    def _advance_phase(self):
        next_phase = self.phase + 1
        if str(next_phase) not in self.phases:
            return
        self.load_phase(next_phase)
        cfg = self.phases[str(next_phase)]
        self.transition_text = cfg.get("transition", "Time passed...")
        self.state = "transition"

    def update(self):
        if self.state == "explore":
            keys = pygame.key.get_pressed()
            self.player.update(self.dt, keys)
            self.camera.update(self._camera_target())
            print(self.player.tile_x, self.player.tile_y)

    def render(self):
        self.map.draw_ground(self.screen, self.camera.offset)

        # Y-sorted pass: tall things draw back-to-front by their foot y.
        drawables = [(self.player.foot_y, self.player.draw)]
        for entity in (*self.props, *self.npcs):
            drawables.append((entity.foot_y, entity.draw))
        for _, draw in sorted(drawables, key=lambda item: item[0]):
            draw(self.screen, self.camera.offset)

        scaled = pygame.transform.scale(
            self.screen, (WINDOW_WIDTH, WINDOW_HEIGHT)
        )
        self.window.blit(scaled, (0, 0))

        # UI draws at window resolution so text stays crisp
        # instead of being upscaled with the world.
        if self.state == "dialogue" and self.dialogue:
            ui.draw_dialogue_box(
                self.window, self.dialogue.speaker,
                self.dialogue.current_line, SCALE,
            )
        elif self.state == "scene" and self.scene:
            ui.draw_scene_panel(self.window, *self.scene, scale=SCALE)
        elif self.state == "transition":
            ui.draw_transition(self.window, self.transition_text, SCALE)
        elif self.state == "end":
            ui.draw_transition(self.window, "The End", SCALE)

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
