import pygame

_fonts = {}


def _font(size):
    if size not in _fonts:
        _fonts[size] = pygame.font.Font(None, size)
    return _fonts[size]


def wrap_text(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = word if not current else current + " " + word
        if font.size(test)[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def draw_dialogue_box(surface, speaker, text, scale=1):
    """Pokemon-style bottom dialogue box.

    Drawn at window resolution (scale = window/logical) so text is crisp
    rather than upscaled with the world.
    """
    s = scale
    margin, box_h = 4 * s, 56 * s
    w, h = surface.get_size()
    rect = pygame.Rect(margin, h - box_h - margin, w - 2 * margin, box_h)
    pygame.draw.rect(surface, (16, 16, 28), rect)
    pygame.draw.rect(surface, (230, 230, 240), rect, max(1, round(1 * s)))

    font = _font(10 * s)
    y = rect.y + 5 * s
    if speaker:
        surface.blit(
            font.render(speaker, True, (255, 220, 120)),
            (rect.x + 6 * s, y),
        )
        y += 11 * s
    for line in wrap_text(text, font, rect.width - 12 * s):
        surface.blit(
            font.render(line, True, (240, 240, 240)),
            (rect.x + 6 * s, y),
        )
        y += 10 * s

    surface.blit(
        font.render("v", True, (200, 200, 200)),
        (rect.right - 10 * s, rect.bottom - 11 * s),
    )


def draw_transition(surface, text, scale=1):
    surface.fill((0, 0, 0))
    font = _font(14 * scale)
    img = font.render(text, True, (240, 240, 240))
    w, h = surface.get_size()
    surface.blit(img, ((w - img.get_width()) / 2, (h - img.get_height()) / 2))


def draw_scene_panel(surface, title, lines, scale=1):
    """Full-screen close-up panel: barn wall, farmhouse window, etc."""
    s = scale
    w, h = surface.get_size()
    surface.fill((30, 22, 16))
    panel = pygame.Rect(12 * s, 12 * s, w - 24 * s, h - 24 * s)
    pygame.draw.rect(surface, (70, 50, 34), panel)
    pygame.draw.rect(surface, (230, 210, 180), panel, max(1, round(2 * s)))

    title_font = _font(12 * s)
    body_font = _font(10 * s)
    img = title_font.render(title, True, (255, 230, 160))
    surface.blit(img, (panel.centerx - img.get_width() / 2, panel.y + 8 * s))

    y = panel.y + 28 * s
    for line in lines:
        for wrapped in wrap_text(line, body_font, panel.width - 20 * s):
            img = body_font.render(wrapped, True, (240, 230, 210))
            surface.blit(img, (panel.centerx - img.get_width() / 2, y))
            y += 11 * s
        y += 4 * s

    hint = body_font.render("[E] close", True, (180, 170, 150))
    surface.blit(
        hint, (panel.centerx - hint.get_width() / 2, panel.bottom - 13 * s)
    )
