"""Day–night cycle: celestial body + color grading overlay (0..1 = one full day)."""

from __future__ import annotations

import math

import pygame

from constants import WIDTH


def time_label_cn(day_t: float) -> str:
    """Rough phase label for HUD."""
    t = day_t % 1.0
    if t < 0.22:
        return "深夜"
    if t < 0.32:
        return "黎明"
    if t < 0.42:
        return "清晨"
    if t < 0.58:
        return "正午"
    if t < 0.68:
        return "午后"
    if t < 0.78:
        return "黄昏"
    if t < 0.9:
        return "傍晚"
    return "月夜"


def draw_sky_gradient(surface: pygame.Surface, day_t: float) -> None:
    h = 80
    t = day_t % 1.0
    if t < 0.25:
        c_top = _mix((12, 18, 42), (40, 55, 95), t / 0.25)
        c_bot = _mix((28, 38, 72), (85, 110, 150), t / 0.25)
    elif t < 0.35:
        u = (t - 0.25) / 0.1
        c_top = _mix((40, 55, 95), (255, 140, 90), u)
        c_bot = _mix((85, 110, 150), (255, 200, 140), u)
    elif t < 0.65:
        u = (t - 0.35) / 0.3
        c_top = _mix((255, 140, 90), (120, 185, 255), u)
        c_bot = _mix((255, 200, 140), (190, 225, 255), u)
    elif t < 0.78:
        u = (t - 0.65) / 0.13
        c_top = _mix((120, 185, 255), (255, 110, 60), u)
        c_bot = _mix((190, 225, 255), (255, 170, 90), u)
    else:
        u = (t - 0.78) / 0.22
        c_top = _mix((255, 110, 60), (15, 22, 48), u)
        c_bot = _mix((255, 170, 90), (35, 48, 82), u)

    for y in range(h):
        k = y / max(1, h - 1)
        c = _mix(c_top, c_bot, k)
        pygame.draw.line(surface, c, (0, y), (WIDTH, y))


def _mix(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    u: float,
) -> tuple[int, int, int]:
    u = max(0.0, min(1.0, u))
    return (int(a[0] + (b[0] - a[0]) * u), int(a[1] + (b[1] - a[1]) * u), int(a[2] + (b[2] - a[2]) * u))


def draw_celestial(surface: pygame.Surface, day_t: float) -> None:
    t = day_t % 1.0
    if 0.26 <= t <= 0.74:
        u = (t - 0.26) / (0.74 - 0.26)
        sx = int(WIDTH * (0.12 + 0.76 * u))
        sy = int(32 + 28 * math.sin(u * math.pi))
        for r, a in ((36, 25), (28, 55), (18, 120)):
            g = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(g, (255, 240, 200, a), (r, r), r)
            surface.blit(g, (sx - r, sy - r))
        pygame.draw.circle(surface, (255, 252, 235), (sx, sy), 12)
    else:
        mx = int(WIDTH * (0.72 if t < 0.5 else 0.28))
        my = 36
        pygame.draw.circle(surface, (235, 240, 255), (mx, my), 16)
        pygame.draw.circle(surface, (200, 208, 218), (mx - 5, my - 3), 3)
        pygame.draw.circle(surface, (200, 208, 218), (mx + 6, my + 5), 2)


def apply_lighting_overlay(surface: pygame.Surface, day_t: float) -> None:
    """Full-screen tint for dawn / noon / dusk / night."""
    t = day_t % 1.0
    ovl = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

    if t < 0.22:
        a = int(20 + (0.22 - t) / 0.22 * 85)
        ovl.fill((18, 28, 58, min(130, a)))
    elif t < 0.34:
        u = (t - 0.22) / 0.12
        ovl.fill((255, 150, 110, int(42 * (1 - u))))
    elif t < 0.62:
        u = (t - 0.34) / 0.28
        ovl.fill((255, 252, 245, int(6 + 10 * math.sin(u * math.pi))))
    elif t < 0.78:
        u = (t - 0.62) / 0.16
        ovl.fill((190, 85, 95, int(52 * u)))
    else:
        u = (t - 0.78) / 0.22
        ovl.fill((25, 35, 75, int(40 + 70 * u)))

    surface.blit(ovl, (0, 0))
