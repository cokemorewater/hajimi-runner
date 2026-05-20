"""Obstacles: low barriers (jump over) and high barriers (slide under)."""

from __future__ import annotations

import enum
import math
import random

import pygame

from assets import get_current_scene, load_obstacle_sprite
from cat_player import lane_center_x
from constants import (
    COIN_OBSTACLE_MIN_Y,
    HEIGHT,
    OBSTACLE_DISTANCE_SHRINK,
    OBSTACLE_HIGH_GAP,
    OBSTACLE_HIGH_HEIGHT,
    OBSTACLE_LANE_COOLDOWN_S,
    OBSTACLE_LOW_HEIGHT,
    OBSTACLE_MIN_Y_GAP,
    OBSTACLE_SPAWN_MAX_FLOOR_S,
    OBSTACLE_SPAWN_MAX_S,
    OBSTACLE_SPAWN_MIN_FLOOR_S,
    OBSTACLE_SPAWN_MIN_S,
    OBSTACLE_WIDTH,
    TRAIN_OBSTACLE_MIN_Y,
)


class ObstacleType(enum.Enum):
    LOW = 0
    HIGH = 1


class Obstacle:
    def __init__(self, lane: int, speed: float, obs_type: ObstacleType) -> None:
        self.lane = lane
        self.speed = speed
        self.obs_type = obs_type
        self.passed: bool = False

        cx = int(lane_center_x(lane))
        if obs_type == ObstacleType.LOW:
            h = random.randint(OBSTACLE_LOW_HEIGHT - 10, OBSTACLE_LOW_HEIGHT + 10)
        else:
            h = random.randint(OBSTACLE_HIGH_HEIGHT - 20, OBSTACLE_HIGH_HEIGHT + 20)

        self.rect = pygame.Rect(0, 0, OBSTACLE_WIDTH, h)
        self.rect.centerx = cx
        self.rect.bottom = -10

        self._color_variant = random.uniform(0.9, 1.0)

    def update(self) -> None:
        self.rect.y += int(self.speed)

    def is_off_screen(self) -> bool:
        return self.rect.top > HEIGHT + 30

    def collision_rect(self) -> pygame.Rect:
        if self.obs_type == ObstacleType.HIGH:
            r = self.rect.copy()
            r.height = 22
            return r
        return self.rect

    def draw(self, surface: pygame.Surface) -> None:
        r = self.rect
        obs_key = "low" if self.obs_type == ObstacleType.LOW else "high"
        sprite = load_obstacle_sprite(get_current_scene(), obs_key)
        if sprite is not None:
            scaled = pygame.transform.smoothscale(sprite, (r.width, r.height))
            surface.blit(scaled, (r.x, r.y))
            return
        if self.obs_type == ObstacleType.LOW:
            self._draw_rock(surface, r)
        else:
            self._draw_barrier(surface, r)

    def _draw_rock(self, surface: pygame.Surface, r: pygame.Rect) -> None:
        v = self._color_variant
        dark = (int(80 * v), int(70 * v), int(60 * v))
        mid = (int(120 * v), int(105 * v), int(90 * v))
        light = (int(160 * v), int(140 * v), int(120 * v))

        shadow = r.inflate(4, 2)
        shadow.bottom = r.bottom + 2
        pygame.draw.ellipse(surface, (20, 18, 16), shadow)

        pygame.draw.ellipse(surface, dark, r)
        inner = r.inflate(-8, -6)
        pygame.draw.ellipse(surface, mid, inner)
        highlight = pygame.Rect(r.x + r.w // 4, r.y + 4, r.w // 3, r.h // 3)
        pygame.draw.ellipse(surface, light, highlight)

        for i in range(3):
            cx = r.x + random.randint(r.w // 4, 3 * r.w // 4)
            cy = r.y + random.randint(r.h // 4, 3 * r.h // 4)
            sz = random.randint(2, 4)
            pygame.draw.circle(surface, light, (cx, cy), sz)

    def _draw_barrier(self, surface: pygame.Surface, r: pygame.Rect) -> None:
        v = self._color_variant
        pole_color = (int(100 * v), int(95 * v), int(85 * v))
        bar_color = (int(200 * v), int(60 * v), int(40 * v))
        bar_light = (int(240 * v), int(80 * v), int(50 * v))
        bar_dark = (int(150 * v), int(40 * v), int(25 * v))
        stripe_color = (int(250 * v), int(230 * v), int(100 * v))

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


class ObstacleSpawner:
    def __init__(self) -> None:
        self._next_spawn: float = 0.0
        self._lane_cooldown_until: list[float] = [0.0, 0.0, 0.0]

    def reset(self) -> None:
        self._next_spawn = 0.0
        self._lane_cooldown_until = [0.0, 0.0, 0.0]

    def update(self, now: float, speed: float, distance_m: float, obstacles: list[Obstacle], coins: list, trains: list) -> Obstacle | None:
        if now < self._next_spawn:
            return None

        min_s = max(OBSTACLE_SPAWN_MIN_FLOOR_S, OBSTACLE_SPAWN_MIN_S - distance_m * OBSTACLE_DISTANCE_SHRINK)
        max_s = max(OBSTACLE_SPAWN_MAX_FLOOR_S, OBSTACLE_SPAWN_MAX_S - distance_m * OBSTACLE_DISTANCE_SHRINK * 2)

        available_lanes = [i for i in range(3) if now >= self._lane_cooldown_until[i]]
        if not available_lanes:
            return None

        lane = random.choice(available_lanes)
        obs_type = random.choice([ObstacleType.LOW, ObstacleType.HIGH])

        candidate = Obstacle(lane=lane, speed=speed, obs_type=obs_type)

        for obs in obstacles:
            if abs(candidate.rect.bottom - obs.rect.top) < OBSTACLE_MIN_Y_GAP:
                return None

        for coin in coins:
            if abs(coin.lane - lane) <= 1 and abs(candidate.rect.bottom - coin.y) < COIN_OBSTACLE_MIN_Y:
                return None

        for t in trains:
            if abs(t.lane - lane) <= 1 and abs(candidate.rect.bottom - t.rect.top) < TRAIN_OBSTACLE_MIN_Y:
                return None

        gap = random.uniform(min_s, max_s)
        self._next_spawn = now + gap
        self._lane_cooldown_until[lane] = now + OBSTACLE_LANE_COOLDOWN_S
        return candidate