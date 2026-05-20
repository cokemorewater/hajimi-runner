"""Game main menu: start, character select, shop, achievements."""

from __future__ import annotations

import math
import os
import pickle
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pygame

from constants import HEIGHT, WIDTH

# ====== 测试用：无限金币开关，正式发布前改为 False ======
DEBUG_INFINITE_COINS = True
# =======================================================


class MenuState(Enum):
    MAIN = "main"
    CHARACTER_SELECT = "character_select"
    MAP_SELECT = "map_select"
    SHOP = "shop"
    ACHIEVEMENTS = "achievements"


@dataclass
class Character:
    name: str
    color: tuple[int, int, int]
    price: int
    unlocked: bool = False
    description: str = ""
    display_name: str = ""
    story: str = ""
    skill_name: str = ""
    skill_desc: str = ""


@dataclass
class ShopItem:
    name: str
    price: int
    purchased: bool = False
    description: str = ""
    consumable: bool = False
    uses_per_purchase: int = 5
    function_desc: str = ""


@dataclass
class Achievement:
    name: str
    description: str
    unlocked: bool = False
    icon: str = "★"


@dataclass
class GameData:
    coins: int = 0
    unlocked_characters: list[str] = field(default_factory=lambda: ["cat_orange"])
    selected_character: str = "cat_orange"
    shop_items: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)
    high_score: int = 0
    total_distance: float = 0.0
    games_played: int = 0
    item_uses: dict[str, int] = field(default_factory=dict)
    total_coins_spent: int = 0
    items_disabled: bool = False


def load_game_data() -> GameData:
    try:
        if os.path.exists("save.dat"):
            with open("save.dat", "rb") as f:
                data = pickle.load(f)
                if isinstance(data, GameData):
                    if not hasattr(data, "item_uses"):
                        data.item_uses = {}
                    if not hasattr(data, "total_coins_spent"):
                        data.total_coins_spent = 0
                    if not hasattr(data, "items_disabled"):
                        data.items_disabled = False
                    return data
    except Exception as e:
        print(f"Failed to load save data: {e}")
    return GameData()


def save_game_data(data: GameData) -> None:
    try:
        with open("save.dat", "wb") as f:
            pickle.dump(data, f)
    except Exception as e:
        print(f"Failed to save game data: {e}")


class Button:
    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        text: str,
        color: tuple[int, int, int],
        hover_color: tuple[int, int, int],
        text_color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.is_hovered = False
        self.animation = 0.0

    def update(self, mouse_pos: tuple[int, int]) -> None:
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        target = 1.0 if self.is_hovered else 0.0
        self.animation += (target - self.animation) * 0.15

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        color = tuple(
            int(c + (self.hover_color[i] - c) * self.animation)
            for i, c in enumerate(self.color)
        )
        scale = 1.0 + self.animation * 0.06
        w = int(self.rect.width * scale)
        h = int(self.rect.height * scale)
        rect = pygame.Rect(
            self.rect.centerx - w // 2,
            self.rect.centery - h // 2,
            w,
            h,
        )
        radius = min(w, h) // 2

        shadow_rect = rect.copy()
        shadow_rect.y += 3 + int(self.animation * 2)
        pygame.draw.rect(surface, (35, 35, 45), shadow_rect, border_radius=radius)

        pygame.draw.rect(surface, color, rect, border_radius=radius)

        border_color = tuple(min(255, c + 30) for c in color)
        pygame.draw.rect(surface, border_color, rect, 2, border_radius=radius)

        text_surf = font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, mouse_pos: tuple[int, int], mouse_pressed: tuple[bool, ...]) -> bool:
        return self.rect.collidepoint(mouse_pos) and mouse_pressed[0]


class Particle:
    def __init__(self, x: float, y: float, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.vx = (random.random() - 0.5) * 3
        self.vy = -random.random() * 2 - 1
        self.life = 1.0
        self.color = color
        self.size = random.randint(2, 5)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.05
        self.life -= 0.02
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(255 * self.life)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        color_with_alpha = (self.color[0], self.color[1], self.color[2], alpha)
        pygame.draw.circle(s, color_with_alpha, (self.size, self.size), self.size)
        surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))


class CatParticle:
    def __init__(
        self,
        x: float,
        y: float,
        vx_range: tuple[float, float] = (-0.6, 0.6),
        vy_range: tuple[float, float] = (-2.0, -0.5),
        life_decay: float = 0.01,
        gravity: float = 0.04,
        size_range: tuple[int, int] = (6, 10),
    ) -> None:
        self.x = x
        self.y = y
        self.vx = random.uniform(*vx_range)
        self.vy = random.uniform(*vy_range)
        self.life = 1.0
        self.life_decay = life_decay
        self.gravity = gravity
        self.size = random.randint(*size_range)
        colors = [(255, 180, 80), (255, 200, 120), (255, 160, 60), (220, 160, 80), (200, 140, 60)]
        self.body_color = random.choice(colors)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= self.life_decay
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(200 * self.life)
        r = self.size
        surf_size = r * 3 + 4
        surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
        cx = cy = surf_size // 2
        ear_color = (self.body_color[0] - 30, self.body_color[1] - 30, self.body_color[2] - 15)
        ear_color = tuple(max(0, c) for c in ear_color)

        pygame.draw.circle(surf, (*self.body_color, alpha), (cx, cy), r)

        ear_size = r * 0.7
        pygame.draw.polygon(surf, (*ear_color, alpha), [
            (cx - r + 1, cy - r + 2),
            (cx - int(r * 0.4), cy - r - int(ear_size) + 2),
            (cx + 1, cy - r + 2),
        ])
        pygame.draw.polygon(surf, (*ear_color, alpha), [
            (cx + r - 1, cy - r + 2),
            (cx + int(r * 0.4), cy - r - int(ear_size) + 2),
            (cx - 1, cy - r + 2),
        ])

        eye_r = max(1, r // 5)
        pygame.draw.circle(surf, (50, 40, 30, alpha), (cx - r // 3, cy - r // 4), eye_r)
        pygame.draw.circle(surf, (50, 40, 30, alpha), (cx + r // 3, cy - r // 4), eye_r)

        surface.blit(surf, (int(self.x) - surf_size // 2, int(self.y) - surf_size // 2))


class PawParticle:
    def __init__(
        self,
        x: float, y: float,
        vx_range: tuple[float, float] = (-0.3, 0.3),
        vy_range: tuple[float, float] = (-0.5, -0.1),
        life_decay: float = 0.006,
        gravity: float = 0.008,
        size_range: tuple[int, int] = (4, 7),
    ) -> None:
        self.x = x
        self.y = y
        self.vx = random.uniform(*vx_range)
        self.vy = random.uniform(*vy_range)
        self.life = 1.0
        self.life_decay = life_decay
        self.gravity = gravity
        self.size = random.randint(*size_range)
        colors = [(255, 255, 255), (255, 200, 220), (255, 180, 200), (255, 220, 240), (255, 160, 190)]
        self.color = random.choice(colors)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= self.life_decay
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(200 * self.life)
        r = self.size
        surf_size = r * 3 + 6
        surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
        cx = surf_size // 2
        cy = surf_size // 2

        main_r = max(1, int(r * 0.55))
        toe_r = max(1, int(r * 0.28))

        pygame.draw.circle(surf, (*self.color, alpha), (cx, int(cy + r * 0.15)), main_r)

        for ox, oy in [(-r * 0.5, -r * 0.5), (-r * 0.15, -r * 0.75), (r * 0.15, -r * 0.75), (r * 0.5, -r * 0.5)]:
            pygame.draw.circle(surf, (*self.color, alpha), (int(cx + ox), int(cy + oy)), toe_r)

        surface.blit(surf, (int(self.x) - surf_size // 2, int(self.y) - surf_size // 2))


class Menu:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.clock = pygame.time.Clock()
        _font_path = os.path.join(os.path.dirname(__file__), "assets", "ZCOOLKuaiLe-Regular.ttf")
        self.font_large = pygame.font.Font(_font_path, 48)
        self.font_medium = pygame.font.Font(_font_path, 28)
        self.font_small = pygame.font.Font(_font_path, 20)
        self.font_title = pygame.font.Font(_font_path, 96)
        self.font_subtitle = pygame.font.Font(_font_path, 24)
        self.state = MenuState.MAIN
        self.game_data = load_game_data()
        if DEBUG_INFINITE_COINS:
            self.game_data.coins = 999999
        self.particles: list[object] = []
        self.scroll_offset = 0.0
        self.transition_alpha = 0
        self.transition_target: Optional[MenuState] = None
        self.fade_state: str = "idle"
        self.popup_anim: float = 0.0
        self.popup_closing: bool = False
        self.mouse_pos = (0, 0)
        self.popup: Optional[dict] = None
        self.popup_buttons: dict[str, Button] = {}

        self.has_bg_image = False
        self.bg_images: dict[str, Optional[pygame.Surface]] = {}
        bg_base = os.path.join(os.path.dirname(__file__), "assets", "menu_bg")
        for page in ("main", "character", "shop", "achievements", "map"):
            folder = os.path.join(bg_base, page)
            img = None
            if os.path.isdir(folder):
                for fname in sorted(os.listdir(folder)):
                    if fname.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                        try:
                            img = pygame.transform.smoothscale(
                                pygame.image.load(os.path.join(folder, fname)),
                                (WIDTH, HEIGHT),
                            )
                        except Exception as e:
                            print(f"Failed to load {page} background: {e}")
                        break
            self.bg_images[page] = img
            if img:
                self.has_bg_image = True

        self._init_buttons()
        self._init_characters()
        self._init_shop_items()
        self._migrate_old_items()
        self._init_achievements()
        self._init_maps()

    def _init_buttons(self) -> None:
        btn_w, btn_h = 220, 55
        center_x = WIDTH // 2
        start_y = HEIGHT // 2 - 80

        self.main_buttons = {
            "start": Button(center_x - btn_w // 2, start_y, btn_w, btn_h, "开始游戏", (60, 140, 80), (80, 180, 100)),
            "character": Button(center_x - btn_w // 2, start_y + 70, btn_w, btn_h, "猫咪", (80, 100, 160), (100, 130, 200)),
            "shop": Button(center_x - btn_w // 2, start_y + 140, btn_w, btn_h, "商店", (160, 120, 60), (200, 160, 80)),
            "achievements": Button(center_x - btn_w // 2, start_y + 210, btn_w, btn_h, "成就", (140, 60, 120), (180, 90, 160)),
        }

        self.back_button = Button(30, HEIGHT - 80, 120, 45, "← 返回", (80, 80, 90), (110, 110, 120))

    def _init_characters(self) -> None:
        self.characters = [
            Character(
                "cat_orange",
                (232, 140, 60),
                0,
                True,
                "小菊花 - 默认猫咪",
                "耄耋",
                "耄耋已经经历了2999次轮回，结局都是跟耄妈一起生活下去，可过得并不好，没有钱给其他哈基米买猫粮，这一次，耄耋开始了哈气",
                "哈气快冲",
                "奔跑时每隔30秒获得一次短暂的加速爆发，速度提升50%持续3秒",
            ),
            Character(
                "cat_gray",
                (140, 140, 150),
                500,
                False,
                "绅士灰猫 - 优雅稳重",
                "灰绅士",
                "出身于贵族庄园的灰色英短，举止优雅、处变不惊。灰绅士从小在书房长大，读遍了关于远方的书，却从未真正踏上旅途。终于有一天，它合上书本，决定用自己的脚步去书写属于自己的冒险故事。",
                "优雅闪避",
                "被货车撞到时有20%的概率触发优雅闪避，免疫本次伤害",
            ),
            Character(
                "cat_white",
                (245, 240, 230),
                800,
                False,
                "雪白猫咪 - 纯洁可爱",
                "雪团团",
                "在北方雪原长大的纯白小猫，毛茸茸的样子像一团会移动的雪球。雪团团天生对世界充满好奇，每一片飘落的雪花都能让它开心一整天。它的笑容像冬日的暖阳，能融化最寒冷的冰。",
                "雪花护盾",
                "游戏开始时获得一层雪花护盾，可以抵挡一次碰撞伤害",
            ),
            Character(
                "cat_black",
                (50, 45, 55),
                1000,
                False,
                "暗夜黑猫 - 神秘酷帅",
                "路过的小猫",
                "一只路过的平平无奇的小猫，被做成了游戏素材",
                "暗夜疾行",
                "夜晚时段移动速度提升30%，且更容易发现前方的障碍物",
            ),
            Character(
                "cat_pink",
                (255, 180, 200),
                1500,
                False,
                "粉红猫咪 - 甜美梦幻",
                "樱花酱",
                "出生在樱花盛开的春天，一身粉色毛发如同飘落的花瓣。樱花酱喜欢收集各种美丽的东西，从蝴蝶翅膀到清晨的露珠。它相信世界上所有的美好都值得被珍惜，包括每一次奔跑的瞬间。",
                "花雨金币",
                "奔跑时收集金币有30%的概率获得双倍金币",
            ),
            Character(
                "cat_gold",
                (255, 215, 0),
                3000,
                False,
                "黄金猫咪 - 尊贵稀有",
                "耄耋",
                "耄耋已经经历了2999次轮回，结局都是跟耄妈一起生活下去，可过得并不好，没有钱给其他哈基米买猫粮，这一次，耄耋开始了哈气",
                "幸运光环",
                "所有金币自动吸附范围扩大100%，且金币价值提升20%",
            ),
            Character(
                "cat_blue",
                (100, 150, 255),
                2000,
                False,
                "星空蓝猫 - 梦幻深邃",
                "迪耄",
                "某个世界拜访的蓝色小猫",
                "星空祝福",
                "每隔60秒获得一次星空祝福，10秒内无敌且移速翻倍",
            ),
        ]
        self._update_character_unlock_status()

    def _update_character_unlock_status(self) -> None:
        for char in self.characters:
            char.unlocked = char.name in self.game_data.unlocked_characters

    def _migrate_old_items(self) -> None:
        consumable_names = {item.name for item in self.shop_items if item.consumable}
        items_to_migrate = [name for name in self.game_data.shop_items if name in consumable_names]
        if not items_to_migrate:
            return
        for name in items_to_migrate:
            self.game_data.shop_items.remove(name)
            for item in self.shop_items:
                if item.name == name:
                    self.game_data.item_uses[name] = self.game_data.item_uses.get(name, 0) + item.uses_per_purchase
                    break
        save_game_data(self.game_data)

    def _init_shop_items(self) -> None:
        self.shop_items = [
            ShopItem("双倍金币", 500, "每次获得金币翻倍", function_desc="每局游戏中获得的金币数量变为2倍，快速积累财富"),
            ShopItem("护盾道具", 150, "游戏开始时有1次护盾", consumable=True, uses_per_purchase=1, function_desc="受到火车碰撞时自动抵挡一次伤害，消耗1次使用次数"),
            ShopItem("减速道具", 200, "减缓货车速度10秒", consumable=True, uses_per_purchase=1, function_desc="游戏开局时减速火车10秒，更容易躲避障碍，消耗1次使用次数"),
            ShopItem("磁铁道具", 250, "自动吸引附近金币", consumable=True, uses_per_purchase=1, function_desc="自动吸引附近金币自动飞入口袋，持续整局游戏，消耗1次使用次数"),
            ShopItem("复活道具", 300, "被撞后原地复活一次", consumable=True, uses_per_purchase=1, function_desc="被火车撞倒后原地复活一次，保留当前得分，消耗1次使用次数"),
            ShopItem("新跑道", 1500, "解锁彩虹跑道", function_desc="解锁全新的彩虹赛道外观，让奔跑更加炫彩"),
        ]

    def _init_achievements(self) -> None:
        self.achievements = [
            Achievement("初次奔跑", "完成第一次游戏", False, "🏃"),
            Achievement("百米冲刺", "单次奔跑超过100米", False, "📏"),
            Achievement("千米达人", "单次奔跑超过1000米", False, "🎯"),
            Achievement("收藏家", "解锁所有猫咪", False, "🐱"),
            Achievement("购物狂", "在商店消费5000金币", False, "💰"),
            Achievement("常胜将军", "累计获得10000分", False, "⭐"),
            Achievement("永不放弃", "复活后继续游戏", False, "💪"),
            Achievement("速度之星", "在10秒内躲避10辆货车", False, "⚡"),
        ]

    def _init_maps(self) -> None:
        self.maps = [
            {"name": "城郊公路", "scene": "suburb", "desc": "绿色的田野与树木，适合新手练习", "bg_color": (38, 92, 48), "icon_color": (52, 118, 62)},
            {"name": "沙漠公路", "scene": "desert", "desc": "金黄的沙漠与仙人掌，视野开阔", "bg_color": (198, 160, 105), "icon_color": (210, 175, 130)},
            {"name": "海岸公路", "scene": "coast", "desc": "蔚蓝的大海与棕榈树，风景优美", "bg_color": (30, 88, 118), "icon_color": (24, 48, 72)},
        ]
        self.selected_map_index = 0

    def _lerp_color(self, c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

    def draw_background(self, page: str = "main") -> None:
        bg = self.bg_images.get(page)
        if bg:
            self.screen.blit(bg, (0, 0))
            return

        for y in range(0, HEIGHT, 4):
            t = y / HEIGHT
            color = self._lerp_color((20, 25, 35), (40, 50, 70), t)
            pygame.draw.line(self.screen, color, (0, y), (WIDTH, y), 4)

        self.scroll_offset += 0.5
        for i in range(15):
            y = ((i * 80 + self.scroll_offset) % (HEIGHT + 40)) - 20
            x = 50 + (i % 3) * 250
            alpha = 30 + (i % 5) * 10
            star_points = []
            for j in range(5):
                angle = j * (4 * math.pi / 5) - math.pi / 2
                r = 8 if j % 2 == 0 else 4
                star_points.append((x + math.cos(angle) * r, y + math.sin(angle) * r))
            if len(star_points) >= 3:
                star_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
                star_color = (255, 255, 200, alpha)
                adjusted_points = [(p[0] - x + 10, p[1] - y + 10) for p in star_points]
                pygame.draw.polygon(star_surf, star_color, adjusted_points)
                self.screen.blit(star_surf, (x - 10, y - 10))

    def draw_cat_preview(self, x: int, y: int, color: tuple[int, int, int], size: float = 1.0, name: str = "") -> None:
        if name:
            from assets import load_cat_preview_sprite
            sprite = load_cat_preview_sprite(name)
            if sprite is not None:
                if size <= 1.5:
                    target = (130, 130)
                else:
                    target = (150, 150)
                scaled = pygame.transform.smoothscale(sprite, target)
                self.screen.blit(scaled, (x - target[0] // 2, y - target[1] // 2))
                return

        s = size
        pygame.draw.ellipse(self.screen, color, (x - 20 * s, y - 25 * s, 40 * s, 50 * s))
        pygame.draw.circle(self.screen, color, (x, y - 30 * s), int(15 * s))
        for side in (-1, 1):
            ear_pts = [(x + side * 12 * s, y - 38 * s), (x + side * 20 * s, y - 55 * s), (x + side * 5 * s, y - 45 * s)]
            pygame.draw.polygon(self.screen, color, ear_pts)
            inner_pts = [(x + side * 12 * s, y - 37 * s), (x + side * 17 * s, y - 48 * s), (x + side * 8 * s, y - 43 * s)]
            pygame.draw.polygon(self.screen, (255, 200, 200), inner_pts)
        pygame.draw.ellipse(self.screen, (30, 30, 30), (x - 8 * s, y - 35 * s, 6 * s, 7 * s))
        pygame.draw.ellipse(self.screen, (30, 30, 30), (x + 2 * s, y - 35 * s, 6 * s, 7 * s))
        pygame.draw.circle(self.screen, (255, 255, 255), (x - 6 * s, y - 34 * s), 2)
        pygame.draw.circle(self.screen, (255, 255, 255), (x + 4 * s, y - 34 * s), 2)
        pygame.draw.ellipse(self.screen, (255, 150, 150), (x - 3 * s, y - 26 * s, 4 * s, 3 * s))

    def draw_coin_icon(self, x: int, y: int, size: float = 1.0) -> None:
        pygame.draw.circle(self.screen, (255, 200, 50), (x, y), int(12 * size))
        pygame.draw.circle(self.screen, (255, 220, 80), (x - 2, y - 2), int(8 * size))
        font = pygame.font.SysFont("arial", int(14 * size), bold=True)
        text = font.render("$", True, (200, 150, 0))
        self.screen.blit(text, text.get_rect(center=(x, y)))

    def draw_main_menu(self) -> None:
        self.draw_background("main")

        title1 = self.font_title.render("哈基米", True, (255, 230, 150))
        title1_rect = title1.get_rect(center=(WIDTH // 2, 170))
        for ox, oy in [(6, 6), (4, 4), (2, 2)]:
            shade = self.font_title.render("哈基米", True, (60, 40, 80))
            self.screen.blit(shade, (title1_rect.x + ox, title1_rect.y + oy))
        self.screen.blit(title1, title1_rect)

        excl = self.font_title.render("！", True, (255, 230, 150))
        excl_rect = excl.get_rect(left=title1_rect.right + 2, centery=title1_rect.centery)
        for ox, oy in [(6, 6), (4, 4), (2, 2)]:
            excl_shade = self.font_title.render("！", True, (60, 40, 80))
            self.screen.blit(excl_shade, (excl_rect.x + ox, excl_rect.y + oy))
        self.screen.blit(excl, excl_rect)

        title2 = self.font_subtitle.render("南北路多", True, (255, 230, 150))
        title2_rect = title2.get_rect(center=(WIDTH // 2, 250))
        for ox, oy in [(6, 6), (4, 4), (2, 2)]:
            shade = self.font_subtitle.render("南北路多", True, (60, 40, 80))
            self.screen.blit(shade, (title2_rect.x + ox, title2_rect.y + oy))
        self.screen.blit(title2, title2_rect)

        coin_x, coin_y = WIDTH - 100, 50
        self.draw_coin_icon(coin_x, coin_y)
        coin_text = self.font_medium.render(f"{self.game_data.coins}", True, (255, 220, 100))
        self.screen.blit(coin_text, (coin_x + 20, coin_y - 12))

        for btn in self.main_buttons.values():
            btn.update(self.mouse_pos)
            btn.draw(self.screen, self.font_medium)
            if self.has_bg_image and btn.is_hovered and random.random() < 0.15:
                bx = random.randint(btn.rect.left + 5, btn.rect.right - 5)
                by = btn.rect.bottom + 2
                self.particles.append(CatParticle(
                    bx, by,
                    vx_range=(-0.4, 0.4), vy_range=(-1.5, -0.5),
                    life_decay=0.015, gravity=0.03, size_range=(3, 6),
                ))

        for p in self.particles:
            p.draw(self.screen)
        self.particles = [p for p in self.particles if p.update()]
        if self.has_bg_image:
            if random.random() < 0.12:
                self.particles.append(CatParticle(random.randint(50, WIDTH - 50), HEIGHT + 10))
            if random.random() < 0.08:
                tx = random.randint(title1_rect.left - 20, excl_rect.right + 20)
                ty = random.randint(title1_rect.top - 15, title1_rect.bottom + 15)
                self.particles.append(PawParticle(
                    tx, ty,
                    vx_range=(-0.3, 0.3), vy_range=(-0.5, -0.1),
                    life_decay=0.006, gravity=0.008, size_range=(7, 11),
                ))
            if random.random() < 0.06:
                tx2 = random.randint(title2_rect.left - 15, title2_rect.right + 15)
                ty2 = random.randint(title2_rect.top - 10, title2_rect.bottom + 10)
                self.particles.append(PawParticle(
                    tx2, ty2,
                    vx_range=(-0.25, 0.25), vy_range=(-0.4, -0.1),
                    life_decay=0.006, gravity=0.008, size_range=(6, 10),
                ))
        else:
            if random.random() < 0.12:
                self.particles.append(Particle(random.randint(50, WIDTH - 50), 0, (100, 200, 255)))

    def draw_character_select(self) -> None:
        try:
            self.draw_background("character")
            
            title = self.font_large.render("选择猫咪", True, (255, 255, 255))
            title_shadow = self.font_large.render("选择猫咪", True, (80, 80, 120))
            title_rect = title.get_rect(center=(WIDTH // 2, 60))
            self.screen.blit(title_shadow, (title_rect.x + 3, title_rect.y + 3))
            self.screen.blit(title, title_rect)

            coin_x, coin_y = WIDTH - 100, 50
            self.draw_coin_icon(coin_x, coin_y)
            coin_text = self.font_medium.render(f"{self.game_data.coins}", True, (255, 220, 100))
            self.screen.blit(coin_text, (coin_x + 20, coin_y - 12))

            cols = 3
            char_w = 180
            char_h = 200
            margin_left = 80
            start_x = margin_left
            start_y = 210
            spacing_x = 25
            spacing_y = 40

            for i, char in enumerate(self.characters):
                if char is None:
                    continue
                    
                row = i // cols
                col = i % cols
                x = start_x + col * (char_w + spacing_x) + char_w // 2
                y = start_y + row * (char_h + spacing_y)

                is_selected = char.name == self.game_data.selected_character
                bg_color = (60, 60, 90) if char.unlocked else (35, 35, 50)
                border_color = (100, 220, 120) if char.unlocked else (90, 90, 120)
                if is_selected:
                    border_color = (255, 230, 100)
                    bg_color = (70, 70, 100)

                rect = pygame.Rect(x - char_w // 2, y - char_h // 2, char_w, char_h)
                pygame.draw.rect(self.screen, bg_color, rect, border_radius=18)
                pygame.draw.rect(self.screen, border_color, rect, 3, border_radius=18)

                if is_selected:
                    glow_rect = rect.inflate(6, 6)
                    pygame.draw.rect(self.screen, (255, 230, 100), glow_rect, 2, border_radius=20)

                if rect.collidepoint(self.mouse_pos):
                    hover_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(hover_surf, (255, 255, 255, 30), hover_surf.get_rect(), border_radius=18)
                    self.screen.blit(hover_surf, rect)

                self.draw_cat_preview(x, y - 25, char.color, 1.4, char.name)

                name_text = char.display_name if char.display_name else char.description
                
                if char.unlocked:
                    status_color = (100, 255, 150) if is_selected else (180, 180, 200)
                    status_prefix = "★ " if is_selected else ""
                    status_text = self.font_medium.render(f"{status_prefix}{name_text}", True, status_color)
                    self.screen.blit(status_text, status_text.get_rect(center=(x, y + 50)))
                    
                    if is_selected:
                        check_text = self.font_small.render("已装备", True, (100, 255, 150))
                        self.screen.blit(check_text, check_text.get_rect(center=(x, y + 75)))
                    else:
                        check_text = self.font_small.render("已拥有", True, (150, 150, 180))
                        self.screen.blit(check_text, check_text.get_rect(center=(x, y + 75)))
                else:
                    if is_selected:
                        lock_border = rect.inflate(4, 4)
                        pygame.draw.rect(self.screen, (150, 150, 150), lock_border, 1, border_radius=20)

                    name_surf = self.font_small.render(name_text, True, (150, 150, 170))
                    self.screen.blit(name_surf, name_surf.get_rect(center=(x, y + 45)))

                    lock_icon = self.font_medium.render("🔒", True, (200, 200, 200))
                    self.screen.blit(lock_icon, lock_icon.get_rect(center=(x, y + 70)))

                    price_bar_y = y + 108
                    price_bar_rect = pygame.Rect(x - 55, price_bar_y - 14, 110, 28)
                    pygame.draw.rect(self.screen, (40, 45, 55), price_bar_rect, border_radius=6)
                    pygame.draw.rect(self.screen, (100, 100, 120), price_bar_rect, 1, border_radius=6)
                    self.draw_coin_icon(x - 28, price_bar_y, 0.6)
                    price_text = self.font_small.render(str(char.price), True, (255, 220, 100))
                    self.screen.blit(price_text, price_text.get_rect(center=(x + 8, price_bar_y)))

            hint_text = self.font_small.render("点击已解锁的猫咪即可装备", True, (150, 150, 180))
            self.screen.blit(hint_text, hint_text.get_rect(center=(WIDTH // 2, HEIGHT - 80)))

            self.back_button.update(self.mouse_pos)
            self.back_button.draw(self.screen, self.font_small)
        except Exception as e:
            import traceback
            print(f"Error in draw_character_select: {e}")
            traceback.print_exc()

    def draw_shop(self) -> None:
        self.draw_background("shop")

        title = self.font_large.render("商店", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 80)))

        coin_x, coin_y = WIDTH - 100, 50
        self.draw_coin_icon(coin_x, coin_y)
        coin_text = self.font_medium.render(f"{self.game_data.coins}", True, (255, 220, 100))
        self.screen.blit(coin_text, (coin_x + 20, coin_y - 12))

        self._shop_buy_buttons: list[tuple[pygame.Rect, int]] = []

        item_h = 70
        start_y = 130
        sorted_items = sorted(enumerate(self.shop_items), key=lambda x: (
            x[1].name in self.game_data.shop_items and not x[1].consumable
        ))
        for display_idx, (actual_idx, item) in enumerate(sorted_items):
            y = start_y + display_idx * (item_h + 15)
            is_permanent_owned = item.name in self.game_data.shop_items
            uses = self.game_data.item_uses.get(item.name, 0)
            can_afford = self.game_data.coins >= item.price
            bg_color = (50, 50, 70)
            if is_permanent_owned:
                bg_color = (40, 80, 50)
            elif item.consumable and uses > 0:
                bg_color = (40, 60, 80)
            rect = pygame.Rect(100, y, WIDTH - 200, item_h)
            pygame.draw.rect(self.screen, bg_color, rect)

            if rect.collidepoint(self.mouse_pos):
                hover_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                hover_surf.fill((255, 255, 255, 20))
                self.screen.blit(hover_surf, rect)

            name_surf = self.font_medium.render(item.name, True, (255, 255, 255))
            self.screen.blit(name_surf, (120, y + 10))

            desc_surf = self.font_small.render(item.description, True, (180, 180, 180))
            self.screen.blit(desc_surf, (120, y + 40))

            right_area_x = WIDTH - 255

            if is_permanent_owned:
                owned_text = self.font_small.render("已拥有 ✓", True, (100, 255, 150))
                self.screen.blit(owned_text, (right_area_x, y + item_h // 2 - 10))
            else:
                if item.consumable and uses > 0:
                    uses_text = self.font_small.render(f"剩余 {uses}次", True, (100, 200, 255))
                    self.screen.blit(uses_text, (right_area_x, y + 6))
                    price_text = self.font_small.render(f"{item.price} 金币", True, (200, 200, 220))
                    self.screen.blit(price_text, (right_area_x, y + 28))
                else:
                    price_text = self.font_small.render(f"{item.price} 金币", True, (200, 200, 220))
                    self.screen.blit(price_text, (right_area_x, y + 22))

                btn_x = WIDTH - 148
                btn_y = y + 18
                btn_w, btn_h = 42, 34
                buy_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
                self._shop_buy_buttons.append((buy_rect, actual_idx))

                btn_color = (60, 140, 80) if can_afford else (65, 65, 70)
                btn_hover = (80, 180, 100) if can_afford else (80, 80, 85)
                is_hovered = buy_rect.collidepoint(self.mouse_pos)
                color = btn_hover if is_hovered else btn_color
                pygame.draw.rect(self.screen, color, buy_rect)
                pygame.draw.rect(self.screen, (255, 255, 255, 30), buy_rect, 1)

                label_color = (255, 255, 255) if can_afford else (160, 160, 160)
                label_text = self.font_small.render("购买", True, label_color)
                label_rect = label_text.get_rect(center=buy_rect.center)
                self.screen.blit(label_text, label_rect)

        self.back_button.update(self.mouse_pos)
        self.back_button.draw(self.screen, self.font_small)

        toggle_x = WIDTH - 240
        toggle_y = HEIGHT - 80
        self._shop_toggle_rect = pygame.Rect(toggle_x, toggle_y, 18, 18)
        checked = self.game_data.items_disabled
        box_color = (70, 70, 85)
        pygame.draw.rect(self.screen, box_color, self._shop_toggle_rect)
        pygame.draw.rect(self.screen, (160, 160, 160), self._shop_toggle_rect, 1)
        if checked:
            check_surf = self.font_small.render("✓", True, (100, 200, 255))
            self.screen.blit(check_surf, (toggle_x + 3, toggle_y - 1))
        label_color = (160, 180, 200) if checked else (200, 200, 200)
        toggle_label = self.font_small.render("局内不使用道具", True, label_color)
        self.screen.blit(toggle_label, (toggle_x + 25, toggle_y))

    def draw_achievements(self) -> None:
        self.draw_background("achievements")

        title = self.font_large.render("成就", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 80)))

        unlocked_count = sum(1 for a in self.achievements if a.name in self.game_data.achievements)
        progress_text = self.font_medium.render(f"已解锁: {unlocked_count}/{len(self.achievements)}", True, (200, 200, 200))
        self.screen.blit(progress_text, progress_text.get_rect(center=(WIDTH // 2, 120)))

        ach_h = 60
        start_y = 150
        for i, ach in enumerate(self.achievements):
            y = start_y + i * (ach_h + 10)
            unlocked = ach.name in self.game_data.achievements
            bg_color = (50, 70, 50) if unlocked else (40, 40, 50)
            rect = pygame.Rect(80, y, WIDTH - 160, ach_h)
            pygame.draw.rect(self.screen, bg_color, rect)

            icon_text = self.font_large.render(ach.icon, True, (255, 255, 200) if unlocked else (100, 100, 100))
            self.screen.blit(icon_text, (100, y + 10))

            name_surf = self.font_medium.render(ach.name, True, (255, 255, 255) if unlocked else (150, 150, 150))
            self.screen.blit(name_surf, (160, y + 8))

            desc_surf = self.font_small.render(ach.description, True, (180, 180, 180) if unlocked else (100, 100, 100))
            self.screen.blit(desc_surf, (160, y + 35))

            if unlocked:
                check_text = self.font_small.render("✓", True, (100, 255, 150))
                self.screen.blit(check_text, (WIDTH - 120, y + ach_h // 2 - 10))

        self.back_button.update(self.mouse_pos)
        self.back_button.draw(self.screen, self.font_small)

    def draw_map_select(self) -> None:
        self.draw_background("map")

        title = self.font_large.render("选择地图", True, (255, 255, 255))
        title_shadow = self.font_large.render("选择地图", True, (80, 80, 120))
        title_rect = title.get_rect(center=(WIDTH // 2, 60))
        self.screen.blit(title_shadow, (title_rect.x + 3, title_rect.y + 3))
        self.screen.blit(title, title_rect)

        card_w = 200
        card_h = 260
        total_w = len(self.maps) * card_w + (len(self.maps) - 1) * 30
        start_x = (WIDTH - total_w) // 2
        start_y = 140

        for i, mp in enumerate(self.maps):
            x = start_x + i * (card_w + 30)
            y = start_y
            is_selected = i == self.selected_map_index

            card_rect = pygame.Rect(x, y, card_w, card_h)
            bg = mp["bg_color"]
            border_color = (255, 230, 100) if is_selected else (100, 110, 130)

            pygame.draw.rect(self.screen, bg, card_rect, border_radius=12)
            pygame.draw.rect(self.screen, border_color, card_rect, 3 if is_selected else 2, border_radius=12)

            if is_selected:
                glow_rect = card_rect.inflate(8, 8)
                pygame.draw.rect(self.screen, (255, 230, 100, 60), glow_rect, 2, border_radius=14)

            if card_rect.collidepoint(self.mouse_pos):
                hover_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                hover_surf.fill((255, 255, 255, 25))
                self.screen.blit(hover_surf, card_rect)

            icon_center = (x + card_w // 2, y + 70)
            pygame.draw.circle(self.screen, mp["icon_color"], icon_center, 35)
            pygame.draw.circle(self.screen, border_color, icon_center, 35, 2)

            scene_icons = {"suburb": "🌳", "desert": "🌵", "coast": "🌊"}
            icon_text = self.font_large.render(scene_icons.get(mp["scene"], "📍"), True, (255, 255, 255))
            self.screen.blit(icon_text, icon_text.get_rect(center=icon_center))

            name_surf = self.font_medium.render(mp["name"], True, (255, 255, 255))
            self.screen.blit(name_surf, name_surf.get_rect(center=(x + card_w // 2, y + 140)))

            desc_lines = self._wrap_text(mp["desc"], self.font_small, card_w - 20)
            for j, line in enumerate(desc_lines[:2]):
                desc_surf = self.font_small.render(line, True, (200, 200, 220))
                self.screen.blit(desc_surf, desc_surf.get_rect(center=(x + card_w // 2, y + 175 + j * 22)))

            if is_selected:
                check = self.font_small.render("已选择 ✓", True, (255, 230, 100))
                self.screen.blit(check, check.get_rect(center=(x + card_w // 2, y + card_h - 25)))

        hint = self.font_small.render("点击地图开始游戏  或按 ← → 选择  Enter 确认  Esc 返回", True, (150, 150, 180))
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 50)))

        self.back_button.update(self.mouse_pos)
        self.back_button.draw(self.screen, self.font_small)

    def handle_map_select(self, events: list[pygame.event.Event]) -> Optional[str]:
        card_w = 200
        total_w = len(self.maps) * card_w + (len(self.maps) - 1) * 30
        start_x = (WIDTH - total_w) // 2
        start_y = 140

        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                    self._start_transition(MenuState.MAIN)
                    return None
                for i in range(len(self.maps)):
                    x = start_x + i * (card_w + 30)
                    card_rect = pygame.Rect(x, start_y, card_w, 260)
                    if card_rect.collidepoint(self.mouse_pos):
                        self.selected_map_index = i
                        save_game_data(self.game_data)
                        return self.maps[i]["scene"]
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._start_transition(MenuState.MAIN)
                    return None
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.selected_map_index = (self.selected_map_index - 1) % len(self.maps)
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.selected_map_index = (self.selected_map_index + 1) % len(self.maps)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    save_game_data(self.game_data)
                    return self.maps[self.selected_map_index]["scene"]
        return None

    def handle_main_menu(self, events: list[pygame.event.Event]) -> Optional[str]:
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.main_buttons["start"].is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                    self._burst_particles(self.main_buttons["start"].rect.center)
                    self._start_transition(MenuState.MAP_SELECT)
                    return None
                if self.main_buttons["character"].is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                    self._burst_particles(self.main_buttons["character"].rect.center)
                    self._start_transition(MenuState.CHARACTER_SELECT)
                    return None
                if self.main_buttons["shop"].is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                    self._burst_particles(self.main_buttons["shop"].rect.center)
                    self._start_transition(MenuState.SHOP)
                    return None
                if self.main_buttons["achievements"].is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                    self._burst_particles(self.main_buttons["achievements"].rect.center)
                    self._start_transition(MenuState.ACHIEVEMENTS)
                    return None
        return None

    def handle_character_select(self, events: list[pygame.event.Event]) -> Optional[str]:
        if self.popup:
            self._handle_popup(events)
            return None

        cols = 3
        char_w = 180
        char_h = 200
        margin_left = 80
        start_x = margin_left
        start_y = 210
        spacing_x = 25
        spacing_y = 40

        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                    self._start_transition(MenuState.MAIN)
                    return None

                for i, char in enumerate(self.characters):
                    try:
                        row = i // cols
                        col = i % cols
                        x = start_x + col * (char_w + spacing_x) + char_w // 2
                        y = start_y + row * (char_h + spacing_y)
                        rect = pygame.Rect(x - char_w // 2, y - char_h // 2, char_w, char_h)

                        if rect.collidepoint(self.mouse_pos):
                            if char.unlocked:
                                self._open_info_popup(char)
                            else:
                                self._open_buy_popup(char)
                    except Exception as e:
                        print(f"Error selecting character: {e}")
        return None

    def _open_info_popup(self, char: Character) -> None:
        self.popup_anim = 0.0
        self.popup_closing = False
        name_text = char.display_name if char.display_name else char.description
        popup_w = 520
        popup_h = 440
        popup_x = (WIDTH - popup_w) // 2
        popup_y = (HEIGHT - popup_h) // 2

        is_selected = char.name == self.game_data.selected_character
        equip_text = "卸下" if is_selected else "装备"
        equip_color = (180, 80, 80) if is_selected else (60, 140, 80)
        equip_hover = (220, 100, 100) if is_selected else (80, 180, 100)

        btn_w = 140
        self.popup_buttons = {
            "equip": Button(popup_x + 50, popup_y + popup_h - 65, btn_w, 45, equip_text, equip_color, equip_hover),
            "close": Button(popup_x + popup_w - btn_w - 50, popup_y + popup_h - 65, btn_w, 45, "关闭", (80, 80, 90), (110, 110, 120)),
        }
        self.popup = {"type": "info", "char": char, "rect": pygame.Rect(popup_x, popup_y, popup_w, popup_h)}

    def _open_buy_popup(self, char: Character) -> None:
        self.popup_anim = 0.0
        self.popup_closing = False
        name_text = char.display_name if char.display_name else char.description
        popup_w = 480
        popup_h = 340
        popup_x = (WIDTH - popup_w) // 2
        popup_y = (HEIGHT - popup_h) // 2

        can_afford = self.game_data.coins >= char.price
        buy_color = (60, 140, 80) if can_afford else (80, 80, 80)
        buy_hover = (80, 180, 100) if can_afford else (100, 100, 100)
        buy_text = f"购买 ({char.price}金币)" if can_afford else "金币不足"

        btn_w = 160
        self.popup_buttons = {
            "buy": Button(popup_x + 50, popup_y + popup_h - 65, btn_w, 45, buy_text, buy_color, buy_hover),
            "close": Button(popup_x + popup_w - btn_w - 50, popup_y + popup_h - 65, btn_w, 45, "取消", (80, 80, 90), (110, 110, 120)),
        }
        self.popup = {"type": "buy", "char": char, "rect": pygame.Rect(popup_x, popup_y, popup_w, popup_h)}

    def _buy_item(self, item: ShopItem) -> bool:
        if item.consumable:
            if self.game_data.coins >= item.price:
                self.game_data.coins -= item.price
                self.game_data.total_coins_spent += item.price
                self.game_data.item_uses[item.name] = self.game_data.item_uses.get(item.name, 0) + item.uses_per_purchase
                save_game_data(self.game_data)
                return True
        else:
            if item.name not in self.game_data.shop_items and self.game_data.coins >= item.price:
                self.game_data.coins -= item.price
                self.game_data.total_coins_spent += item.price
                self.game_data.shop_items.append(item.name)
                save_game_data(self.game_data)
                return True
        return False

    def _open_shop_popup(self, item: ShopItem) -> None:
        self.popup_anim = 0.0
        self.popup_closing = False
        popup_w = 400
        popup_h = 360
        popup_x = (WIDTH - popup_w) // 2
        popup_y = (HEIGHT - popup_h) // 2

        can_afford = self.game_data.coins >= item.price
        buy_color = (60, 140, 80) if can_afford else (80, 80, 80)
        buy_hover = (80, 180, 100) if can_afford else (100, 100, 100)
        buy_text = f"购买 ({item.price}金币)" if can_afford else "金币不足"

        btn_w = 140
        self.popup_buttons = {
            "buy": Button(popup_x + 40, popup_y + popup_h - 65, btn_w, 45, buy_text, buy_color, buy_hover),
            "close": Button(popup_x + popup_w - btn_w - 40, popup_y + popup_h - 65, btn_w, 45, "关闭", (80, 80, 90), (110, 110, 120)),
        }
        self.popup = {"type": "shop_buy", "item": item, "rect": pygame.Rect(popup_x, popup_y, popup_w, popup_h)}

    def _handle_popup(self, events: list[pygame.event.Event]) -> None:
        if self.popup_closing:
            return

        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN:
                if "close" in self.popup_buttons and self.popup_buttons["close"].is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                    self.popup_closing = True
                    return

                if self.popup["type"] == "info":
                    if "equip" in self.popup_buttons and self.popup_buttons["equip"].is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                        char = self.popup["char"]
                        if char.name == self.game_data.selected_character:
                            self.game_data.selected_character = ""
                        else:
                            self.game_data.selected_character = char.name
                        save_game_data(self.game_data)
                        self.popup_closing = True
                        return

                elif self.popup["type"] == "buy":
                    if "buy" in self.popup_buttons and self.popup_buttons["buy"].is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                        char = self.popup["char"]
                        if self.game_data.coins >= char.price:
                            self.game_data.coins -= char.price
                            self.game_data.unlocked_characters.append(char.name)
                            self.game_data.selected_character = char.name
                            self._update_character_unlock_status()
                            save_game_data(self.game_data)
                            self.popup_closing = True
                            return

                elif self.popup["type"] == "shop_buy":
                    if "buy" in self.popup_buttons and self.popup_buttons["buy"].is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                        item = self.popup["item"]
                        if self._buy_item(item):
                            self.popup_closing = True
                            return

        for btn in self.popup_buttons.values():
            btn.update(self.mouse_pos)

    def _draw_popup(self) -> None:
        if not self.popup:
            return

        if self.popup_closing:
            self.popup_anim = max(0.0, self.popup_anim - 0.08)
            if self.popup_anim <= 0.0:
                self.popup = None
                self.popup_buttons = {}
                self.popup_closing = False
                return
        else:
            self.popup_anim = min(1.0, self.popup_anim + 0.08)

        popup_rect = self.popup["rect"]
        popup_type = self.popup["type"]
        char = self.popup.get("char")
        name_text = char.display_name if char and char.display_name else (char.description if char else "")

        overlay_alpha = int(self.popup_anim * 160)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, overlay_alpha))
        self.screen.blit(overlay, (0, 0))

        y_offset = int((1.0 - self.popup_anim) * 25)
        anim_rect = popup_rect.move(0, y_offset)

        pygame.draw.rect(self.screen, (45, 50, 70), anim_rect, border_radius=20)
        shadow_rect = anim_rect.move(0, 4)
        pygame.draw.rect(self.screen, (25, 28, 40), shadow_rect, border_radius=20)
        pygame.draw.rect(self.screen, (120, 130, 160), anim_rect, 3, border_radius=20)
        popup_rect = anim_rect

        title_surf = self.font_medium.render(name_text, True, (255, 255, 255))
        self.screen.blit(title_surf, (popup_rect.x + 25, popup_rect.y + 20))

        if char:
            cat_x = popup_rect.x + 80
            cat_y = popup_rect.y + 170
            self.draw_cat_preview(cat_x, cat_y, char.color, 1.8, char.name)

        if popup_type == "info":
            story_lines = self._wrap_text(char.story, self.font_small, popup_rect.width - 200)
            for j, line in enumerate(story_lines[:6]):
                text_surf = self.font_small.render(line, True, (200, 200, 220))
                self.screen.blit(text_surf, (popup_rect.x + 170, popup_rect.y + 55 + j * 22))

            skill_label = self.font_small.render(f"技能: {char.skill_name}", True, (255, 220, 100))
            self.screen.blit(skill_label, (popup_rect.x + 170, popup_rect.y + 55 + len(story_lines[:6]) * 22 + 10))

            skill_lines = self._wrap_text(char.skill_desc, self.font_small, popup_rect.width - 200)
            for j, line in enumerate(skill_lines[:2]):
                text_surf = self.font_small.render(line, True, (180, 200, 180))
                self.screen.blit(text_surf, (popup_rect.x + 170, popup_rect.y + 55 + (len(story_lines[:6]) + 1) * 22 + 10 + j * 22))

        elif popup_type == "buy":
            confirm_text = self.font_medium.render(f"确认购买 {name_text}?", True, (255, 255, 255))
            self.screen.blit(confirm_text, (popup_rect.x + 170, popup_rect.y + 55))

            skill_label = self.font_small.render(f"技能: {char.skill_name}", True, (255, 220, 100))
            self.screen.blit(skill_label, (popup_rect.x + 170, popup_rect.y + 95))

            skill_lines = self._wrap_text(char.skill_desc, self.font_small, popup_rect.width - 200)
            for j, line in enumerate(skill_lines[:2]):
                text_surf = self.font_small.render(line, True, (180, 200, 180))
                self.screen.blit(text_surf, (popup_rect.x + 170, popup_rect.y + 120 + j * 22))

            self.draw_coin_icon(popup_rect.x + 170, popup_rect.y + popup_rect.height - 110, 0.8)
            coin_surf = self.font_medium.render(f"{char.price} 金币", True, (255, 220, 100))
            self.screen.blit(coin_surf, (popup_rect.x + 195, popup_rect.y + popup_rect.height - 125))

            balance_surf = self.font_small.render(f"(拥有: {self.game_data.coins} 金币)", True, (180, 180, 180))
            self.screen.blit(balance_surf, (popup_rect.x + 170, popup_rect.y + popup_rect.height - 95))

        elif popup_type == "shop_buy":
            item = self.popup["item"]

            title_surf = self.font_medium.render(item.name, True, (255, 255, 255))
            self.screen.blit(title_surf, (popup_rect.x + 30, popup_rect.y + 25))

            tag_surf = self.font_small.render(item.description, True, (180, 200, 180))
            self.screen.blit(tag_surf, (popup_rect.x + 30, popup_rect.y + 52))

            func_lines = self._wrap_text(item.function_desc, self.font_small, popup_rect.width - 60)
            for j, line in enumerate(func_lines[:4]):
                text_surf = self.font_small.render(line, True, (200, 200, 220))
                self.screen.blit(text_surf, (popup_rect.x + 30, popup_rect.y + 78 + j * 22))

            self.draw_coin_icon(popup_rect.x + 30, popup_rect.y + 190, 0.8)
            price_surf = self.font_medium.render(f"{item.price} 金币", True, (255, 220, 100))
            self.screen.blit(price_surf, (popup_rect.x + 55, popup_rect.y + 175))

            balance_surf = self.font_small.render(f"拥有: {self.game_data.coins} 金币", True, (180, 180, 180))
            self.screen.blit(balance_surf, (popup_rect.x + 30, popup_rect.y + 208))

            if item.consumable:
                info_surf = self.font_small.render("购买后获得 1 次使用次数", True, (100, 200, 255))
                self.screen.blit(info_surf, (popup_rect.x + 30, popup_rect.y + 245))

                uses = self.game_data.item_uses.get(item.name, 0)
                if uses > 0:
                    uses_surf = self.font_small.render(f"当前剩余: {uses}次", True, (180, 180, 200))
                    self.screen.blit(uses_surf, (popup_rect.x + 30, popup_rect.y + 267))

        for btn in self.popup_buttons.values():
            btn.draw(self.screen, self.font_small)

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> list[str]:
        lines = []
        current = ""
        for char in text:
            test = current + char
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
        return lines

    def handle_shop(self, events: list[pygame.event.Event]) -> Optional[str]:
        if self.popup:
            self._handle_popup(events)
            return None

        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                    self._start_transition(MenuState.MAIN)
                    return None

                for buy_rect, i in self._shop_buy_buttons:
                    if buy_rect.collidepoint(self.mouse_pos):
                        self._buy_item(self.shop_items[i])
                        return None

                item_h = 70
                start_y = 130
                sorted_items = sorted(enumerate(self.shop_items), key=lambda x: (
                    x[1].name in self.game_data.shop_items and not x[1].consumable
                ))
                for display_idx, (actual_idx, item) in enumerate(sorted_items):
                    y = start_y + display_idx * (item_h + 15)
                    rect = pygame.Rect(100, y, WIDTH - 200, item_h)
                    if rect.collidepoint(self.mouse_pos):
                        self._open_shop_popup(item)
                        return None

                toggle_rect = getattr(self, "_shop_toggle_rect", None)
                if toggle_rect and toggle_rect.collidepoint(self.mouse_pos):
                    self.game_data.items_disabled = not self.game_data.items_disabled
                    save_game_data(self.game_data)
                    return None
        return None

    def handle_achievements(self, events: list[pygame.event.Event]) -> Optional[str]:
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.is_clicked(self.mouse_pos, pygame.mouse.get_pressed()):
                    self._start_transition(MenuState.MAIN)
        return None

    def update_achievements(self, score: int, distance: float, revived: bool) -> None:
        if self.game_data.games_played == 0:
            if "初次奔跑" not in self.game_data.achievements:
                self.game_data.achievements.append("初次奔跑")
        if distance > 100:
            if "百米冲刺" not in self.game_data.achievements:
                self.game_data.achievements.append("百米冲刺")
        if distance > 1000:
            if "千米达人" not in self.game_data.achievements:
                self.game_data.achievements.append("千米达人")
        if len(self.game_data.unlocked_characters) >= len(self.characters):
            if "收藏家" not in self.game_data.achievements:
                self.game_data.achievements.append("收藏家")
        total_spent = self.game_data.total_coins_spent
        if total_spent >= 5000:
            if "购物狂" not in self.game_data.achievements:
                self.game_data.achievements.append("购物狂")
        if score >= 10000:
            if "常胜将军" not in self.game_data.achievements:
                self.game_data.achievements.append("常胜将军")
        if revived:
            if "永不放弃" not in self.game_data.achievements:
                self.game_data.achievements.append("永不放弃")
        save_game_data(self.game_data)

    def add_coins(self, amount: int) -> None:
        if "双倍金币" in self.game_data.shop_items:
            amount *= 2
        self.game_data.coins += amount
        save_game_data(self.game_data)

    def update_game_stats(self, score: int, distance: float, revived: bool = False) -> None:
        self.game_data.games_played += 1
        if score > self.game_data.high_score:
            self.game_data.high_score = score
        self.game_data.total_distance += distance
        self.update_achievements(score, distance, revived)
        save_game_data(self.game_data)

    def get_selected_character(self) -> Character:
        for char in self.characters:
            if char.name == self.game_data.selected_character:
                return char
        return self.characters[0]

    def has_item(self, item_name: str) -> bool:
        for item in self.shop_items:
            if item.name == item_name:
                if item.consumable:
                    return self.game_data.item_uses.get(item_name, 0) > 0
                break
        return item_name in self.game_data.shop_items

    def get_item_uses(self, item_name: str) -> int:
        return self.game_data.item_uses.get(item_name, 0)

    def use_item(self, item_name: str) -> bool:
        if self.game_data.item_uses.get(item_name, 0) > 0:
            self.game_data.item_uses[item_name] -= 1
            save_game_data(self.game_data)
            return True
        return False

    def add_item_uses(self, item_name: str, uses: int) -> None:
        self.game_data.item_uses[item_name] = self.game_data.item_uses.get(item_name, 0) + uses
        save_game_data(self.game_data)

    def _start_transition(self, target: MenuState) -> None:
        self.transition_target = target
        self.fade_state = "fade_out"
        self.transition_alpha = 0

    def _draw_scene(self) -> None:
        if self.state == MenuState.MAIN:
            self.draw_main_menu()
        elif self.state == MenuState.CHARACTER_SELECT:
            self.draw_character_select()
            self._draw_popup()
        elif self.state == MenuState.MAP_SELECT:
            self.draw_map_select()
        elif self.state == MenuState.SHOP:
            self.draw_shop()
            self._draw_popup()
        elif self.state == MenuState.ACHIEVEMENTS:
            self.draw_achievements()

    def _burst_particles(self, pos: tuple[int, int], count: int = 10) -> None:
        if not self.has_bg_image:
            return
        for _ in range(count):
            self.particles.append(CatParticle(
                pos[0], pos[1],
                vx_range=(-3.0, 3.0), vy_range=(-3.0, 3.0),
                life_decay=0.025, gravity=0.05, size_range=(5, 9),
            ))

    def run(self) -> Optional[str]:
        running = True
        while running:
            self.clock.tick(60)
            events = pygame.event.get()

            # 手机触控: 将 FINGERDOWN 转为 MOUSEBUTTONDOWN 事件
            extra_mouse_events: list[pygame.event.Event] = []
            for event in events:
                if event.type == pygame.FINGERDOWN:
                    mx = int(event.x * WIDTH)
                    my = int(event.y * HEIGHT)
                    extra_mouse_events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (mx, my)}))
                    extra_mouse_events.append(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (mx, my)}))
            if extra_mouse_events:
                events = list(events) + extra_mouse_events

            for event in events:
                if event.type == pygame.QUIT:
                    save_game_data(self.game_data)
                    return None

            if self.fade_state != "idle":
                self._draw_scene()
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, self.transition_alpha))
                self.screen.blit(overlay, (0, 0))
                step = 17
                if self.fade_state == "fade_out":
                    self.transition_alpha = min(255, self.transition_alpha + step)
                    if self.transition_alpha >= 255:
                        self.state = self.transition_target
                        self.transition_target = None
                        self.fade_state = "fade_in"
                elif self.fade_state == "fade_in":
                    self.transition_alpha = max(0, self.transition_alpha - step)
                    if self.transition_alpha <= 0:
                        self.fade_state = "idle"
            elif self.state == MenuState.MAIN:
                result = self.handle_main_menu(events)
                if result:
                    return result
                self.draw_main_menu()
            elif self.state == MenuState.CHARACTER_SELECT:
                result = self.handle_character_select(events)
                self.draw_character_select()
                self._draw_popup()
            elif self.state == MenuState.MAP_SELECT:
                result = self.handle_map_select(events)
                if result:
                    return result
                self.draw_map_select()
            elif self.state == MenuState.SHOP:
                result = self.handle_shop(events)
                self.draw_shop()
                self._draw_popup()
            elif self.state == MenuState.ACHIEVEMENTS:
                result = self.handle_achievements(events)
                self.draw_achievements()

            pygame.display.flip()

        return None
