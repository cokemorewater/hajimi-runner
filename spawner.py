"""Spawns trains at random lanes with distance-based difficulty."""

import math
import random
import time

from constants import (
    LANE_COUNT,
    SPAWN_DISTANCE_SHRINK,
    SPAWN_MIN_INTERVAL_MS,
    SPAWN_START_INTERVAL_MS,
    TRAIN_BASE_SPEED,
    TRAIN_COIN_MIN_Y,
    TRAIN_LANE_COOLDOWN_S,
    TRAIN_OBSTACLE_MIN_Y,
    TRAIN_SPEED_DISTANCE_FACTOR,
)
from train import Train


class TrainSpawner:
    def __init__(self) -> None:
        self._next_spawn_at = time.monotonic() + 0.8
        self._spawn_interval_ms = SPAWN_START_INTERVAL_MS
        self._lane_cooldown_until: list[float] = [0.0, 0.0, 0.0]

    def reset(self) -> None:
        self._next_spawn_at = time.monotonic() + 0.8
        self._spawn_interval_ms = SPAWN_START_INTERVAL_MS
        self._lane_cooldown_until = [0.0, 0.0, 0.0]

    @staticmethod
    def current_speed(distance_m: float) -> float:
        return TRAIN_BASE_SPEED + (math.sqrt(distance_m + 100) - 10) * TRAIN_SPEED_DISTANCE_FACTOR

    @staticmethod
    def spawn_interval_ms(distance_m: float) -> float:
        return max(SPAWN_MIN_INTERVAL_MS, SPAWN_START_INTERVAL_MS - distance_m * SPAWN_DISTANCE_SHRINK)

    def update(self, now: float, dt: float, distance_m: float, coins: list, obstacles: list) -> Train | None:
        speed = self.current_speed(distance_m)
        self._spawn_interval_ms = self.spawn_interval_ms(distance_m)

        if now < self._next_spawn_at:
            return None

        available_lanes = [i for i in range(LANE_COUNT) if now >= self._lane_cooldown_until[i]]
        if not available_lanes:
            return None

        lane = random.choice(available_lanes)

        candidate = Train(lane=lane, speed=speed)

        for coin in coins:
            if abs(coin.lane - lane) <= 1 and abs(candidate.rect.centery - coin.y) < TRAIN_COIN_MIN_Y:
                return None

        for obs in obstacles:
            if abs(obs.lane - lane) <= 1 and abs(candidate.rect.centery - obs.rect.centery) < TRAIN_OBSTACLE_MIN_Y:
                return None

        gap = self._spawn_interval_ms / 1000.0
        self._next_spawn_at = now + gap
        self._lane_cooldown_until[lane] = now + TRAIN_LANE_COOLDOWN_S
        return candidate