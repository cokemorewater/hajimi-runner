"""
Top-down three-lane dodge: cat vs trucks, multi-scene roads + day–night lighting.
Run: pip install -r requirements.txt && python main.py
"""

import math
import os
import random
import sys
import time

_ROOT = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    _ROOT = sys._MEIPASS
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pygame

from constants import (
    COLOR_BG,
    COLOR_UI,
    COLOR_UI_DIM,
    DAY_CYCLE_SEC,
    FPS,
    HEIGHT,
    JUMP_DURATION,
    METERS_PER_SPEED_PIXEL,
    SLIDE_DURATION,
    TRAIN_BASE_SPEED,
    WIDTH,
)
from cat_player import Player, set_road_scene
from coin import COIN_SIZE, Coin, CoinSpawner, apply_magnet
from daycycle import (
    apply_lighting_overlay,
    draw_celestial,
    draw_sky_gradient,
    time_label_cn,
)
from menu import Menu
from obstacle import Obstacle, ObstacleSpawner, ObstacleType
from realistic_art import (
    invalidate_road_cache,
    road_scroll_strip,
)
from road_scenes import RoadScene, scene_for_distance, scene_name_cn
from spawner import TrainSpawner
from train import Train
from assets import clear_cache, set_current_scene

_RUN_PHASE_PER_SPEED = 1.0 / TRAIN_BASE_SPEED
_ROAD_SCROLL_FACTOR: float = 0.4
_TRANSITION_DURATION: float = 0.6
_ROAD_CHANGE_METERS: float = 200.0

# ── 手机触控参数 ──────────────────────────────────────────────
_SWIPE_THRESHOLD = 30      # 滑动距离阈值（像素）
_TAP_THRESHOLD = 12        # 点击距离阈值（小于此值视为点击）
_SWIPE_HOLD_TIME = 0.25    # 长按判定时间（秒）


class TouchHandler:
    """手机触控手势识别与可视化提示。"""

    def __init__(self) -> None:
        self.finger_down = False
        self.start_x = 0.0
        self.start_y = 0.0
        self.fx = 0.0   # 当前手指位置（归一化 0~1）
        self.fy = 0.0
        self.down_time = 0.0
        self._last_swipe = ""  # 防止同一滑动手势触发多次
        self._last_swipe_time = 0.0
        self._show_touch_hint = False  # 短暂显示触摸提示动画
        self._hint_timer = 0.0

    def finger_down(self, x: float, y: float, now: float) -> None:
        self.finger_down = True
        self.start_x = x
        self.start_y = y
        self.fx = x
        self.fy = y
        self.down_time = now
        self._last_swipe = ""

    def finger_motion(self, x: float, y: float) -> None:
        self.fx = x
        self.fy = y

    def finger_up(self, now: float) -> str:
        """检测手势方向。"""
        self.finger_down = False
        dx = (self.fx - self.start_x) * WIDTH
        dy = (self.fy - self.start_y) * HEIGHT
        dist = (dx * dx + dy * dy) ** 0.5
        hold = now - self.down_time

        if dist < _TAP_THRESHOLD:
            return "tap"
        if dist < _SWIPE_THRESHOLD:
            return "hold" if hold > _SWIPE_HOLD_TIME else ""

        gesture = ""
        if abs(dx) > abs(dy):
            gesture = "swipe_left" if dx < 0 else "swipe_right"
        else:
            gesture = "swipe_up" if dy < 0 else "swipe_down"

        self._show_touch_hint = True
        self._hint_timer = 0.3
        self._last_swipe = gesture
        self._last_swipe_time = now
        return gesture

    def update_hint(self, dt: float) -> None:
        if self._hint_timer > 0:
            self._hint_timer -= dt
            if self._hint_timer <= 0:
                self._show_touch_hint = False

    def draw_touch_guides(self, surface: pygame.Surface) -> None:
        """在画面边缘绘制触摸操作提示符号（半透明）。"""
        if not self._show_touch_hint:
            return
        alpha = min(255, int(self._hint_timer / 0.3 * 200))
        guide_color = (255, 255, 255, alpha)

        # 使用 SRCALPHA 创建半透明表面
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        # 底部左右箭头（左右滑动换道）
        arrow_y = HEIGHT - 60
        for x_pos, direction in [(120, "left"), (WIDTH - 120, "right")]:
            pts = []
            if direction == "left":
                pts = [(x_pos + 20, arrow_y - 12), (x_pos - 10, arrow_y), (x_pos + 20, arrow_y + 12)]
            else:
                pts = [(x_pos - 20, arrow_y - 12), (x_pos + 10, arrow_y), (x_pos - 20, arrow_y + 12)]
            pygame.draw.polygon(overlay, guide_color, pts)
            pygame.draw.circle(overlay, guide_color, (x_pos, arrow_y), 18, 2)

        # 右侧上下箭头（上滑跳、下滑滑行）
        arr_x = WIDTH - 70
        cx, cy = HEIGHT // 2, HEIGHT // 2
        # 上箭头
        up_pts = [(arr_x, cy - 50), (arr_x - 12, cy - 25), (arr_x + 12, cy - 25)]
        pygame.draw.polygon(overlay, guide_color, up_pts)
        # 下箭头
        down_pts = [(arr_x, cy + 50), (arr_x - 12, cy + 25), (arr_x + 12, cy + 25)]
        pygame.draw.polygon(overlay, guide_color, down_pts)
        # 中心圆形
        pygame.draw.circle(overlay, guide_color, (arr_x, cy), 8, 2)

        surface.blit(overlay, (0, 0))

    @staticmethod
    def draw_perm_guides(surface: pygame.Surface) -> None:
        """绘制永久触摸操作提示（微弱的半透明图标）。"""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        c = (200, 200, 220, 25)  # 非常淡的颜色

        # 底部左右换道提示
        for x_pos in [100, WIDTH - 100]:
            pygame.draw.circle(overlay, c, (x_pos, HEIGHT - 55), 28, 2)

        # 右侧跳跃/滑行提示
        arr_x = WIDTH - 60
        mid_y = HEIGHT // 2 - 20
        up_pts = [(arr_x, mid_y - 30), (arr_x - 10, mid_y - 10), (arr_x + 10, mid_y - 10)]
        pygame.draw.polygon(overlay, c, up_pts)
        down_pts = [(arr_x, mid_y + 30), (arr_x - 10, mid_y + 10), (arr_x + 10, mid_y + 10)]
        pygame.draw.polygon(overlay, c, down_pts)
        pygame.draw.circle(overlay, c, (arr_x, mid_y), 6, 1)

        # 暂停按钮（右上角）
        pause_c = (200, 200, 220, 40)
        pause_rect = pygame.Rect(WIDTH - 46, 8, 36, 30)
        pygame.draw.rect(overlay, pause_c, pause_rect, border_radius=6)
        bar_h = 16
        bar_w = 5
        bar_gap = 8
        bar_y = pause_rect.y + (pause_rect.h - bar_h) // 2
        bar_x1 = pause_rect.x + (pause_rect.w - bar_w * 2 - bar_gap) // 2
        bar_x2 = bar_x1 + bar_w + bar_gap
        pygame.draw.rect(overlay, (255, 255, 255, 60), (bar_x1, bar_y, bar_w, bar_h), border_radius=2)
        pygame.draw.rect(overlay, (255, 255, 255, 60), (bar_x2, bar_y, bar_w, bar_h), border_radius=2)

        surface.blit(overlay, (0, 0))

    def get_pause_rect(self) -> pygame.Rect:
        return pygame.Rect(WIDTH - 50, 4, 44, 38)


def _outline_text(font: pygame.font.Font, text: str, color: tuple[int, int, int],
                  outline_color: tuple[int, int, int] = (60, 50, 80), width: int = 2) -> pygame.Surface:
    text_surf = font.render(text, True, color)
    outline_surf = font.render(text, True, outline_color)
    w, h = text_surf.get_size()
    surf = pygame.Surface((w + width * 2, h + width * 2), pygame.SRCALPHA)
    for dx in (-width, width):
        for dy in (-width, width):
            surf.blit(outline_surf, (width + dx, width + dy))
    surf.blit(text_surf, (width, width))
    return surf


def _shadow_text(font: pygame.font.Font, text: str, color: tuple[int, int, int],
                 shadow_color: tuple[int, int, int] = (0, 0, 0), offset: tuple[int, int] = (2, 3)) -> pygame.Surface:
    text_surf = font.render(text, True, color)
    shadow_surf = font.render(text, True, shadow_color)
    w, h = text_surf.get_size()
    surf = pygame.Surface((w + offset[0], h + offset[1]), pygame.SRCALPHA)
    surf.blit(shadow_surf, (offset[0], offset[1]))
    surf.blit(text_surf, (0, 0))
    return surf


def _setup_skills(player: Player, selected_char: object) -> None:
    name = selected_char.name
    if name == "cat_orange":
        player.skill_name = "阳光冲刺"
        player.skill_cooldown_max = 22.0
        player.skill_duration_max = 3.0
    elif name == "cat_gray":
        player.skill_name = "优雅闪避"
        player.skill_cooldown_max = 18.0
        player.skill_duration_max = 4.0
    elif name == "cat_white":
        player.skill_name = "雪花护盾"
        player.skill_cooldown_max = 25.0
        player.skill_duration_max = 5.0
    elif name == "cat_black":
        player.skill_name = "暗夜疾行"
        player.skill_cooldown_max = 18.0
        player.skill_duration_max = 4.0
        player.night_speed_bonus = True
    elif name == "cat_pink":
        player.skill_name = "花雨金币"
        player.skill_cooldown_max = 22.0
        player.skill_duration_max = 5.0
    elif name == "cat_gold":
        player.skill_name = "幸运光环"
        player.skill_cooldown_max = 25.0
        player.skill_duration_max = 6.0
    elif name == "cat_blue":
        player.skill_name = "星空祝福"
        player.skill_cooldown_max = 45.0
        player.skill_duration_max = 8.0


def draw_hud(
    surface: pygame.Surface,
    font_small: pygame.font.Font,
    scene: RoadScene,
    day_t: float,
    score: int,
    coins: int,
) -> None:
    loc_time = font_small.render(
        f"{scene_name_cn(scene)}  ·  {time_label_cn(day_t)}",
        True,
        COLOR_UI_DIM,
    )
    surface.blit(loc_time, loc_time.get_rect(topright=(WIDTH - 16, 16)))
    coin_surf = font_small.render(f"金币: {coins}", True, (255, 220, 100))
    surface.blit(coin_surf, (16, HEIGHT - 60))
    score_surf = font_small.render(f"分数: {score}", True, COLOR_UI)
    surface.blit(score_surf, (16, HEIGHT - 36))


def draw_distance_top_left(
    surface: pygame.Surface,
    font: pygame.font.Font,
    meters: float,
) -> None:
    text = f"{meters:.1f} 米"
    sh = font.render(text, True, (10, 12, 16))
    fg = font.render(text, True, COLOR_UI)
    x, y = 14, 12
    surface.blit(sh, (x + 2, y + 2))
    surface.blit(fg, (x, y))


def run_game(menu: Menu, screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font, font_small: pygame.font.Font, font_dist: pygame.font.Font, selected_scene: str) -> None:
    def new_game(scene_name: str) -> tuple[Player, TrainSpawner, list[Train], float, float, float, RoadScene, float, CoinSpawner, list[Coin], int, ObstacleSpawner, list[Obstacle]]:
        invalidate_road_cache()
        s0 = RoadScene[scene_name.upper()] if scene_name.upper() in RoadScene.__members__ else RoadScene.DESERT
        set_current_scene(s0.name.lower())
        set_road_scene(s0)
        d0 = 0.0
        return Player(), TrainSpawner(), [], time.monotonic(), 0.0, d0, s0, 0.0, CoinSpawner(), [], 0, ObstacleSpawner(), []

    player, spawner, trains, day_start, run_phase, distance_m, scene, road_scroll, coin_spawner, coins, collected_coins, obstacle_spawner, obstacles = new_game(selected_scene)
    alive = True
    score = 0
    last_tick = time.monotonic()
    revived = False
    paused = False
    _pause_selection = 0
    anim_scale = 1.0
    death_cause = ""
    _death_selection = 0
    _death_bg_cache: dict[str, pygame.Surface | None] = {}
    _death_dir = os.path.join(_ROOT, "assets", "death")
    _death_btn_rects: list[pygame.Rect] = []
    _death_popup_alpha = 0
    _pause_btn_rects: list[pygame.Rect] = []
    _road_old_index = 0
    _road_fade = 1.0

    selected_char = menu.get_selected_character()
    _setup_skills(player, selected_char)

    has_shield_item = False
    has_shield_active = False
    has_magnet = False
    has_revive = False
    has_revive_available = False
    slow_timer = 0.0

    if not menu.game_data.items_disabled:
        has_shield_item = menu.get_item_uses("护盾道具") > 0
        has_shield_active = has_shield_item
        has_magnet = menu.get_item_uses("磁铁道具") > 0
        has_revive = menu.get_item_uses("复活道具") > 0
        has_revive_available = has_revive

        if has_magnet:
            menu.use_item("磁铁道具")
        has_slow_item = menu.get_item_uses("减速道具") > 0
        if has_slow_item:
            menu.use_item("减速道具")
            slow_timer = 10.0

    if has_shield_active or player.shield:
        shield_text = font_small.render("护盾 ✓", True, (100, 200, 255))
        screen.blit(shield_text, (WIDTH - 80, 50))
        pygame.display.flip()
        pygame.time.wait(800)

    touch = TouchHandler()

    while True:
        now = time.monotonic()
        dt = now - last_tick
        last_tick = now
        day_t = ((now - day_start) / DAY_CYCLE_SEC) % 1.0
        is_night = day_t < 0.22 or day_t > 0.78

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                menu.update_game_stats(score, distance_m, revived)
                return
            if event.type == pygame.MOUSEMOTION and not alive:
                for i, r in enumerate(_death_btn_rects):
                    if r.collidepoint(event.pos):
                        _death_selection = i
                        break
            if event.type == pygame.MOUSEMOTION and paused:
                for i, r in enumerate(_pause_btn_rects):
                    if r.collidepoint(event.pos):
                        _pause_selection = i
                        break
            # ── 手机触控事件 ──────────────────────────────────
            if event.type == pygame.FINGERDOWN:
                touch.finger_down(event.x, event.y, now)
                # 检查暂停按钮区域
                px = event.x * WIDTH
                py = event.y * HEIGHT
                if touch.get_pause_rect().collidepoint(px, py) and alive:
                    paused = not paused
            if event.type == pygame.FINGERMOTION:
                touch.finger_motion(event.x, event.y)
            if event.type == pygame.FINGERUP:
                touch.finger_motion(event.x, event.y)
                gesture = touch.finger_up(now)
                if gesture == "tap":
                    # 映射到鼠标点击
                    fake_pos = (touch.fx * WIDTH, touch.fy * HEIGHT)
                    if not alive:
                        for i, r in enumerate(_death_btn_rects):
                            if r.collidepoint(fake_pos):
                                coins_earned = collected_coins
                                if player.coin_multiplier != 1.0:
                                    coins_earned = int(coins_earned * player.coin_multiplier)
                                menu.add_coins(coins_earned)
                                menu.update_game_stats(score, distance_m, revived)
                                if i == 0:
                                    player, spawner, trains, day_start, run_phase, distance_m, scene, road_scroll, coin_spawner, coins, collected_coins, obstacle_spawner, obstacles = new_game(selected_scene)
                                    alive = True
                                    score = 0
                                    last_tick = time.monotonic()
                                    revived = False
                                    _death_selection = 0
                                    anim_scale = 1.0
                                    _setup_skills(player, selected_char)
                                    has_shield_active = not menu.game_data.items_disabled and menu.get_item_uses("护盾道具") > 0
                                    has_revive_available = not menu.game_data.items_disabled and menu.get_item_uses("复活道具") > 0
                                    slow_timer = 0.0
                                else:
                                    return
                                break
                    elif paused:
                        for i, r in enumerate(_pause_btn_rects):
                            if r.collidepoint(fake_pos):
                                if i == 0:
                                    paused = False
                                    _pause_selection = 0
                                elif i == 1:
                                    coins_earned = collected_coins
                                    if player.coin_multiplier != 1.0:
                                        coins_earned = int(coins_earned * player.coin_multiplier)
                                    menu.add_coins(coins_earned)
                                    menu.update_game_stats(score, distance_m, revived)
                                    player, spawner, trains, day_start, run_phase, distance_m, scene, road_scroll, coin_spawner, coins, collected_coins, obstacle_spawner, obstacles = new_game(selected_scene)
                                    alive = True
                                    score = 0
                                    last_tick = time.monotonic()
                                    revived = False
                                    paused = False
                                    _pause_selection = 0
                                    anim_scale = 1.0
                                    _setup_skills(player, selected_char)
                                    has_shield_active = not menu.game_data.items_disabled and menu.get_item_uses("护盾道具") > 0
                                    has_revive_available = not menu.game_data.items_disabled and menu.get_item_uses("复活道具") > 0
                                    slow_timer = 0.0
                                elif i == 2:
                                    coins_earned = collected_coins
                                    if player.coin_multiplier != 1.0:
                                        coins_earned = int(coins_earned * player.coin_multiplier)
                                    menu.add_coins(coins_earned)
                                    menu.update_game_stats(score, distance_m, revived)
                                    return
                                break
                    elif alive and not paused:
                        player.activate_skill()
                elif alive and not paused:
                    if gesture == "swipe_left":
                        player.move_left()
                    elif gesture == "swipe_right":
                        player.move_right()
                    elif gesture == "swipe_up":
                        player.start_jump()
                    elif gesture == "swipe_down":
                        player.start_slide()
            if event.type == pygame.MOUSEBUTTONDOWN and not alive and event.button == 1:
                for i, r in enumerate(_death_btn_rects):
                    if r.collidepoint(event.pos):
                        coins_earned = collected_coins
                        if player.coin_multiplier != 1.0:
                            coins_earned = int(coins_earned * player.coin_multiplier)
                        menu.add_coins(coins_earned)
                        menu.update_game_stats(score, distance_m, revived)
                        if i == 0:
                            player, spawner, trains, day_start, run_phase, distance_m, scene, road_scroll, coin_spawner, coins, collected_coins, obstacle_spawner, obstacles = new_game(selected_scene)
                            alive = True
                            score = 0
                            last_tick = time.monotonic()
                            revived = False
                            _death_selection = 0
                            anim_scale = 1.0
                            _setup_skills(player, selected_char)
                            has_shield_active = not menu.game_data.items_disabled and menu.get_item_uses("护盾道具") > 0
                            has_revive_available = not menu.game_data.items_disabled and menu.get_item_uses("复活道具") > 0
                            slow_timer = 0.0
                        else:
                            return
                        break
            if event.type == pygame.MOUSEBUTTONDOWN and paused and event.button == 1:
                for i, r in enumerate(_pause_btn_rects):
                    if r.collidepoint(event.pos):
                        if i == 0:
                            paused = False
                            _pause_selection = 0
                        elif i == 1:
                            coins_earned = collected_coins
                            if player.coin_multiplier != 1.0:
                                coins_earned = int(coins_earned * player.coin_multiplier)
                            menu.add_coins(coins_earned)
                            menu.update_game_stats(score, distance_m, revived)
                            player, spawner, trains, day_start, run_phase, distance_m, scene, road_scroll, coin_spawner, coins, collected_coins, obstacle_spawner, obstacles = new_game(selected_scene)
                            alive = True
                            score = 0
                            last_tick = time.monotonic()
                            revived = False
                            paused = False
                            _pause_selection = 0
                            anim_scale = 1.0
                            _setup_skills(player, selected_char)
                            has_shield_active = not menu.game_data.items_disabled and menu.get_item_uses("护盾道具") > 0
                            has_revive_available = not menu.game_data.items_disabled and menu.get_item_uses("复活道具") > 0
                            slow_timer = 0.0
                        elif i == 2:
                            coins_earned = collected_coins
                            if player.coin_multiplier != 1.0:
                                coins_earned = int(coins_earned * player.coin_multiplier)
                            menu.add_coins(coins_earned)
                            menu.update_game_stats(score, distance_m, revived)
                            return
                        break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if alive:
                        paused = not paused
                    else:
                        coins_earned = collected_coins
                        if player.coin_multiplier != 1.0:
                            coins_earned = int(coins_earned * player.coin_multiplier)
                        menu.add_coins(coins_earned)
                        menu.update_game_stats(score, distance_m, revived)
                        return
                elif alive and not paused:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        player.move_left()
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        player.move_right()
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        player.start_jump()
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        player.start_slide()
                    elif event.key in (pygame.K_SPACE, pygame.K_e):
                        player.activate_skill()
                elif paused:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        _pause_selection = (_pause_selection - 1) % 3
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        _pause_selection = (_pause_selection + 1) % 3
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if _pause_selection == 0:
                            paused = False
                        elif _pause_selection == 1:
                            coins_earned = collected_coins
                            if player.coin_multiplier != 1.0:
                                coins_earned = int(coins_earned * player.coin_multiplier)
                            menu.add_coins(coins_earned)
                            menu.update_game_stats(score, distance_m, revived)
                            player, spawner, trains, day_start, run_phase, distance_m, scene, road_scroll, coin_spawner, coins, collected_coins, obstacle_spawner, obstacles = new_game(selected_scene)
                            alive = True
                            score = 0
                            last_tick = time.monotonic()
                            revived = False
                            paused = False
                            _pause_selection = 0
                            anim_scale = 1.0
                            _setup_skills(player, selected_char)
                            has_shield_active = not menu.game_data.items_disabled and menu.get_item_uses("护盾道具") > 0
                            has_revive_available = not menu.game_data.items_disabled and menu.get_item_uses("复活道具") > 0
                            slow_timer = 0.0
                        elif _pause_selection == 2:
                            coins_earned = collected_coins
                            if player.coin_multiplier != 1.0:
                                coins_earned = int(coins_earned * player.coin_multiplier)
                            menu.add_coins(coins_earned)
                            menu.update_game_stats(score, distance_m, revived)
                            return
                elif not alive:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        _death_selection = (_death_selection - 1) % 2
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        _death_selection = (_death_selection + 1) % 2
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        coins_earned = collected_coins
                        if player.coin_multiplier != 1.0:
                            coins_earned = int(coins_earned * player.coin_multiplier)
                        menu.add_coins(coins_earned)
                        menu.update_game_stats(score, distance_m, revived)
                        if _death_selection == 0:
                            player, spawner, trains, day_start, run_phase, distance_m, scene, road_scroll, coin_spawner, coins, collected_coins, obstacle_spawner, obstacles = new_game(selected_scene)
                            alive = True
                            score = 0
                            last_tick = time.monotonic()
                            revived = False
                            _death_selection = 0
                            anim_scale = 1.0
                            _setup_skills(player, selected_char)
                            has_shield_active = not menu.game_data.items_disabled and menu.get_item_uses("护盾道具") > 0
                            has_revive_available = not menu.game_data.items_disabled and menu.get_item_uses("复活道具") > 0
                            slow_timer = 0.0
                        else:
                            return

        if alive and not paused:
            player.update_action(dt)
            if not player.skill_active:
                if player.skill_cooldown > 0:
                    player.skill_cooldown = max(0.0, player.skill_cooldown - dt)

            if player.skill_active:
                player.skill_duration -= dt
                if player.skill_duration <= 0:
                    player.skill_active = False
                    player.skill_cooldown = player.skill_cooldown_max

            if player.skill_name == "阳光冲刺":
                player.speed_multiplier = 1.5 if player.skill_active else player._skill_base_speed
            elif player.skill_name == "星空祝福":
                player.invincible = player.skill_active
                player.speed_multiplier = 2.0 if player.skill_active else player._skill_base_speed
            elif player.skill_name == "优雅闪避":
                player.dodge_chance = 0.5 if player.skill_active else player._skill_base_dodge
            elif player.skill_name == "雪花护盾":
                player.shield = player.skill_active
            elif player.skill_name == "暗夜疾行":
                player.speed_multiplier = 1.5 if player.skill_active else player._skill_base_speed
            elif player.skill_name == "花雨金币":
                player.coin_multiplier = 2.0 if player.skill_active else player._skill_base_coin
            elif player.skill_name == "幸运光环":
                player.coin_multiplier = 2.0 if player.skill_active else player._skill_base_coin
                player.coin_magnet_extra = 250.0 if player.skill_active else player._skill_base_magnet

            if player.night_speed_bonus and is_night:
                player.speed_multiplier = max(player.speed_multiplier, 1.3)

            new_train = spawner.update(now, dt, distance_m, coins, obstacles)
            if new_train is not None:
                trains.append(new_train)

            spd = spawner.current_speed(distance_m) * player.speed_multiplier
            if slow_timer > 0:
                spd *= 0.5

            for t in trains:
                t.speed = spd
                t.update()
            trains = [t for t in trains if not t.is_off_screen(HEIGHT)]

            new_coin = coin_spawner.update(now, spd * 0.8, obstacles, trains)
            if new_coin is not None:
                coins.append(new_coin)
            for c in coins:
                c.speed = spd * 0.8
                c.update(dt)
            coins = [c for c in coins if not c.is_off_screen() and not c.collected]

            magnet_range = 120.0
            if player.coin_magnet_extra > 0:
                magnet_range += player.coin_magnet_extra
            if has_magnet:
                magnet_range += 150.0
            apply_magnet(player.rect, coins, magnet_range, dt)

            for c in coins:
                if c.rect().colliderect(player.rect):
                    c.collected = True
                    collected_coins += 1

            new_obs = obstacle_spawner.update(now, spd, distance_m, obstacles, coins, trains)
            if new_obs is not None:
                obstacles.append(new_obs)
            for obs in obstacles:
                obs.speed = spd
                obs.update()
            obstacles = [obs for obs in obstacles if not obs.is_off_screen()]

            obstacles.sort(key=lambda o: o.rect.y)
            trains.sort(key=lambda t: t.rect.y)
            coins.sort(key=lambda c: c.y)

            def _push_apart(a_rect: pygame.Rect, b_rect: pygame.Rect, gap: int = 16) -> bool:
                if not a_rect.colliderect(b_rect):
                    return False
                if a_rect.y < b_rect.y:
                    b_rect.y = max(b_rect.y, a_rect.bottom + gap)
                else:
                    a_rect.y = max(a_rect.y, b_rect.bottom + gap)
                return True

            def _push_coin(coin: Coin, rect: pygame.Rect, gap: int = 12) -> bool:
                cr = coin.rect()
                if not cr.colliderect(rect):
                    return False
                if cr.centery < rect.centery:
                    coin.y = rect.top - COIN_SIZE // 2 - gap
                else:
                    coin.y = rect.bottom + COIN_SIZE // 2 + gap
                return True

            for _ in range(3):
                any_fixed = False
                for i in range(len(obstacles)):
                    for j in range(i + 1, len(obstacles)):
                        oi, oj = obstacles[i], obstacles[j]
                        if _push_apart(oi.rect, oj.rect):
                            any_fixed = True
                        elif abs(oi.lane - oj.lane) == 1:
                            if oi.rect.colliderect(oj.rect.inflate(30, 0)):
                                if oi.rect.y < oj.rect.y:
                                    oj.rect.y = max(oj.rect.y, oi.rect.bottom + 16)
                                else:
                                    oi.rect.y = max(oi.rect.y, oj.rect.bottom + 16)
                                any_fixed = True
                for i in range(len(trains)):
                    for j in range(i + 1, len(trains)):
                        if _push_apart(trains[i].rect, trains[j].rect):
                            any_fixed = True
                for obs in obstacles:
                    for t in trains:
                        if _push_apart(obs.rect, t.rect):
                            any_fixed = True
                for obs in obstacles:
                    for c in coins:
                        if _push_coin(c, obs.rect):
                            any_fixed = True
                for t in trains:
                    for c in coins:
                        if _push_coin(c, t.rect):
                            any_fixed = True
                for i in range(len(coins)):
                    for j in range(i + 1, len(coins)):
                        ci, cj = coins[i], coins[j]
                        if ci.rect().colliderect(cj.rect()):
                            if ci.y < cj.y:
                                cj.y = max(cj.y, ci.y + COIN_SIZE + 12)
                            else:
                                ci.y = max(ci.y, cj.y + COIN_SIZE + 12)
                            any_fixed = True
                if not any_fixed:
                    break

            collided = any(t.rect.colliderect(player.rect) for t in trains)
            if collided:
                death_cause = "train"
            if not collided:
                for obs in obstacles:
                    if obs.collision_rect().colliderect(player.rect):
                        if obs.obs_type == ObstacleType.LOW and player.jumping:
                            prog = player.jump_timer / max(JUMP_DURATION, 0.001)
                            if prog > 0.05:
                                continue
                        if obs.obs_type == ObstacleType.HIGH and player.sliding:
                            prog = player.slide_timer / max(SLIDE_DURATION, 0.001)
                            if prog > 0.03:
                                continue
                        collided = True
                        death_cause = "low" if obs.obs_type == ObstacleType.LOW else "high"
                        break
            if collided:
                if player.invincible:
                    collided = False
                elif player.dodge_chance > 0 and random.random() < player.dodge_chance:
                    collided = False
                elif player.shield:
                    player.shield = False
                    collided = False
                elif has_shield_active:
                    has_shield_active = False
                    collided = False
                    menu.use_item("护盾道具")
                elif has_revive_available:
                    has_revive_available = False
                    revived = True
                    collided = False
                    menu.use_item("复活道具")
                    trains = [t for t in trains if t.rect.y > player.rect.y + 100]
                    obstacles = []
                    obstacle_spawner.reset()
                    slow_timer = 5.0
                else:
                    alive = False
            else:
                score += int(dt * 60)
                if slow_timer > 0:
                    slow_timer -= dt
                run_phase += dt * spd * _RUN_PHASE_PER_SPEED
                distance_m += spd * METERS_PER_SPEED_PIXEL
                road_scroll -= spd * _ROAD_SCROLL_FACTOR

        screen.fill(COLOR_BG)
        sy = int(road_scroll) % HEIGHT
        road_index = int(distance_m / _ROAD_CHANGE_METERS)

        if road_index != _road_old_index and _road_fade >= 1.0:
            _road_fade = 0.0
        if _road_fade < 1.0:
            if _road_old_index != road_index:
                old_strip = road_scroll_strip(scene, _road_old_index).copy()
                old_strip.set_alpha(int((1.0 - _road_fade) * 255))
                screen.blit(old_strip, (0, -sy))
            _road_fade = min(1.0, _road_fade + dt * 2.0)

        new_strip = road_scroll_strip(scene, road_index).copy()
        if _road_fade < 1.0:
            new_strip.set_alpha(int(_road_fade * 255))
        screen.blit(new_strip, (0, -sy))
        _road_old_index = road_index

        for t in trains:
            t.draw(screen)
        for c in coins:
            c.draw(screen)
        for obs in obstacles:
            obs.draw(screen)
        player.draw(screen, run_phase, anim_scale, selected_char.color, selected_char.name)

        draw_sky_gradient(screen, day_t)
        draw_celestial(screen, day_t)

        apply_lighting_overlay(screen, day_t)
        draw_distance_top_left(screen, font_dist, distance_m)
        draw_hud(screen, font_small, scene, day_t, score, collected_coins)

        if (has_shield_active or player.shield):
            shield_surf = pygame.Surface((player.rect.width + 16, player.rect.height + 16), pygame.SRCALPHA)
            pygame.draw.ellipse(shield_surf, (100, 200, 255, 60), shield_surf.get_rect(), 4)
            screen.blit(shield_surf, (player.rect.x - 8, player.rect.y - 8 + player.jump_offset))

        if player.skill_flash_timer > 0:
            flash_progress = 1.0 - player.skill_flash_timer / 0.5
            flash_radius = int(30 + 80 * flash_progress)
            flash_alpha = int(180 * (1.0 - flash_progress))
            flash_surf = pygame.Surface((flash_radius * 2, flash_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 255, 200, flash_alpha), (flash_radius, flash_radius), flash_radius, 4)
            screen.blit(flash_surf, (player.rect.centerx - flash_radius, player.rect.centery - flash_radius))
            if player.skill_flash_timer > 0.35:
                label = font.render("技能释放!", True, (255, 255, 150))
                label.set_alpha(int(255 * (player.skill_flash_timer - 0.35) / 0.15))
                screen.blit(label, (player.rect.centerx - label.get_width() // 2, player.rect.top - 50))

        if player.skill_active:
            pulse = 0.6 + 0.4 * math.sin(time.monotonic() * 5)
            glow_surf = pygame.Surface((player.rect.width + 24, player.rect.height + 24), pygame.SRCALPHA)
            glow_color = (255, 215, 0, int(50 * pulse)) if player.invincible else (150, 220, 255, int(35 * pulse))
            pygame.draw.ellipse(glow_surf, glow_color, glow_surf.get_rect(), 3)
            screen.blit(glow_surf, (player.rect.x - 12, player.rect.y - 12))

        if slow_timer > 0:
            slow_text = font_small.render(f"减速 {int(slow_timer)}s", True, (255, 200, 100))
            screen.blit(slow_text, (WIDTH // 2 - 40, 80))

        if player.skill_name:
            if player.skill_active:
                skill_color = (100, 255, 150)
                skill_text = font_small.render(f"{player.skill_name} {int(player.skill_duration)+1}s", True, skill_color)
            elif player.skill_ready:
                skill_color = (255, 220, 100)
                skill_text = font_small.render(f"{player.skill_name} 就绪 按空格", True, skill_color)
            else:
                cd = max(0, int(player.skill_cooldown))
                skill_color = (180, 180, 200)
                skill_text = font_small.render(f"{player.skill_name} CD:{cd}s", True, skill_color)
            screen.blit(skill_text, (WIDTH - 200, HEIGHT - 40))

        touch.update_hint(dt)
        TouchHandler.draw_perm_guides(screen)
        touch.draw_touch_guides(screen)

        if paused:
            dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 160))
            screen.blit(dim, (0, 0))

            popup_w, popup_h = 300, 260
            popup_x = (WIDTH - popup_w) // 2
            popup_y = (HEIGHT - popup_h) // 2
            popup = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
            pygame.draw.rect(popup, (30, 35, 50, 235), popup.get_rect(), border_radius=16)
            pygame.draw.rect(popup, (60, 65, 90), popup.get_rect(), 2, border_radius=16)
            screen.blit(popup, (popup_x, popup_y))

            title = _outline_text(font, "暂停", (255, 220, 100), (80, 60, 100), 2)
            screen.blit(title, (popup_x + (popup_w - title.get_width()) // 2, popup_y + 20))

            _pause_btn_rects.clear()
            options = ["继续游戏", "重新开始", "返回主菜单"]
            for idx, opt in enumerate(options):
                btn_w, btn_h = 240, 38
                btn_x = popup_x + (popup_w - btn_w) // 2
                btn_y = popup_y + 70 + idx * 50
                rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
                _pause_btn_rects.append(rect)

                is_active = idx == _pause_selection
                if is_active:
                    pygame.draw.rect(screen, (60, 70, 100), rect, border_radius=8)
                    pygame.draw.rect(screen, (255, 220, 100), rect, 2, border_radius=8)
                else:
                    pygame.draw.rect(screen, (40, 45, 65), rect, border_radius=8)
                    pygame.draw.rect(screen, (60, 65, 90), rect, 2, border_radius=8)

                color = (255, 220, 100) if is_active else (200, 205, 215)
                opt_surf = _shadow_text(font_small, opt, color, (30, 25, 40), (1, 2))
                screen.blit(opt_surf, opt_surf.get_rect(center=rect.center))

            hint = font_small.render("↑↓ 选择  Enter 确认  Esc 继续", True, (120, 125, 140))
            screen.blit(hint, (popup_x + (popup_w - hint.get_width()) // 2, popup_y + popup_h - 32))

        if not alive:
            _death_popup_alpha = min(255, _death_popup_alpha + 20)

            dim_alpha = min(160, int(160 * _death_popup_alpha / 255))
            dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, dim_alpha))
            screen.blit(dim, (0, 0))

            popup_w, popup_h = 340, 430
            popup_x = (WIDTH - popup_w) // 2
            popup_y = (HEIGHT - popup_h) // 2
            popup_alpha = min(235, int(235 * _death_popup_alpha / 255))
            popup = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
            pygame.draw.rect(popup, (30, 35, 50, popup_alpha), popup.get_rect(), border_radius=16)
            pygame.draw.rect(popup, (60, 65, 90), popup.get_rect(), 2, border_radius=16)
            screen.blit(popup, (popup_x, popup_y))

            title = _outline_text(font, "游戏结束", (255, 220, 100), (80, 60, 100), 2)
            screen.blit(title, (popup_x + (popup_w - title.get_width()) // 2, popup_y + 16))

            death_msgs = {
                "train": "哈基米，货车的力量是不可抗衡的！",
                "low": "哈！哈！一只哈气基米",
                "high": "大狗大狗嚼嚼嚼！",
            }
            msg = death_msgs.get(death_cause, "撞到了！")
            death_msg = _shadow_text(font_small, msg, (255, 200, 150), (40, 30, 50), (1, 2))
            screen.blit(death_msg, (popup_x + (popup_w - death_msg.get_width()) // 2, popup_y + 50))

            img = _death_bg_cache.get(death_cause)
            if img is None and death_cause not in _death_bg_cache:
                path = os.path.join(_death_dir, f"{death_cause}.png")
                if os.path.exists(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                    except Exception:
                        pass
                _death_bg_cache[death_cause] = img

            if img is None and "default" not in _death_bg_cache:
                path = os.path.join(_death_dir, "default.png")
                if os.path.exists(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                    except Exception:
                        pass
                _death_bg_cache["default"] = img
            elif img is None:
                img = _death_bg_cache.get("default")

            if img is not None:
                img_w, img_h = img.get_size()
                max_w, max_h = 260, 150
                if img_w > max_w or img_h > max_h:
                    scale = min(max_w / img_w, max_h / img_h)
                    img_w = int(img_w * scale)
                    img_h = int(img_h * scale)
                    img_surf = pygame.transform.smoothscale(img, (img_w, img_h))
                else:
                    img_surf = img
                screen.blit(img_surf, (popup_x + (popup_w - img_w) // 2, popup_y + 80))

            coins_earned = collected_coins
            if player.coin_multiplier != 1.0:
                coins_earned = int(coins_earned * player.coin_multiplier)
            coins_text = _shadow_text(font_small, f"获得金币: {coins_earned}", (255, 220, 100), (40, 30, 20), (1, 2))
            screen.blit(coins_text, (popup_x + (popup_w - coins_text.get_width()) // 2, popup_y + 250))

            _death_btn_rects.clear()
            options = ["重新开始", "返回主菜单"]
            for idx, opt in enumerate(options):
                btn_w, btn_h = 240, 38
                btn_x = popup_x + (popup_w - btn_w) // 2
                btn_y = popup_y + 295 + idx * 44
                rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
                _death_btn_rects.append(rect)

                is_active = idx == _death_selection
                if is_active:
                    pygame.draw.rect(screen, (60, 70, 100), rect, border_radius=8)
                    pygame.draw.rect(screen, (255, 220, 100), rect, 2, border_radius=8)
                else:
                    pygame.draw.rect(screen, (40, 45, 65), rect, border_radius=8)
                    pygame.draw.rect(screen, (60, 65, 90), rect, 2, border_radius=8)

                color = (255, 220, 100) if is_active else (200, 205, 215)
                opt_surf = _shadow_text(font_small, opt, color, (30, 25, 40), (1, 2))
                screen.blit(opt_surf, opt_surf.get_rect(center=rect.center))

            hint = font_small.render("↑↓ 选择  Enter 确认", True, (120, 125, 140))
            screen.blit(hint, (popup_x + (popup_w - hint.get_width()) // 2, popup_y + popup_h - 32))

        pygame.display.flip()
        clock.tick(FPS)


def main() -> None:
    pygame.init()
    # 强制清除所有精灵缓存
    clear_cache()
    
    pygame.display.set_caption("Cat Runner")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    _FONT_PATH = os.path.join(_ROOT, "assets", "ZCOOLKuaiLe-Regular.ttf")
    font = pygame.font.Font(_FONT_PATH, 30)
    font_small = pygame.font.Font(_FONT_PATH, 22)
    font_dist = pygame.font.Font(_FONT_PATH, 28)

    while True:
        menu = Menu(screen)
        result = menu.run()
        if result is None:
            break
        
        run_game(menu, screen, clock, font, font_small, font_dist, result)


if __name__ == "__main__":
    main()
    pygame.quit()
