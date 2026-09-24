import pygame

# Fraction of the window width the allegory side panel covers.
PANEL_FRACTION = 0.4
# Allegory panel palette: yellowed old paper with dark ink.
PAPER = (222, 202, 150)
PAPER_EDGE = (120, 90, 50)
INK_TITLE = (110, 40, 30)
INK = (55, 40, 28)
INK_FAINT = (125, 105, 75)

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


def draw_dialogue_box(surface, speaker, text, scale=1, hint=None):
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
        font.render("[E]", True, (200, 200, 200)),
        (rect.right - 12 * s, rect.bottom - 11 * s),
    )
    if hint:
        surface.blit(
            font.render(hint, True, (180, 180, 200)),
            (rect.x + 6 * s, rect.bottom - 11 * s),
        )


def draw_confirm_box(surface, question, options, choice, scale=1):
    """Dialogue-style box with a question and a row of choices; the
    selected one is highlighted with a cursor."""
    s = scale
    margin, box_h = 4 * s, 56 * s
    w, h = surface.get_size()
    rect = pygame.Rect(margin, h - box_h - margin, w - 2 * margin, box_h)
    pygame.draw.rect(surface, (16, 16, 28), rect)
    pygame.draw.rect(surface, (230, 230, 240), rect, max(1, round(1 * s)))

    font = _font(10 * s)
    y = rect.y + 5 * s
    for line in wrap_text(question, font, rect.width - 12 * s):
        surface.blit(font.render(line, True, (240, 240, 240)), (rect.x + 6 * s, y))
        y += 10 * s

    x = rect.x + 14 * s
    y = rect.bottom - 14 * s
    for i, label in enumerate(options):
        selected = i == choice
        color = (255, 220, 120) if selected else (170, 170, 185)
        if selected:
            surface.blit(font.render(">", True, color), (x - 8 * s, y))
        text = font.render(label, True, color)
        surface.blit(text, (x, y))
        x += text.get_width() + 24 * s


def draw_transition(surface, text, scale=1):
    surface.fill((0, 0, 0))
    font = _font(14 * scale)
    img = font.render(text, True, (240, 240, 240))
    w, h = surface.get_size()
    surface.blit(img, ((w - img.get_width()) / 2, (h - img.get_height()) / 2))


def credits_height(lines, scale=1):
    """Total pixel height of the credits roll (see draw_credits)."""
    return sum(_credit_line_height(line, scale) for line in lines)


def _credit_line_height(line, scale):
    if line.startswith("#"):
        return 20 * scale
    return 12 * scale


def draw_credits(surface, lines, scroll, scale=1):
    """Film-style rolling credits on black.

    `lines` come from data/credits.json: "# Heading" draws a bigger gold
    heading, "" leaves a gap, anything else is a normal centered line.
    `scroll` is how many pixels the roll has moved up; at 0 the first
    line is just below the bottom edge.
    """
    s = scale
    surface.fill((0, 0, 0))
    w, h = surface.get_size()
    heading_font, body_font = _font(16 * s), _font(10 * s)
    y = h - scroll
    for line in lines:
        line_h = _credit_line_height(line, s)
        if line and -line_h < y < h:
            if line.startswith("#"):
                img = heading_font.render(line.lstrip("# "), True, (255, 220, 120))
            else:
                img = body_font.render(line, True, (240, 240, 240))
            surface.blit(img, ((w - img.get_width()) / 2, y))
        y += line_h


def draw_scene_panel(surface, title, lines, scale=1, hint=None):
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

    footer = "[E] close" + ("   " + hint if hint else "")
    img = body_font.render(footer, True, (180, 170, 150))
    surface.blit(
        img, (panel.centerx - img.get_width() / 2, panel.bottom - 13 * s)
    )


def draw_allegory_panel(surface, title, text, t, scroll, scale=1):
    """Soviet-allegory side panel sliding in from the right edge.

    `t` is 0..1 slide progress (eased here), `scroll` the body scroll
    offset in px. Returns the overflow in px (max useful scroll).
    """
    s = scale
    w, h = surface.get_size()
    panel_w = round(w * PANEL_FRACTION)
    e = 1 - (1 - t) ** 2
    panel = pygame.Rect(round(w - panel_w * e), 0, panel_w, h)
    # Old-paper look: parchment fill, a darker worn edge, and ink text.
    pygame.draw.rect(surface, PAPER, panel)
    pygame.draw.rect(surface, PAPER_EDGE, (panel.x, 0, max(1, round(3 * s)), h))

    title_font = _font(11 * s)
    body_font = _font(8 * s)
    text_w = panel_w - 12 * s

    y = panel.y + 8 * s
    for line in wrap_text(title, title_font, text_w):
        surface.blit(
            title_font.render(line, True, INK_TITLE),
            (panel.x + 6 * s, y),
        )
        y += 12 * s
    pygame.draw.line(
        surface, PAPER_EDGE,
        (panel.x + 6 * s, y + 2 * s), (panel.right - 6 * s, y + 2 * s), max(1, round(s)),
    )

    body_y = y + 6 * s
    body_top = body_y
    body_bottom = panel.bottom - 13 * s
    lines = wrap_text(text, body_font, text_w)
    prev_clip = surface.get_clip()
    surface.set_clip((panel.x, body_top, panel.width, body_bottom - body_top))
    for line in lines:
        surface.blit(
            body_font.render(line, True, INK),
            (panel.x + 6 * s, body_y - scroll),
        )
        body_y += 9 * s
    surface.set_clip(prev_clip)

    overflow = max(0, (body_y - body_top) - (body_bottom - body_top))
    footer = "[Q] close" + ("  Up/Down: scroll" if overflow > 0 else "")
    surface.blit(
        body_font.render(footer, True, INK_FAINT),
        (panel.x + 6 * s, panel.bottom - 13 * s),
    )
    return overflow
