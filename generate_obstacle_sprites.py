"""Generate example obstacle sprites for external import."""

import os
import random
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pygame

from constants import OBSTACLE_HIGH_GAP, OBSTACLE_HIGH_HEIGHT, OBSTACLE_LOW_HEIGHT, OBSTACLE_WIDTH

pygame.init()

OUT_DIR = os.path.join(_ROOT, "assets", "obstacles")
os.makedirs(OUT_DIR, exist_ok=True)


def draw_rock(surface: pygame.Surface, r: pygame.Rect) -> None:
    dark = (80, 70, 60)
    mid = (120, 105, 90)
    light = (160, 140, 120)

    shadow = r.inflate(4, 2)
    shadow.bottom = r.bottom + 2
    pygame.draw.ellipse(surface, (20, 18, 16), shadow)

    pygame.draw.ellipse(surface, dark, r)
    inner = r.inflate(-8, -6)
    pygame.draw.ellipse(surface, mid, inner)
    highlight = pygame.Rect(r.x + r.w // 4, r.y + 4, r.w // 3, r.h // 3)
    pygame.draw.ellipse(surface, light, highlight)

    random.seed(42)
    for _ in range(3):
        cx = r.x + random.randint(r.w // 4, 3 * r.w // 4)
        cy = r.y + random.randint(r.h // 4, 3 * r.h // 4)
        sz = random.randint(2, 4)
        pygame.draw.circle(surface, light, (cx, cy), sz)


def draw_barrier(surface: pygame.Surface, r: pygame.Rect) -> None:
    pole_color = (100, 95, 85)
    bar_color = (200, 60, 40)
    bar_light = (240, 80, 50)
    bar_dark = (150, 40, 25)
    stripe_color = (250, 230, 100)

    pole_w = 6
    left_pole = pygame.Rect(r.centerx - r.w // 2 + 2, r.y + OBSTACLE_HIGH_GAP, pole_w, r.h - OBSTACLE_HIGH_GAP)
    right_pole = pygame.Rect(r.centerx + r.w // 2 - pole_w - 2, r.y + OBSTACLE_HIGH_GAP, pole_w, r.h - OBSTACLE_HIGH_GAP)
    pygame.draw.rect(surface, pole_color, left_pole)
    pygame.draw.rect(surface, pole_color, right_pole)

    bar_rect = pygame.Rect(r.x, r.y, r.w, OBSTACLE_HIGH_GAP)
    pygame.draw.rect(surface, bar_dark, bar_rect)
    bar_inner = bar_rect.inflate(-4, -4)
    pygame.draw.rect(surface, bar_color, bar_inner)
    bar_top = pygame.Rect(bar_inner.x, bar_inner.y, bar_inner.w, bar_inner.h // 2)
    pygame.draw.rect(surface, bar_light, bar_top)

    stripe_count = 4
    stripe_w = bar_inner.w // stripe_count
    for i in range(stripe_count):
        sx = bar_inner.x + i * stripe_w + stripe_w // 4
        stripe = pygame.Rect(sx, bar_inner.y + 2, stripe_w // 2, bar_inner.h - 4)
        if i % 2 == 0:
            pygame.draw.rect(surface, stripe_color, stripe)

    arrow_size = 8
    arrow_x = r.centerx
    arrow_y = r.y + OBSTACLE_HIGH_GAP - arrow_size
    pygame.draw.polygon(surface, (255, 255, 255), [
        (arrow_x, arrow_y + arrow_size),
        (arrow_x - arrow_size // 2, arrow_y),
        (arrow_x + arrow_size // 2, arrow_y),
    ])


scale = 2
low_w = OBSTACLE_WIDTH * scale
low_h = OBSTACLE_LOW_HEIGHT * scale
low_surf = pygame.Surface((low_w, low_h), pygame.SRCALPHA)
draw_rock(low_surf, pygame.Rect(0, 0, low_w, low_h))
pygame.image.save(low_surf, os.path.join(OUT_DIR, "low.png"))
print(f"Generated: {os.path.join(OUT_DIR, 'low.png')} ({low_w}x{low_h})")

high_w = OBSTACLE_WIDTH * scale
high_h = OBSTACLE_HIGH_HEIGHT * scale
high_surf = pygame.Surface((high_w, high_h), pygame.SRCALPHA)
draw_barrier(high_surf, pygame.Rect(0, 0, high_w, high_h))
pygame.image.save(high_surf, os.path.join(OUT_DIR, "high.png"))
print(f"Generated: {os.path.join(OUT_DIR, 'high.png')} ({high_w}x{high_h})")

pygame.quit()