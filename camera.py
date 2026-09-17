import pygame


class Camera:
    """Follows a target and clamps to the map bounds."""

    def __init__(self, view_width, view_height, map_pixel_width, map_pixel_height):
        self.view_w = view_width
        self.view_h = view_height
        self.map_w = map_pixel_width
        self.map_h = map_pixel_height
        self.offset = pygame.Vector2(0, 0)

    def update(self, target_pos):
        # target_pos is the world-space point to center on (player feet).
        # Rounded to whole pixels: a fractional offset makes every entity's
        # draw position flicker by +-1px each frame (visible as shaking).
        self.offset.x = round(self._clamp(target_pos.x - self.view_w / 2, self.map_w, self.view_w))
        self.offset.y = round(self._clamp(target_pos.y - self.view_h / 2, self.map_h, self.view_h))

    @staticmethod
    def _clamp(value, map_px, view_px):
        if map_px <= view_px:
            return (map_px - view_px) / 2
        return max(0, min(value, map_px - view_px))
