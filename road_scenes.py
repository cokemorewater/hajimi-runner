"""Multi-scene top-down roads (suburb / desert / coast). Full-screen cached bitmaps."""

from __future__ import annotations

import math
from enum import IntEnum

import pygame

from constants import HEIGHT, LANE_COUNT, LANE_MARGIN_X, SCENE_SEGMENT_METERS, WIDTH
from cat_player import lane_center_x, lane_width


class RoadScene(IntEnum):
    SUBURB = 0
    DESERT = 1
    COAST = 2


def scene_name_cn(scene: RoadScene) -> str:
    return {
        RoadScene.SUBURB: "城郊公路",
        RoadScene.DESERT: "沙漠公路",
        RoadScene.COAST: "海岸公路",
    }[scene]


_SCENE_PROGRESSION: tuple[RoadScene, ...] = (
    RoadScene.SUBURB,
    RoadScene.DESERT,
    RoadScene.COAST,
)

_PARALLAX_SCROLL_FACTOR: float = 1.4


def scene_for_distance(meters: float) -> RoadScene:
    """场景随奔跑距离增加按 城郊→沙漠→海岸 循环切换。"""
    if SCENE_SEGMENT_METERS <= 0:
        return RoadScene.SUBURB
    idx = int(meters // SCENE_SEGMENT_METERS) % len(_SCENE_PROGRESSION)
    return _SCENE_PROGRESSION[idx]


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_rgb(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(_lerp(c1[0], c2[0], t)),
        int(_lerp(c1[1], c2[1], t)),
        int(_lerp(c1[2], c2[2], t)),
    )


def _paint_lane_lines(
    surf: pygame.Surface,
    lw: float,
    dash_rgb: tuple[int, int, int],
    edge_rgb: tuple[int, int, int],
    edge_inner: tuple[int, int, int],
) -> None:
    dash, gap = 26, 18
    for k in range(1, LANE_COUNT):
        cx = int(LANE_MARGIN_X + k * lw)
        y = 0
        while y < HEIGHT:
            pygame.draw.line(surf, dash_rgb, (cx, y), (cx, min(y + dash, HEIGHT)), 3)
            y += dash + gap
    lx, rx = LANE_MARGIN_X, WIDTH - LANE_MARGIN_X
    pygame.draw.line(surf, edge_rgb, (lx, 0), (lx, HEIGHT), 4)
    pygame.draw.line(surf, edge_inner, (lx + 2, 0), (lx + 2, HEIGHT), 1)
    pygame.draw.line(surf, edge_rgb, (rx, 0), (rx, HEIGHT), 4)
    pygame.draw.line(surf, edge_inner, (rx - 2, 0), (rx - 2, HEIGHT), 1)


def _paint_lane_wear(surf: pygame.Surface, lw: float) -> None:
    inner = max(24, int(lw) - 16)
    for i in range(LANE_COUNT):
        cx = int(lane_center_x(i))
        wy = pygame.Rect(cx - inner // 2, 0, inner, HEIGHT)
        patch = pygame.Surface((wy.width, wy.height), pygame.SRCALPHA)
        for yy in range(0, HEIGHT, 120):
            pygame.draw.ellipse(patch, (0, 0, 0, 12), pygame.Rect(4, yy, wy.width - 8, 70))
        surf.blit(patch, wy.topleft)


def _noise_road(surf: pygame.Surface, road_rect: pygame.Rect, base: int, spread: int) -> None:
    for y in range(0, HEIGHT, 5):
        for x in range(road_rect.left, road_rect.right, 6):
            n = (x * 1103515245 + y) & 0xFF
            if n > 210:
                c = base + (n % spread)
                pygame.draw.rect(surf, (c, c, c + 1), (x, y, 2, 2))


def _rng01(i: int, side: int) -> float:
    return ((i * 7919 + side * 104729) % 10000) / 10000.0


def _tree(surf: pygame.Surface, cx: int, cy: int, scale: float) -> None:
    s = scale
    trunk = pygame.Rect(int(cx - 3 * s), int(cy - 2 * s), int(6 * s), int(18 * s))
    pygame.draw.rect(surf, (62, 44, 30), trunk)
    pygame.draw.rect(surf, (48, 34, 24), trunk, 1)
    r0 = int(14 * s)
    pygame.draw.circle(surf, (38, 92, 48), (cx, int(cy - 12 * s)), r0)
    pygame.draw.circle(surf, (52, 118, 62), (cx, int(cy - 16 * s)), int(11 * s))
    pygame.draw.circle(surf, (72, 140, 78), (cx, int(cy - 20 * s)), int(7 * s))


def _bush(surf: pygame.Surface, cx: int, cy: int) -> None:
    pygame.draw.ellipse(surf, (48, 100, 52), (cx - 14, cy - 6, 28, 16))
    pygame.draw.ellipse(surf, (62, 120, 66), (cx - 10, cy - 10, 20, 14))


def _cactus(surf: pygame.Surface, cx: int, cy: int) -> None:
    pygame.draw.ellipse(surf, (55, 110, 65), (cx - 8, cy - 28, 16, 52))
    pygame.draw.ellipse(surf, (42, 92, 55), (cx - 9, cy - 29, 18, 54), 2)
    pygame.draw.ellipse(surf, (55, 110, 65), (cx - 22, cy - 12, 14, 10))
    pygame.draw.ellipse(surf, (55, 110, 65), (cx + 8, cy - 18, 14, 10))


def _rock(surf: pygame.Surface, cx: int, cy: int, r: int) -> None:
    pts = [
        (cx - r, cy + r // 2),
        (cx - r // 2, cy - r),
        (cx + r, cy - r // 3),
        (cx + r // 2, cy + r),
    ]
    pygame.draw.polygon(surf, (120, 110, 98), pts)
    pygame.draw.polygon(surf, (88, 82, 74), pts, 2)


def _palm(surf: pygame.Surface, cx: int, cy: int) -> None:
    pygame.draw.rect(surf, (95, 72, 48), (cx - 3, cy - 4, 6, 26))
    top = (cx, cy - 8)
    for ang in (-0.9, -0.45, 0, 0.45, 0.9):
        ex = int(top[0] + math.cos(ang - math.pi / 2) * 22)
        ey = int(top[1] + math.sin(ang - math.pi / 2) * 22)
        pygame.draw.line(surf, (48, 110, 72), top, (ex, ey), 4)
        pygame.draw.line(surf, (72, 140, 88), top, (ex, ey), 2)


def _shell(surf: pygame.Surface, cx: int, cy: int) -> None:
    pygame.draw.arc(surf, (245, 230, 210), (cx - 8, cy - 4, 16, 12), 3.3, 6.5, 2)
    pygame.draw.line(surf, (210, 195, 180), (cx - 2, cy + 2), (cx + 4, cy - 2), 1)


def _paint_roadside_scenery(surf: pygame.Surface, scene: RoadScene, scroll_offset: float = 0.0) -> None:
    """Decorations in the wide shoulder (not on drivable asphalt)."""
    curb = 10
    left_max = LANE_MARGIN_X - curb - 8
    right_cx_min = WIDTH - LANE_MARGIN_X + 24
    right_cx_max = WIDTH - 22

    parallax = scroll_offset * _PARALLAX_SCROLL_FACTOR

    for i in range(8):
        y = 70 + i * 118 + int(_rng01(i, 0) * 40)
        y = (y + parallax * 0.4) % (HEIGHT + 80) - 40
        u = _rng01(i, 1)
        lx = int(22 + u * max(6, left_max - 50))
        rx = int(right_cx_min + u * max(8, right_cx_max - right_cx_min))
        rx = min(rx, right_cx_max)

        if scene == RoadScene.SUBURB:
            if i % 3 != 1:
                _tree(surf, lx, y, 0.85 + 0.3 * _rng01(i, 2))
            else:
                _bush(surf, lx, y)
            if i % 2 == 0:
                _tree(surf, rx, y + 20, 0.75 + 0.25 * _rng01(i, 3))
            else:
                _bush(surf, rx, y - 10)
        elif scene == RoadScene.DESERT:
            if i % 2 == 0:
                _cactus(surf, lx, y)
            else:
                _rock(surf, lx, y, 8 + int(6 * _rng01(i, 2)))
            _rock(surf, rx, y + 10, 6 + int(5 * _rng01(i, 3)))
        else:
            _palm(surf, lx, y)
            if i % 2 == 0:
                _shell(surf, max(14, lx - 10), y + 32)
            _palm(surf, rx, y - 15)
            _rock(surf, rx - 10, y + 28, 5)


def build_road(scene: RoadScene) -> pygame.Surface:
    surf = pygame.Surface((WIDTH, HEIGHT))
    lw = lane_width()
    road_rect = pygame.Rect(LANE_MARGIN_X, 0, WIDTH - 2 * LANE_MARGIN_X, HEIGHT)

    if scene == RoadScene.SUBURB:
        surf.fill((28, 32, 36))
        grass_l = pygame.Rect(0, 0, LANE_MARGIN_X - 8, HEIGHT)
        grass_r = pygame.Rect(WIDTH - (LANE_MARGIN_X - 8), 0, LANE_MARGIN_X - 8, HEIGHT)
        g_dark, g_mid, g_light = (32, 58, 38), (44, 82, 48), (52, 98, 56)
        for r in (grass_l, grass_r):
            for y in range(r.height):
                t = y / max(1, HEIGHT - 1)
                c = _lerp_rgb(g_dark, g_light, 0.35 + 0.65 * t)
                pygame.draw.line(surf, c, (r.left, r.top + y), (r.right - 1, r.top + y))
            for y in range(0, r.height, 6):
                for x in range(r.left, r.right, 7):
                    h = (x * 928371 + y * 31337) % 100
                    if h > 72:
                        v = 8 + (h % 12)
                        surf.set_at((x, r.top + y), (g_mid[0] + v, g_mid[1] + v // 2, g_mid[2] + v // 3))
        curb_w = 10
        pygame.draw.rect(surf, (88, 90, 86), pygame.Rect(LANE_MARGIN_X - curb_w, 0, curb_w, HEIGHT))
        pygame.draw.rect(surf, (88, 90, 86), pygame.Rect(WIDTH - LANE_MARGIN_X, 0, curb_w, HEIGHT))
        pygame.draw.line(surf, (118, 118, 114), (LANE_MARGIN_X - curb_w + 1, 0), (LANE_MARGIN_X - curb_w + 1, HEIGHT), 2)
        pygame.draw.line(
            surf,
            (70, 72, 68),
            (WIDTH - LANE_MARGIN_X + curb_w - 2, 0),
            (WIDTH - LANE_MARGIN_X + curb_w - 2, HEIGHT),
            2,
        )
        a_top, a_bot = (46, 46, 48), (38, 38, 42)
        for y in range(road_rect.height):
            t = y / max(1, road_rect.height - 1)
            row_c = _lerp_rgb(a_top, a_bot, t)
            pygame.draw.line(surf, row_c, (road_rect.left, y), (road_rect.right - 1, y))
        wear = pygame.Surface((road_rect.width, road_rect.height), pygame.SRCALPHA)
        for x in range(road_rect.width):
            nx = x / max(1, road_rect.width - 1)
            dist = abs(nx - 0.5) * 2
            alpha = int(28 * (1 - dist * dist))
            if alpha > 0:
                pygame.draw.line(wear, (255, 255, 255, alpha), (x, 0), (x, road_rect.height - 1))
        surf.blit(wear, road_rect.topleft)
        _noise_road(surf, road_rect, 50, 8)
        _paint_lane_lines(surf, lw, (235, 238, 242), (250, 252, 255), (210, 212, 218))
        _paint_lane_wear(surf, lw)

    elif scene == RoadScene.DESERT:
        surf.fill((210, 175, 130))
        sand_l = pygame.Rect(0, 0, LANE_MARGIN_X - 8, HEIGHT)
        sand_r = pygame.Rect(WIDTH - (LANE_MARGIN_X - 8), 0, LANE_MARGIN_X - 8, HEIGHT)
        s1, s2 = (198, 160, 105), (165, 125, 78)
        for r in (sand_l, sand_r):
            for y in range(r.height):
                t = y / max(1, HEIGHT - 1)
                c = _lerp_rgb(s2, s1, 0.2 + 0.8 * t)
                pygame.draw.line(surf, c, (r.left, y), (r.right - 1, y))
            for y in range(0, r.height, 8):
                for x in range(r.left, r.right, 9):
                    if (x + y * 3) % 17 == 0:
                        pygame.draw.circle(surf, (140, 110, 70), (x, r.top + y), 2)
            # distant dunes line
            for i in range(3):
                yy = 120 + i * 280
                pygame.draw.arc(surf, (180, 145, 95), pygame.Rect(-40, yy, WIDTH + 80, 80), 0.1, 2.8, 2)
        curb_w = 10
        pygame.draw.rect(surf, (160, 135, 100), pygame.Rect(LANE_MARGIN_X - curb_w, 0, curb_w, HEIGHT))
        pygame.draw.rect(surf, (160, 135, 100), pygame.Rect(WIDTH - LANE_MARGIN_X, 0, curb_w, HEIGHT))
        d_top, d_bot = (200, 168, 118), (168, 138, 92)
        for y in range(road_rect.height):
            t = y / max(1, road_rect.height - 1)
            row_c = _lerp_rgb(d_top, d_bot, t)
            pygame.draw.line(surf, row_c, (road_rect.left, y), (road_rect.right - 1, y))
        for y in range(0, HEIGHT, 7):
            for x in range(road_rect.left, road_rect.right, 5):
                n = (x * 333 + y) % 55
                if n < 4:
                    pygame.draw.rect(surf, (150, 120, 80), (x, y, 2, 2))
        _paint_lane_lines(surf, lw, (255, 230, 160), (255, 245, 210), (220, 190, 140))
        _paint_lane_wear(surf, lw)

    else:  # COAST
        surf.fill((24, 48, 72))
        water_l = pygame.Rect(0, 0, LANE_MARGIN_X - 8, HEIGHT)
        water_r = pygame.Rect(WIDTH - (LANE_MARGIN_X - 8), 0, LANE_MARGIN_X - 8, HEIGHT)
        w1, w2 = (30, 88, 118), (18, 62, 98)
        for r in (water_l, water_r):
            for y in range(r.height):
                t = y / max(1, HEIGHT - 1)
                c = _lerp_rgb(w2, w1, 0.25 + 0.75 * t)
                pygame.draw.line(surf, c, (r.left, y), (r.right - 1, y))
            for y in range(0, r.height, 4):
                for x in range(r.left, r.right, 11):
                    if (x * 7 + y * 13) % 23 < 3:
                        pygame.draw.rect(surf, (200, 220, 235), (x, r.top + y, 3, 1))
        # wet sand band
        pygame.draw.rect(surf, (190, 175, 150), pygame.Rect(LANE_MARGIN_X - 14, 0, 14, HEIGHT))
        pygame.draw.rect(surf, (190, 175, 150), pygame.Rect(WIDTH - LANE_MARGIN_X, 0, 14, HEIGHT))
        curb_w = 10
        pygame.draw.rect(surf, (120, 118, 112), pygame.Rect(LANE_MARGIN_X - curb_w, 0, curb_w, HEIGHT))
        pygame.draw.rect(surf, (120, 118, 112), pygame.Rect(WIDTH - LANE_MARGIN_X, 0, curb_w, HEIGHT))
        a_top, a_bot = (72, 74, 78), (52, 54, 58)
        for y in range(road_rect.height):
            t = y / max(1, road_rect.height - 1)
            row_c = _lerp_rgb(a_top, a_bot, t)
            pygame.draw.line(surf, row_c, (road_rect.left, y), (road_rect.right - 1, y))
        wear = pygame.Surface((road_rect.width, road_rect.height), pygame.SRCALPHA)
        for x in range(road_rect.width):
            nx = x / max(1, road_rect.width - 1)
            dist = abs(nx - 0.5) * 2
            alpha = int(22 * (1 - dist * dist))
            if alpha > 0:
                pygame.draw.line(wear, (200, 210, 220, alpha), (x, 0), (x, road_rect.height - 1))
        surf.blit(wear, road_rect.topleft)
        _noise_road(surf, road_rect, 58, 7)
        _paint_lane_lines(surf, lw, (248, 252, 255), (255, 255, 255), (200, 205, 210))
        _paint_lane_wear(surf, lw)

    _paint_roadside_scenery(surf, scene)
    return surf
