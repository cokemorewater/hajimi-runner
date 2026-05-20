from __future__ import annotations

import math
import random
import time

import pygame

from constants import COIN_OBSTACLE_MIN_Y, HEIGHT, LANE_COUNT, LANE_MARGIN_X, TRAIN_COIN_MIN_Y, WIDTH
from cat_player import lane_center_x

COIN_SIZE = 24
COIN_SPAWN_MIN_MS = 800
COIN_SPAWN_MAX_MS = 2000
_COIN_GLOW = 0.0


class Coin:
    def __init__(self, lane: int, y: float, speed: float) -> None:
        self.lane = lane
        cx = lane_center_x(lane)
        self.x = cx
        self.y = y
        self.speed = speed
        self.collected = False
        self.birth = time.monotonic()

    def update(self, dt: float) -> None:
        self.y += self.speed

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - COIN_SIZE // 2), int(self.y - COIN_SIZE // 2), COIN_SIZE, COIN_SIZE)

    def is_off_screen(self) -> bool:
        return self.y > HEIGHT + COIN_SIZE

    def draw(self, surface: pygame.Surface) -> None:
        global _COIN_GLOW
        _COIN_GLOW += 0.05
        r = COIN_SIZE // 2
        cx, cy = int(self.x), int(self.y)

        pulse = 1.0 + 0.08 * math.sin(_COIN_GLOW * 3.0 + self.birth)
        pr = int(r * pulse)

        glow_surf = pygame.Surface((pr * 3, pr * 3), pygame.SRCALPHA)
        glow_alpha = int(40 + 15 * math.sin(_COIN_GLOW * 3.0 + self.birth))
        pygame.draw.circle(glow_surf, (255, 220, 80, glow_alpha), (pr * 3 // 2, pr * 3 // 2), int(pr * 1.5))
        surface.blit(glow_surf, (cx - pr * 3 // 2, cy - pr * 3 // 2))

        pygame.draw.circle(surface, (220, 170, 30), (cx, cy), pr + 2)
        pygame.draw.circle(surface, (255, 215, 50), (cx, cy), pr)
        pygame.draw.circle(surface, (255, 235, 120), (cx - pr // 3, cy - pr // 3), pr // 2)

        sparkle = int(40 + 30 * math.sin(_COIN_GLOW * 5.0 + self.birth * 2.0))
        spark_color = (255, 255, 220, sparkle)
        spark_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
        spark_surf.fill(spark_color)
        surface.blit(spark_surf, (cx - pr + 2, cy - pr + 2))


class CoinSpawner:
    def __init__(self) -> None:
        self._next_spawn = time.monotonic() + random.uniform(0.5, 1.5)

    def update(self, now: float, speed: float, obstacles: list, trains: list) -> Coin | None:
        if now >= self._next_spawn:
            for _ in range(5):
                lane = random.randint(0, LANE_COUNT - 1)
                coin_y = random.uniform(-80, -20)

                overlap = False
                for obs in obstacles:
                    if abs(obs.lane - lane) <= 1 and abs(coin_y - obs.rect.centery) < COIN_OBSTACLE_MIN_Y:
                        overlap = True
                        break
                if not overlap:
                    for t in trains:
                        if abs(t.lane - lane) <= 1 and abs(coin_y - t.rect.centery) < TRAIN_COIN_MIN_Y:
                            overlap = True
                            break
                if not overlap:
                    coin = Coin(lane, coin_y, speed)
                    interval = random.uniform(COIN_SPAWN_MIN_MS / 1000.0, COIN_SPAWN_MAX_MS / 1000.0)
                    self._next_spawn = now + interval
                    return coin

            self._next_spawn = now + 0.3
        return None


def apply_magnet(player_rect: pygame.Rect, coins: list[Coin], magnet_range: float, dt: float) -> None:
    if magnet_range <= 0:
        return
    pcx, pcy = player_rect.center
    for coin in coins:
        if coin.collected:
            continue
        dx = pcx - coin.x
        dy = pcy - coin.y
        dist = math.hypot(dx, dy)
        if dist < magnet_range and dist > 1:
            pull = min(300.0, magnet_range / max(dist, 1)) * dt * 2.0
            coin.x += dx / dist * pull
            coin.y += dy / dist * pull