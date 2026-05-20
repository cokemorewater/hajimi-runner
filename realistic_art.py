"""Road bitmap cache: doubled vertical strip for seamless scrolling (see road_scenes)."""

from __future__ import annotations

import math

import pygame

from assets import load_road_texture
from constants import HEIGHT, WIDTH
from road_scenes import RoadScene, _paint_roadside_scenery, build_road

_strip_cache: dict[tuple[RoadScene, int], pygame.Surface] = {}
_bg_strip_cache: dict[RoadScene, pygame.Surface] = {}

_SCENE_FILE_NAMES = {
    RoadScene.SUBURB: "suburb",
    RoadScene.DESERT: "desert",
    RoadScene.COAST: "coast",
}


def _scale_to_fill(surface: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
    sw, sh = surface.get_size()
    if sw == target_w and sh == target_h:
        return surface
    scale = max(target_w / sw, target_h / sh)
    new_w = int(sw * scale)
    new_h = int(sh * scale)
    scaled = pygame.transform.smoothscale(surface, (new_w, new_h))
    crop_x = (new_w - target_w) // 2
    crop_y = (new_h - target_h) // 2
    cropped = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
    cropped.blit(scaled, (0, 0), (crop_x, crop_y, target_w, target_h))
    return cropped


def road_scroll_strip(scene: RoadScene, road_index: int = 0, scroll_offset: float = 0.0) -> pygame.Surface:
    """Two identical full-screen tiles stacked (height 2×HEIGHT) for wrap-around scroll."""
    parallax = scroll_offset * 1.4
    base_y = int(parallax) % (HEIGHT * 2)

    key = (scene, road_index)
    if key not in _strip_cache:
        tile = load_road_texture(_SCENE_FILE_NAMES.get(scene, scene.name.lower()), road_index)
        if tile is None:
            tile = build_road(scene)
        else:
            if tile.get_size() != (WIDTH, HEIGHT):
                tile = pygame.transform.smoothscale(tile, (WIDTH, HEIGHT))
        big = pygame.Surface((WIDTH, HEIGHT * 2))
        big.blit(tile, (0, 0))
        big.blit(tile, (0, HEIGHT))
        _strip_cache[key] = big

    return _strip_cache[key]


def road_background_strip(scene: RoadScene, scroll_offset: float = 0.0) -> pygame.Surface:
    """Background scenery layer with parallax scrolling (slower than road)."""
    parallax = scroll_offset * 0.6
    tile_h = HEIGHT * 2
    base_y = int(parallax) % tile_h

    cache_key = f"{scene.name}_{int(parallax) // 60}"
    if cache_key not in _bg_strip_cache:
        tile = pygame.Surface((WIDTH, tile_h))
        tile.fill((0, 0, 0, 0))
        tile.set_colorkey((0, 0, 0))
        _paint_roadside_scenery(tile, scene, 0)
        _bg_strip_cache[cache_key] = tile

    return _bg_strip_cache[cache_key]

def invalidate_road_cache() -> None:
    _strip_cache.clear()
    _bg_strip_cache.clear()