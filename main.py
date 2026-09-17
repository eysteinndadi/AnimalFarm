import asyncio

import pygame

from player import Player, TILE_SIZE

# Pokemon White 2 runs on the DS at 256x192 per screen.
# We render to a small logical surface and scale it up for chunky pixels.
LOGICAL_WIDTH = 256
LOGICAL_HEIGHT = 192
SCALE = 3

WINDOW_WIDTH = LOGICAL_WIDTH * SCALE
WINDOW_HEIGHT = LOGICAL_HEIGHT * SCALE

FPS = 60


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("AnimalFarm")

        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.screen = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))

        self.grass_tile = pygame.image.load("Images/Grasstile01.png").convert()

        self.clock = pygame.time.Clock()
        self.running = True
        self.dt = 0.0

        self.trees = [(5, 4), (10, 8), (3, 9)]
        self.player = Player(8, 6, solid=set(self.trees))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self):
        keys = pygame.key.get_pressed()
        self.player.update(self.dt, keys)

    def render(self):
        for y in range(0, LOGICAL_HEIGHT, TILE_SIZE):
            for x in range(0, LOGICAL_WIDTH, TILE_SIZE):
                self.screen.blit(self.grass_tile, (x, y))
        
        # Y-sorted pass: tall things draw back-to-front by their foot y,
        # so the player correctly walks in front of or behind them.
        drawables = [(self.player.foot_y, self.player.draw)]
        for tx, ty in self.trees:
            foot_y = (ty + 1) * TILE_SIZE
            drawables.append(
                (foot_y, lambda s, t=(tx, ty): self._draw_tree(s, *t))
            )
        for _, draw in sorted(drawables, key=lambda item: item[0]):
            draw(self.screen)

        scaled = pygame.transform.scale(
            self.screen, (WINDOW_WIDTH, WINDOW_HEIGHT)
        )
        self.window.blit(scaled, (0, 0))
        pygame.display.flip()

    def _draw_tree(self, surface, tile_x, tile_y):
        # Placeholder tree: 16x32, anchored at the bottom of its base tile.
        # Only the base tile is solid; the top half just overhangs visually.
        rect = pygame.Rect(
            tile_x * TILE_SIZE,
            (tile_y + 1) * TILE_SIZE - 32,
            TILE_SIZE,
            32,
        )
        pygame.draw.rect(surface, (50, 140, 70), rect)
        trunk = pygame.Rect(0, 0, 4, 8)
        trunk.midbottom = rect.midbottom
        pygame.draw.rect(surface, (110, 80, 50), trunk)

    async def run(self):
        while self.running:
            self.dt = self.clock.tick(FPS) / 1000.0

            self.handle_events()
            self.update()
            self.render()

            # Required for pygbag: yields control to the browser each frame.
            await asyncio.sleep(0)

        pygame.quit()


def main():
    game = Game()
    asyncio.run(game.run())


if __name__ == "__main__":
    main()
