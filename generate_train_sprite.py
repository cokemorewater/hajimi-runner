"""Generate example train sprites (multiple color variants) for external import."""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pygame

from constants import TRAIN_MIN_HEIGHT, TRAIN_WIDTH

pygame.init()

OUT_DIR = os.path.join(_ROOT, "assets", "trains")
os.makedirs(OUT_DIR, exist_ok=True)

SCALE = 2
W = TRAIN_WIDTH * SCALE
H = TRAIN_MIN_HEIGHT * SCALE
CAB_H = max(34, int(H * 0.24))

VARIANTS = [
    {"name": "train_0", "trailer": (60, 66, 80), "cab": (39, 43, 49)},
    {"name": "train_1", "trailer": (180, 50, 40), "cab": (140, 35, 30)},
    {"name": "train_2", "trailer": (40, 90, 60), "cab": (28, 65, 42)},
]


def draw_train(surface: pygame.Surface, trailer_color: tuple, cab_color: tuple) -> None:
    w, h = surface.get_size()
    cab_h = CAB_H

    # shadow
    sh = pygame.Surface((w + 10, h + 10), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 55), sh.get_rect(), border_radius=10)
    surface.blit(sh, (-3, 5))

    trailer = pygame.Rect(4, 6, w - 8, h - cab_h - 10)
    cab = pygame.Rect(6, h - cab_h - 4, w - 12, cab_h)

    # trailer
    pygame.draw.rect(surface, trailer_color, trailer, border_radius=4)
    pygame.draw.rect(surface, (20, 22, 26), trailer, 2, border_radius=4)
    stripe_w = 14
    for x in range(trailer.left + stripe_w, trailer.right - 2, stripe_w):
        shade = tuple(max(0, c - 12) for c in trailer_color)
        pygame.draw.line(surface, shade, (x, trailer.top + 4), (x, trailer.bottom - 4), 2)
    pygame.draw.line(
        surface,
        tuple(min(255, c + 35) for c in trailer_color),
        (trailer.left + 3, trailer.top + 3),
        (trailer.right - 4, trailer.top + 3),
        2,
    )
    pygame.draw.line(
        surface, (28, 30, 34),
        (trailer.centerx - 18, trailer.top + 10),
        (trailer.centerx + 18, trailer.top + 10),
        2,
    )

    # cab
    pygame.draw.rect(surface, cab_color, cab, border_radius=3)
    pygame.draw.rect(surface, (12, 14, 18), cab, 2, border_radius=3)
    wind = pygame.Rect(cab.left + 6, cab.top + 5, cab.width - 12, int(cab.height * 0.42))
    pygame.draw.rect(surface, (110, 168, 210), wind, border_radius=2)
    pygame.draw.rect(surface, (40, 52, 68), wind, 1, border_radius=2)
    pygame.draw.line(surface, (28, 40, 56), (wind.centerx, wind.top + 1), (wind.centerx, wind.bottom - 1), 1)

    fair = pygame.Rect(cab.centerx - cab.width // 4, cab.top - 6, cab.width // 2, 8)
    pygame.draw.rect(surface, tuple(min(255, c + 18) for c in cab_color), fair, border_radius=2)

    # wheels
    wheel_col = (28, 28, 30)
    hub = (90, 92, 96)
    ys = [
        trailer.top + int(trailer.height * 0.28),
        trailer.top + int(trailer.height * 0.62),
        cab.centery + 4,
    ]
    for wy in ys:
        for dx in (10, w - 10):
            pygame.draw.circle(surface, wheel_col, (dx, wy), 9)
            pygame.draw.circle(surface, (10, 10, 12), (dx, wy), 9, 2)
            pygame.draw.circle(surface, hub, (dx, wy), 4)

    # bumper / lights
    pygame.draw.rect(surface, (52, 54, 58), (cab.left + 4, cab.bottom - 5, cab.width - 8, 5), border_radius=1)
    pygame.draw.circle(surface, (255, 240, 120), (cab.left + 10, cab.bottom - 3), 3)
    pygame.draw.circle(surface, (255, 120, 90), (cab.right - 10, cab.bottom - 3), 3)


for v in VARIANTS:
    surface = pygame.Surface((W, H), pygame.SRCALPHA)
    draw_train(surface, v["trailer"], v["cab"])
    out_path = os.path.join(OUT_DIR, f"{v['name']}.png")
    pygame.image.save(surface, out_path)
    print(f"Generated: {out_path} ({W}x{H})")

pygame.quit()