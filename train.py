"""Cargo truck obstacle (top-down); logic same as before, drawn as a realistic hauler."""

import random

import pygame

from assets import get_current_scene, load_train_sprite
from constants import (
    TRAIN_MAX_HEIGHT,
    TRAIN_MIN_HEIGHT,
    TRAIN_WIDTH,
)
from cat_player import lane_center_x


class Train:
    """Top-down box truck / semi-style hauler (game still calls it Train internally)."""

    def __init__(self, lane: int, speed: float) -> None:
        h = random.randint(TRAIN_MIN_HEIGHT, TRAIN_MAX_HEIGHT)
        self.rect = pygame.Rect(0, 0, TRAIN_WIDTH, h)
        self.rect.centerx = int(lane_center_x(lane))
        self.rect.bottom = -10
        self.lane = lane
        self.speed = speed
        self._sprite = load_train_sprite(get_current_scene())
        self._cab_h = max(34, int(h * 0.24))
        self._trailer_color = (
            random.randint(52, 68),
            random.randint(58, 74),
            random.randint(72, 88),
        )
        self._cab_color = (
            random.randint(34, 44),
            random.randint(38, 48),
            random.randint(44, 54),
        )

    def update(self) -> None:
        self.rect.y += int(self.speed)

    def is_off_screen(self, height: int) -> bool:
        return self.rect.top > height + 20

    def draw(self, surface: pygame.Surface) -> None:
        r = self.rect
        if self._sprite is not None:
            scaled = pygame.transform.smoothscale(self._sprite, (r.width, r.height))
            surface.blit(scaled, (r.x, r.y))
            return

        cab_h = self._cab_h

        # vehicle shadow
        sh = pygame.Surface((r.width + 10, r.height + 10), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 55), sh.get_rect(), border_radius=10)
        surface.blit(sh, (r.x - 3, r.y + 5))

        trailer = pygame.Rect(r.x + 4, r.y + 6, r.width - 8, r.height - cab_h - 10)
        cab = pygame.Rect(r.x + 6, r.bottom - cab_h - 4, r.width - 12, cab_h)

        # --- trailer: corrugated metal look ---
        pygame.draw.rect(surface, self._trailer_color, trailer, border_radius=4)
        pygame.draw.rect(surface, (20, 22, 26), trailer, 2, border_radius=4)
        stripe_w = 14
        for x in range(trailer.left + stripe_w, trailer.right - 2, stripe_w):
            shade = tuple(max(0, c - 12) for c in self._trailer_color)
            pygame.draw.line(surface, shade, (x, trailer.top + 4), (x, trailer.bottom - 4), 2)
        # roof edge highlight
        pygame.draw.line(
            surface,
            tuple(min(255, c + 35) for c in self._trailer_color),
            (trailer.left + 3, trailer.top + 3),
            (trailer.right - 4, trailer.top + 3),
            2,
        )
        # rear roll door line (top of vehicle = back when moving down — still reads as detail)
        pygame.draw.line(
            surface,
            (28, 30, 34),
            (trailer.centerx - 18, trailer.top + 10),
            (trailer.centerx + 18, trailer.top + 10),
            2,
        )

        # --- cab ---
        pygame.draw.rect(surface, self._cab_color, cab, border_radius=3)
        pygame.draw.rect(surface, (12, 14, 18), cab, 2, border_radius=3)
        wind = pygame.Rect(cab.left + 6, cab.top + 5, cab.width - 12, int(cab.height * 0.42))
        pygame.draw.rect(surface, (110, 168, 210), wind, border_radius=2)
        pygame.draw.rect(surface, (40, 52, 68), wind, 1, border_radius=2)
        # windshield split
        pygame.draw.line(
            surface,
            (28, 40, 56),
            (wind.centerx, wind.top + 1),
            (wind.centerx, wind.bottom - 1),
            1,
        )
        # roof fairing
        fair = pygame.Rect(cab.centerx - cab.width // 4, cab.top - 6, cab.width // 2, 8)
        pygame.draw.rect(surface, tuple(min(255, c + 18) for c in self._cab_color), fair, border_radius=2)

        # --- wheels (duals on each side, 3 axles) ---
        wheel_col = (28, 28, 30)
        hub = (90, 92, 96)
        ys = [
            trailer.top + int(trailer.height * 0.28),
            trailer.top + int(trailer.height * 0.62),
            cab.centery + 4,
        ]
        for wy in ys:
            for dx in (10, r.width - 10):
                cx = r.left + dx
                pygame.draw.circle(surface, wheel_col, (cx, wy), 9)
                pygame.draw.circle(surface, (10, 10, 12), (cx, wy), 9, 2)
                pygame.draw.circle(surface, hub, (cx, wy), 4)

        # --- bumper / lights ---
        pygame.draw.rect(
            surface,
            (52, 54, 58),
            (cab.left + 4, cab.bottom - 5, cab.width - 8, 5),
            border_radius=1,
        )
        pygame.draw.circle(surface, (255, 240, 120), (cab.left + 10, cab.bottom - 3), 3)
        pygame.draw.circle(surface, (255, 120, 90), (cab.right - 10, cab.bottom - 3), 3)
