"""Cat: three lanes; top-down facing road forward (−Y), diagonal trot animation."""

from __future__ import annotations

import math

import pygame

from assets import load_cat_sprite, load_cat_action_sprite, load_cat_sprite_sheet, load_cat_sheet_frames
from constants import (
    HEIGHT,
    JUMP_COOLDOWN,
    JUMP_DURATION,
    JUMP_HEIGHT,
    LANE_COUNT,
    PLAYER_SIZE,
    SLIDE_COOLDOWN,
    SLIDE_DURATION,
    WIDTH,
)

_ROAD_SCENE_LANES: dict[str, list[int]] = {
    "SUBURB": [278, 360, 457],
    "DESERT": [283, 366, 454],
    "COAST": [283, 365, 453],
}
_current_road_scene: str = "DESERT"


def set_road_scene(scene_name: str) -> None:
    global _current_road_scene
    if scene_name in _ROAD_SCENE_LANES:
        _current_road_scene = scene_name


def _lane_centers() -> list[int]:
    return _ROAD_SCENE_LANES.get(_current_road_scene, [200, 360, 458])


def drivable_width() -> float:
    centers = _lane_centers()
    if len(centers) < 2:
        return 280.0
    half = (centers[1] - centers[0]) / 2
    return float(centers[-1] - centers[0] + 2 * half)


def lane_width() -> float:
    centers = _lane_centers()
    if len(centers) < 2:
        return 93.0
    gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
    return float(sum(gaps) / len(gaps))


def lane_center_x(lane: int) -> float:
    centers = _lane_centers()
    if 0 <= lane < len(centers):
        return float(centers[lane])
    return float(WIDTH / 2)


class Player:
    PLAYER_Y_FRAC: float = 0.82

    def __init__(self) -> None:
        self.lane = LANE_COUNT // 2
        w, h = PLAYER_SIZE
        self.rect = pygame.Rect(0, 0, w, h)
        self._sync_position()

        self.skill_name: str = ""
        self.skill_cooldown: float = 0.0
        self.skill_cooldown_max: float = 30.0
        self.skill_duration: float = 0.0
        self.skill_duration_max: float = 3.0
        self.skill_active: bool = False
        self._skill_base_speed: float = 1.0
        self._skill_base_dodge: float = 0.0
        self._skill_base_coin: float = 1.0
        self._skill_base_magnet: float = 0.0
        self.speed_multiplier: float = 1.0
        self.dodge_chance: float = 0.0
        self.coin_multiplier: float = 1.0
        self.coin_magnet_extra: float = 0.0
        self.night_speed_bonus: bool = False
        self.invincible: bool = False
        self.shield: bool = False
        self.jumping: bool = False
        self.jump_timer: float = 0.0
        self.jump_cooldown_timer: float = 0.0
        self.sliding: bool = False
        self.slide_timer: float = 0.0
        self.slide_cooldown_timer: float = 0.0
        self.skill_flash_timer: float = 0.0

    def _sync_position(self) -> None:
        cx = lane_center_x(self.lane)
        cy = int(HEIGHT * self.PLAYER_Y_FRAC)
        self.rect.center = (int(cx), cy)

    def move_left(self) -> None:
        if self.lane > 0:
            self.lane -= 1
            self._sync_position()

    def move_right(self) -> None:
        if self.lane < LANE_COUNT - 1:
            self.lane += 1
            self._sync_position()

    def start_jump(self) -> bool:
        if self.jumping or self.sliding or self.jump_cooldown_timer > 0:
            return False
        self.jumping = True
        self.jump_timer = 0.0
        return True

    def start_slide(self) -> bool:
        if self.jumping or self.sliding or self.slide_cooldown_timer > 0:
            return False
        self.sliding = True
        self.slide_timer = 0.0
        return True

    @property
    def skill_ready(self) -> bool:
        return self.skill_cooldown_max > 0 and self.skill_cooldown <= 0 and not self.skill_active

    def activate_skill(self) -> bool:
        if not self.skill_ready:
            return False
        self._skill_base_speed = self.speed_multiplier
        self._skill_base_dodge = self.dodge_chance
        self._skill_base_coin = self.coin_multiplier
        self._skill_base_magnet = self.coin_magnet_extra
        self.skill_active = True
        self.skill_duration = self.skill_duration_max
        self.skill_flash_timer = 0.5
        return True

    def update_action(self, dt: float) -> None:
        if self.jumping:
            self.jump_timer += dt
            if self.jump_timer >= JUMP_DURATION:
                self.jumping = False
                self.jump_cooldown_timer = JUMP_COOLDOWN
        if self.sliding:
            self.slide_timer += dt
            if self.slide_timer >= SLIDE_DURATION:
                self.sliding = False
                self.slide_cooldown_timer = SLIDE_COOLDOWN
        if self.jump_cooldown_timer > 0:
            self.jump_cooldown_timer = max(0.0, self.jump_cooldown_timer - dt)
        if self.slide_cooldown_timer > 0:
            self.slide_cooldown_timer = max(0.0, self.slide_cooldown_timer - dt)
        if self.skill_flash_timer > 0:
            self.skill_flash_timer = max(0.0, self.skill_flash_timer - dt)

    @property
    def jump_offset(self) -> float:
        if not self.jumping:
            return 0.0
        progress = self.jump_timer / JUMP_DURATION
        return -JUMP_HEIGHT * math.sin(progress * math.pi)

    @property
    def slide_hitbox_scale(self) -> float:
        if not self.sliding:
            return 1.0
        progress = self.slide_timer / SLIDE_DURATION
        return 0.35 + 0.15 * math.sin(progress * math.pi)

    _CAT_GAME_SIZE = (70, 70)

    def draw(self, surface: pygame.Surface, run_phase: float, anim_scale: float, color: tuple[int, int, int] = (232, 140, 60), name: str = "") -> None:
        cx, cy = self.rect.center
        jump_y = int(self.jump_offset)
        slide_scale = self.slide_hitbox_scale

        if self.jumping:
            self._draw_jump(surface, cx, cy, jump_y, color, name)
        elif self.sliding:
            self._draw_slide(surface, cx, cy, slide_scale, color, name)
        else:
            self._draw_run(surface, cx, cy, run_phase, color, name)

    def _try_action_sprite(self, name: str, action: str) -> pygame.Surface | None:
        if not name:
            return None
        sprite = load_cat_action_sprite(name, action)
        if sprite is not None:
            return sprite
        return load_cat_sprite(name)

    def _get_sheet_frame(self, name: str, action: str, progress: float) -> pygame.Surface | None:
        if not name:
            return None
        frames_dict = load_cat_sheet_frames(name)
        if action in frames_dict:
            frames = frames_dict[action]
            if frames:
                n = len(frames)
                # 乒乓播放：0→1→2→...→n-1→n-2→...→1→0→1→...
                cycle = n * 2 - 2
                if cycle < 1:
                    cycle = 1
                pos = progress * cycle
                idx = int(pos) % cycle
                if idx >= n:
                    idx = cycle - idx
                return frames[idx]
        return None

    def _draw_run(self, surface: pygame.Surface, cx: int, cy: int, run_phase: float, color: tuple[int, int, int], name: str) -> None:
        progress = run_phase % 1.0
        sheet_frame = self._get_sheet_frame(name, "run", progress)
        if sheet_frame is not None:
            x = cx - sheet_frame.get_width() // 2
            y = cy - sheet_frame.get_height() // 2
            surface.blit(sheet_frame, (x, y))
            return
        sprite = self._try_action_sprite(name, "run")
        if sprite is not None:
            p = run_phase * 2.0 * math.pi
            bob = 1.2 * math.sin(p * 2.0)
            scaled = pygame.transform.smoothscale(sprite, Player._CAT_GAME_SIZE)
            x = cx - scaled.get_width() // 2
            y = cy + int(bob) - scaled.get_height() // 2
            surface.blit(scaled, (x, y))
            return
        self._draw_run_procedural(surface, cx, cy, run_phase, color)

    def _draw_jump(self, surface: pygame.Surface, cx: int, cy: int, jump_y: int, color: tuple[int, int, int], name: str) -> None:
        progress = self.jump_timer / JUMP_DURATION if JUMP_DURATION > 0 else 0.0
        progress = progress * 0.5
        sheet_frame = self._get_sheet_frame(name, "jump", progress)
        if sheet_frame is not None:
            x = cx - sheet_frame.get_width() // 2
            y = cy + jump_y - sheet_frame.get_height() // 2
            surface.blit(sheet_frame, (x, y))
            return
        sprite = self._try_action_sprite(name, "jump")
        if sprite is not None:
            scaled = pygame.transform.smoothscale(sprite, Player._CAT_GAME_SIZE)
            x = cx - scaled.get_width() // 2
            y = cy + jump_y - scaled.get_height() // 2
            surface.blit(scaled, (x, y))
            return
        self._draw_jump_procedural(surface, cx, cy + jump_y, color)

    def _draw_slide(self, surface: pygame.Surface, cx: int, cy: int, slide_scale: float, color: tuple[int, int, int], name: str) -> None:
        progress = self.slide_timer / SLIDE_DURATION if SLIDE_DURATION > 0 else 0.0
        progress = progress * 0.5
        sheet_frame = self._get_sheet_frame(name, "slide", progress)
        if sheet_frame is not None:
            fw, fh = sheet_frame.get_size()
            x = cx - fw // 2
            y = cy - fh // 2
            surface.blit(sheet_frame, (x, y))
            return
        sprite = self._try_action_sprite(name, "slide")
        if sprite is not None:
            w = Player._CAT_GAME_SIZE[0]
            h = int(Player._CAT_GAME_SIZE[1] * slide_scale)
            scaled = pygame.transform.smoothscale(sprite, (w, h))
            x = cx - scaled.get_width() // 2
            y = cy - scaled.get_height() // 2
            surface.blit(scaled, (x, y))
            return
        self._draw_slide_procedural(surface, cx, cy, slide_scale, color)

    def _fur_colors(self, color: tuple[int, int, int]) -> dict[str, tuple[int, int, int]]:
        r, g, b = color
        return {
            "dark": (max(0, r - 60), max(0, g - 40), max(0, b - 25)),
            "mid": color,
            "light": (min(255, r + 30), min(255, g + 30), min(255, b + 20)),
            "hi": (min(255, r + 50), min(255, g + 50), min(255, b + 50)),
            "belly": (min(255, r + 20), min(255, g + 30), min(255, b + 40)),
        }

    @staticmethod
    def _paw(surface: pygame.Surface, color: tuple[int, int, int], x: float, y: float) -> None:
        pygame.draw.ellipse(surface, color, (int(x - 4), int(y - 2), 9, 10))
        pygame.draw.ellipse(surface, (48, 38, 30), (int(x - 2), int(y + 3), 5, 4))

    @staticmethod
    def _draw_head(surface: pygame.Surface, hx: int, hy: int, head_r: int, fc: dict, pink: tuple[int, int, int], sf: float, ear_flat: bool = False) -> None:
        pygame.draw.circle(surface, fc["mid"], (hx, hy), head_r)
        pygame.draw.circle(surface, fc["light"], (hx, hy - 1), head_r - 5)
        pygame.draw.circle(surface, fc["dark"], (hx, hy), head_r, 2)

        if ear_flat:
            ear_l = [(hx - head_r + 2, hy - 2), (hx - head_r - 8, hy + 2), (hx - 6, hy - head_r + 6)]
            ear_r = [(hx + head_r - 2, hy - 2), (hx + head_r + 8, hy + 2), (hx + 6, hy - head_r + 6)]
        else:
            ear_l = [(hx - head_r + 1, hy), (hx - head_r - 7, hy - head_r - 1), (hx - 5, hy - head_r + 3)]
            ear_r = [(hx + head_r - 1, hy), (hx + head_r + 7, hy - head_r - 1), (hx + 5, hy - head_r + 3)]

        pygame.draw.polygon(surface, fc["mid"], ear_l)
        pygame.draw.polygon(surface, fc["mid"], ear_r)
        pygame.draw.polygon(surface, pink, [(ear_l[0][0], ear_l[0][1] + 1), ear_l[1], (ear_l[2][0], ear_l[2][1] - 3)])
        pygame.draw.polygon(surface, pink, [(ear_r[0][0], ear_r[0][1] + 1), ear_r[1], (ear_r[2][0], ear_r[2][1] - 3)])
        pygame.draw.polygon(surface, fc["dark"], ear_l, 2)
        pygame.draw.polygon(surface, fc["dark"], ear_r, 2)

        eye_h = hy - 1 if ear_flat else hy - 1
        pygame.draw.ellipse(surface, (248, 250, 252), (hx - 13, eye_h - 6, 9, 10))
        pygame.draw.ellipse(surface, (248, 250, 252), (hx + 4, eye_h - 6, 9, 10))
        pygame.draw.circle(surface, (32, 38, 48), (hx - 8, eye_h - 1), int(3.2 * sf))
        pygame.draw.circle(surface, (32, 38, 48), (hx + 8, eye_h - 1), int(3.2 * sf))
        pygame.draw.circle(surface, (255, 255, 255), (hx - 10, eye_h - 3), 2)
        pygame.draw.circle(surface, (255, 255, 255), (hx + 6, eye_h - 3), 2)

        muzzle_y = hy + 8 if not ear_flat else hy + 6
        pygame.draw.ellipse(surface, fc["hi"], (hx - 9, muzzle_y, 18, 9))
        pygame.draw.circle(surface, (42, 36, 34), (hx, muzzle_y + 3), 3)

    def _draw_run_procedural(self, surface: pygame.Surface, cx: int, cy: int, run_phase: float, color: tuple[int, int, int]) -> None:
        sf = 1.0
        p = run_phase * 2.0 * math.pi
        bob = 1.2 * sf * math.sin(p * 2.0)
        cy = int(cy + bob)

        fc = self._fur_colors(color)
        pink = (228, 165, 178)

        stride = 7.5 * sf * math.sin(p)
        lift = 2.8 * sf * math.cos(p * 2.0)

        self._paw(surface, fc["dark"], cx - 11 + stride, cy - 2 + lift * 0.4)
        self._paw(surface, fc["dark"], cx + 11 - stride, cy - 2 - lift * 0.4)
        self._paw(surface, fc["dark"], cx - 10 - stride, cy + 19 - lift * 0.35)
        self._paw(surface, fc["dark"], cx + 10 + stride, cy + 19 + lift * 0.35)

        chest = pygame.Rect(0, 0, int(44 * sf), int(26 * sf))
        chest.center = (cx, cy + 2)
        haunch = pygame.Rect(0, 0, int(38 * sf), int(28 * sf))
        haunch.center = (cx, cy + 16)
        pygame.draw.ellipse(surface, fc["mid"], chest)
        pygame.draw.ellipse(surface, fc["light"], chest.inflate(-8, -6))
        pygame.draw.ellipse(surface, fc["mid"], haunch)
        pygame.draw.ellipse(surface, fc["light"], haunch.inflate(-6, -6))
        pygame.draw.ellipse(surface, fc["belly"], (cx - 11, cy + 1, 22, 16))
        pygame.draw.line(surface, fc["dark"], (chest.centerx, chest.top + 4), (haunch.centerx, haunch.bottom - 4), 2)

        for ox in (-9, 0, 9):
            pygame.draw.arc(
                surface, fc["dark"],
                pygame.Rect(chest.centerx + ox - 6, chest.centery - 6, 12, 18),
                0.2 * math.pi, 0.95 * math.pi, 2,
            )

        wag = 5.0 * sf * math.sin(p * 2.8)
        bx, by = cx + int(16 * sf), cy + int(14 * sf)
        tail = [
            (bx, by), (bx + 14 + int(wag), by - 6),
            (bx + 22 + int(wag * 1.2), by - 22), (bx + 10 + int(wag * 0.5), by - 28),
        ]
        pygame.draw.lines(surface, fc["dark"], False, tail, 5)
        pygame.draw.lines(surface, fc["mid"], False, tail, 3)

        hx, hy = cx, cy - int(22 * sf)
        head_r = int(18 * sf)
        self._draw_head(surface, hx, hy, head_r, fc, pink, sf, ear_flat=False)

        for dx, dy in ((-6, -8), (0, -10), (6, -8)):
            pygame.draw.line(surface, (240, 235, 230), (hx - 10, hy + 9), (hx - 22 + dx, hy - 4 + dy), 1)
            pygame.draw.line(surface, (240, 235, 230), (hx + 10, hy + 9), (hx + 22 + dx, hy - 4 + dy), 1)

    def _draw_jump_procedural(self, surface: pygame.Surface, cx: int, cy: int, color: tuple[int, int, int]) -> None:
        sf = 1.0
        fc = self._fur_colors(color)
        pink = (228, 165, 178)

        shadow = pygame.Surface((50, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 60), shadow.get_rect())
        surface.blit(shadow, (cx - 25, cy + 18))

        self._paw(surface, fc["dark"], cx - 7, cy + 0)
        self._paw(surface, fc["dark"], cx + 7, cy + 0)
        self._paw(surface, fc["dark"], cx - 6, cy + 16)
        self._paw(surface, fc["dark"], cx + 6, cy + 16)

        chest = pygame.Rect(0, 0, int(46 * sf), int(24 * sf))
        chest.center = (cx, cy + 2)
        haunch = pygame.Rect(0, 0, int(40 * sf), int(26 * sf))
        haunch.center = (cx, cy + 15)
        pygame.draw.ellipse(surface, fc["mid"], chest)
        pygame.draw.ellipse(surface, fc["light"], chest.inflate(-8, -6))
        pygame.draw.ellipse(surface, fc["mid"], haunch)
        pygame.draw.ellipse(surface, fc["light"], haunch.inflate(-6, -6))
        pygame.draw.ellipse(surface, fc["belly"], (cx - 10, cy + 2, 20, 14))

        bx, by = cx + int(16 * sf), cy + int(13 * sf)
        tail = [(bx, by), (bx + 16, by - 4), (bx + 24, by - 16), (bx + 14, by - 26)]
        pygame.draw.lines(surface, fc["dark"], False, tail, 5)
        pygame.draw.lines(surface, fc["mid"], False, tail, 3)

        hx, hy = cx, cy - int(24 * sf)
        head_r = int(18 * sf)
        self._draw_head(surface, hx, hy, head_r, fc, pink, sf, ear_flat=True)

        for dx, dy in ((-5, -6), (0, -8), (5, -6)):
            pygame.draw.line(surface, (240, 235, 230), (hx - 9, hy + 9), (hx - 20 + dx, hy - 2 + dy), 1)
            pygame.draw.line(surface, (240, 235, 230), (hx + 9, hy + 9), (hx + 20 + dx, hy - 2 + dy), 1)

    def _draw_slide_procedural(self, surface: pygame.Surface, cx: int, cy: int, slide_scale: float, color: tuple[int, int, int]) -> None:
        sf = 1.0
        fc = self._fur_colors(color)
        pink = (228, 165, 178)

        self._paw(surface, fc["dark"], cx - 14, cy - 2)
        self._paw(surface, fc["dark"], cx + 14, cy - 2)
        self._paw(surface, fc["dark"], cx - 8, cy + 8)
        self._paw(surface, fc["dark"], cx + 8, cy + 8)

        body_w = int(48 * sf)
        body_h = int(22 * sf * slide_scale)
        body = pygame.Rect(0, 0, body_w, body_h)
        body.center = (cx, cy)
        pygame.draw.ellipse(surface, fc["mid"], body)
        if body_h > 8:
            inner = body.inflate(-8, -4)
            pygame.draw.ellipse(surface, fc["light"], inner)
        pygame.draw.ellipse(surface, fc["belly"], (cx - 12, cy - 2, 24, max(4, int(12 * slide_scale))))

        bx, by = cx + int(14 * sf), cy + int(2 * sf)
        tail = [(bx, by), (bx + 12, by), (bx + 18, by - 4), (bx + 10, by - 8)]
        pygame.draw.lines(surface, fc["dark"], False, tail, 4)
        pygame.draw.lines(surface, fc["mid"], False, tail, 2)

        hx, hy = cx, cy - int(14 * sf * slide_scale)
        head_r = int(16 * sf)
        self._draw_head(surface, hx, hy, head_r, fc, pink, sf * slide_scale, ear_flat=True)
