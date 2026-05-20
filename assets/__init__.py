"""Asset loading with per-scene override support.

Directory layout
----------------
assets/
  cats/             -- cat sprites (global)
  roads/            -- road textures (global fallback)
  obstacles/        -- obstacle sprites (global fallback)
  trains/           -- train sprites (global fallback)
  maps/
    {scene_name}/
      roads/
        road_0.png     -- scene-specific road variants
        ...
      obstacles/
        low.png        -- scene-specific low obstacle
        high.png       -- scene-specific high obstacle
      trains/
        train_0.png    -- scene-specific train variants
        ...
"""

import glob
import os
import random
import sys

import pygame

_ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    _ASSETS_DIR = os.path.join(sys._MEIPASS, 'assets')
_CAT_SPRITES: dict[str, pygame.Surface | None] = {}
_CAT_SHEET_FRAMES: dict[str, dict[str, list[pygame.Surface]]] = {}
_ROAD_SPRITES: dict[str, list[pygame.Surface]] = {}
_OBSTACLE_SPRITES: dict[str, pygame.Surface | None] = {}
_TRAIN_SPRITES: dict[str, list[pygame.Surface]] = {}

_current_scene: str = ""
SUPPORTED_EXTENSIONS = ["png", "webp"]


def set_current_scene(scene: str) -> None:
    global _current_scene
    _current_scene = scene


def get_current_scene() -> str:
    return _current_scene


def _maps_dir(scene: str = "") -> str:
    base = os.path.join(_ASSETS_DIR, "maps")
    if scene:
        base = os.path.join(base, scene)
    return base


def _resolve_path(*candidates: str) -> str | None:
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def clear_cache() -> None:
    _CAT_SPRITES.clear()
    _CAT_SHEET_FRAMES.clear()
    _ROAD_SPRITES.clear()
    _OBSTACLE_SPRITES.clear()
    _TRAIN_SPRITES.clear()


def clear_road_cache() -> None:
    _ROAD_SPRITES.clear()


def cat_sprite_path(name: str) -> str:
    for ext in SUPPORTED_EXTENSIONS:
        path = os.path.join(_ASSETS_DIR, "cats", f"{name}.{ext}")
        if os.path.isfile(path):
            return path
    return os.path.join(_ASSETS_DIR, "cats", f"{name}.png")


def cat_sheet_path(name: str) -> str:
    for ext in SUPPORTED_EXTENSIONS:
        path = os.path.join(_ASSETS_DIR, "cats", f"{name}_sheet.{ext}")
        if os.path.isfile(path):
            return path
    return os.path.join(_ASSETS_DIR, "cats", f"{name}_sheet.png")


def load_cat_sprite(name: str) -> pygame.Surface | None:
    if name in _CAT_SPRITES:
        return _CAT_SPRITES[name]
    path = cat_sprite_path(name)
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            _CAT_SPRITES[name] = img
            return img
        except pygame.error:
            pass
    _CAT_SPRITES[name] = None
    return None


def load_cat_preview_sprite(name: str) -> pygame.Surface | None:
    return load_cat_sprite(name)


def load_cat_action_sprite(name: str, action: str) -> pygame.Surface | None:
    key = f"{name}_{action}"
    if key in _CAT_SPRITES:
        return _CAT_SPRITES[key]
    path = os.path.join(_ASSETS_DIR, "cats", f"{name}_{action}.png")
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            _CAT_SPRITES[key] = img
            return img
        except pygame.error:
            pass
    _CAT_SPRITES[key] = None
    return None


def load_cat_sprite_sheet(name: str) -> pygame.Surface | None:
    key = f"{name}_sheet"
    if key in _CAT_SPRITES:
        return _CAT_SPRITES[key]
    path = cat_sheet_path(name)
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path)
            try:
                img = img.convert_alpha()
            except pygame.error:
                img = img.convert()
            _CAT_SPRITES[key] = img
            return img
        except Exception:
            pass
    _CAT_SPRITES[key] = None
    return None


_SHEET_ACTIONS = ["run", "jump", "slide"]
_DEFAULT_FRAME_SIZE = 70


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def _detect_frame_size(iw: int, ih: int) -> tuple[int, int] | None:
    if iw <= 0 or ih <= 0:
        return None
    for rows in (3, 5, 4, 2, 1):
        if ih % rows != 0:
            continue
        base_h = ih // rows
        for offset in range(-5, 6):
            frame_h = base_h + offset
            if frame_h < 16 or frame_h > 256:
                continue
            if iw % frame_h != 0:
                continue
            cols = iw // frame_h
            if cols < 1 or cols > 30:
                continue
            return frame_h, frame_h
    return None


def _center_content(surface: pygame.Surface) -> pygame.Surface:
    """将帧中的非透明内容居中到帧中心，消除帧间内容位置偏移。"""
    w, h = surface.get_size()
    sum_x = 0
    sum_y = 0
    count = 0
    for y in range(h):
        for x in range(w):
            try:
                if surface.get_at((x, y))[3] > 10:
                    sum_x += x
                    sum_y += y
                    count += 1
            except Exception:
                pass
    if count == 0:
        return surface
    cx = sum_x / count
    cy = sum_y / count
    dx = int(w // 2 - cx)
    dy = int(h // 2 - cy)
    if dx == 0 and dy == 0:
        return surface
    new_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    new_surf.blit(surface, (dx, dy))
    return new_surf


def load_cat_sheet_frames(name: str) -> dict[str, list[pygame.Surface]]:
    """Parse a sprite sheet PNG into frames dict.

    Expected format:
      - Single PNG image: rows = actions, columns = frames
      - Row 0: run frames (running animation)
      - Row 1: jump frames (jumping animation)
      - Row 2: slide frames (sliding animation)
      - All rows must have the same number of frames (columns)
      - Standard frame size: 70x70 pixels
      - Minimum sheet: 70x70 (1 frame each), standard: 350x210 (5 frames each)

    Auto-detects any frame size. Falls back to empty dict if sheet not found.

    Returns: {"run": [Surface, ...], "jump": [...], "slide": [...]}
    """
    key = f"{name}_sheet_frames"
    if key in _CAT_SHEET_FRAMES:
        return _CAT_SHEET_FRAMES[key]

    img = load_cat_sprite_sheet(name)
    if img is None:
        _CAT_SHEET_FRAMES[key] = {}
        return {}

    iw, ih = img.get_size()
    frame_size = _detect_frame_size(iw, ih)
    if frame_size is None:
        _CAT_SHEET_FRAMES[key] = {}
        return {}

    frame_w, frame_h = frame_size
    cols = iw // frame_w
    rows = ih // frame_h

    # 验证检测到的帧是否合理：检查四个角是否有透明像素
    # 无效的精灵表（如全不透明图片）会导致错误帧
    corners_ok = False
    for cx, cy in ((0, 0), (iw - 1, 0), (0, ih - 1), (iw - 1, ih - 1)):
        try:
            if img.get_at((cx, cy))[3] <= 10:
                corners_ok = True
                break
        except Exception:
            pass
    if not corners_ok:
        # 四个角都不透明，可能不是有效精灵表
        _CAT_SHEET_FRAMES[key] = {}
        return {}

    frames: dict[str, list[pygame.Surface]] = {}
    for row_idx, action in enumerate(_SHEET_ACTIONS):
        if row_idx >= rows:
            break
        row_frames: list[pygame.Surface] = []
        for col in range(cols):
            rect = pygame.Rect(col * frame_w, row_idx * frame_h, frame_w, frame_h)
            raw = img.subsurface(rect).copy()
            # 将每一帧的内容居中到帧的中心，
            # 避免不同帧中猫咪位置不同导致播放时身体左右跳动
            row_frames.append(_center_content(raw))
        frames[action] = row_frames

    _CAT_SHEET_FRAMES[key] = frames
    return frames


def road_texture_path(name: str) -> str:
    return os.path.join(_ASSETS_DIR, "roads", f"{name}.png")


def load_road_sprites(scene: str) -> list[pygame.Surface]:
    key = f"road_{scene}"
    if key in _ROAD_SPRITES:
        return _ROAD_SPRITES[key]

    sprites: list[pygame.Surface] = []
    scene_pattern = os.path.join(_maps_dir(scene), "roads", "*.png")
    scene_single = os.path.join(_maps_dir(scene), "road.png")
    global_path = road_texture_path(scene)

    paths = sorted(glob.glob(scene_pattern))
    if not paths and os.path.isfile(scene_single):
        paths = [scene_single]
    if not paths and os.path.isfile(global_path):
        paths = [global_path]

    for path in paths:
        try:
            img = pygame.image.load(path).convert_alpha()
            sprites.append(img)
        except pygame.error:
            pass

    _ROAD_SPRITES[key] = sprites
    return sprites


def load_road_texture(name: str, index: int = 0) -> pygame.Surface | None:
    sprites = load_road_sprites(name)
    if not sprites:
        return None
    return sprites[index % len(sprites)]


def obstacle_sprite_path(obs_type: str) -> str:
    return os.path.join(_ASSETS_DIR, "obstacles", f"{obs_type}.png")


def load_obstacle_sprite(scene: str, obs_type: str) -> pygame.Surface | None:
    key = f"obs_{scene}_{obs_type}"
    if key in _OBSTACLE_SPRITES:
        return _OBSTACLE_SPRITES[key]

    scene_path = os.path.join(_maps_dir(scene), "obstacles", f"{obs_type}.png")
    global_path = obstacle_sprite_path(obs_type)
    resolved = _resolve_path(scene_path, global_path)
    if resolved:
        try:
            img = pygame.image.load(resolved).convert_alpha()
            _OBSTACLE_SPRITES[key] = img
            return img
        except pygame.error:
            pass
    _OBSTACLE_SPRITES[key] = None
    return None


def clear_obstacle_cache() -> None:
    _OBSTACLE_SPRITES.clear()


def load_train_sprites(scene: str) -> list[pygame.Surface]:
    key = f"train_{scene}"
    if key in _TRAIN_SPRITES:
        return _TRAIN_SPRITES[key]

    sprites: list[pygame.Surface] = []
    scene_pattern = os.path.join(_maps_dir(scene), "trains", "*.png")
    global_pattern = os.path.join(_ASSETS_DIR, "trains", "*.png")

    paths = sorted(glob.glob(scene_pattern))
    if not paths:
        paths = sorted(glob.glob(global_pattern))

    for path in paths:
        try:
            img = pygame.image.load(path).convert_alpha()
            sprites.append(img)
        except pygame.error:
            pass

    _TRAIN_SPRITES[key] = sprites
    return sprites


def load_train_sprite(scene: str) -> pygame.Surface | None:
    sprites = load_train_sprites(scene)
    if not sprites:
        return None
    return random.choice(sprites)


def clear_train_cache() -> None:
    _TRAIN_SPRITES.clear()