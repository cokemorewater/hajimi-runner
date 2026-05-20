import os
import sys
import math

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

pygame.init()

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cats")
os.makedirs(OUT_DIR, exist_ok=True)

CATS = [
    ("cat_orange", (232, 140, 60), "小菊花"),
    ("cat_gray", (140, 140, 150), "灰绅士"),
    ("cat_white", (245, 240, 230), "雪团团"),
    ("cat_black", (50, 45, 55), "夜影"),
    ("cat_pink", (255, 180, 200), "樱花酱"),
    ("cat_gold", (255, 215, 0), "金宝"),
    ("cat_blue", (100, 150, 255), "星小蓝"),
]

SIZE = 160


def draw_cat(surf: pygame.Surface, color: tuple[int, int, int]) -> None:
    s = 1.0
    cx, cy = SIZE // 2, SIZE // 2 + 15

    r, g, b = color
    fur_dark = (max(0, r - 60), max(0, g - 40), max(0, b - 25))
    fur_mid = color
    fur_light = (min(255, r + 30), min(255, g + 30), min(255, b + 20))
    fur_hi = (min(255, r + 50), min(255, g + 50), min(255, b + 50))
    fur_belly = (min(255, r + 20), min(255, g + 30), min(255, b + 40))
    pink = (228, 165, 178)

    tail_bx = cx + int(18 * s)
    tail_by = cy + int(16 * s)
    tail_pts = [
        (tail_bx, tail_by),
        (tail_bx + 16, tail_by - 8),
        (tail_bx + 26, tail_by - 24),
        (tail_bx + 14, tail_by - 32),
    ]
    pygame.draw.lines(surf, fur_dark, False, tail_pts, 5)
    pygame.draw.lines(surf, fur_mid, False, tail_pts, 3)

    paw_offsets = [(-11, -4), (11, -4), (-10, 22), (10, 22)]
    for px, py in paw_offsets:
        pygame.draw.ellipse(surf, fur_dark, (cx + px - 5, cy + py - 3, 10, 12))
        pygame.draw.ellipse(surf, (48, 38, 30), (cx + px - 2, cy + py + 4, 5, 4))

    chest = pygame.Rect(0, 0, int(46 * s), int(28 * s))
    chest.center = (cx, cy + 2)
    haunch = pygame.Rect(0, 0, int(40 * s), int(30 * s))
    haunch.center = (cx, cy + 18)
    pygame.draw.ellipse(surf, fur_mid, chest)
    pygame.draw.ellipse(surf, fur_light, chest.inflate(-8, -6))
    pygame.draw.ellipse(surf, fur_mid, haunch)
    pygame.draw.ellipse(surf, fur_light, haunch.inflate(-6, -6))
    pygame.draw.ellipse(surf, fur_belly, (cx - 12, cy + 2, 24, 18))
    pygame.draw.line(surf, fur_dark, (chest.centerx, chest.top + 4), (haunch.centerx, haunch.bottom - 4), 2)

    for ox in (-10, 0, 10):
        pygame.draw.arc(
            surf, fur_dark,
            pygame.Rect(chest.centerx + ox - 7, chest.centery - 7, 14, 20),
            0.2 * math.pi, 0.95 * math.pi, 2,
        )

    hx, hy = cx, cy - int(24 * s)
    head_r = int(20 * s)
    pygame.draw.circle(surf, fur_mid, (hx, hy), head_r)
    pygame.draw.circle(surf, fur_light, (hx, hy - 1), head_r - 5)
    pygame.draw.circle(surf, fur_dark, (hx, hy), head_r, 2)

    ear_l = [(hx - head_r + 1, hy), (hx - head_r - 8, hy - head_r - 2), (hx - 5, hy - head_r + 3)]
    ear_r = [(hx + head_r - 1, hy), (hx + head_r + 8, hy - head_r - 2), (hx + 5, hy - head_r + 3)]
    pygame.draw.polygon(surf, fur_mid, ear_l)
    pygame.draw.polygon(surf, fur_mid, ear_r)
    pygame.draw.polygon(surf, pink, [(hx - head_r + 1, hy + 1), (hx - head_r + 1, hy - head_r + 3), (hx - 5, hy - 2)])
    pygame.draw.polygon(surf, pink, [(hx + head_r - 1, hy + 1), (hx + head_r - 1, hy - head_r + 3), (hx + 5, hy - 2)])
    pygame.draw.polygon(surf, fur_dark, ear_l, 2)
    pygame.draw.polygon(surf, fur_dark, ear_r, 2)

    pygame.draw.ellipse(surf, (248, 250, 252), (hx - 14, hy - 7, 10, 12))
    pygame.draw.ellipse(surf, (248, 250, 252), (hx + 4, hy - 7, 10, 12))
    pygame.draw.circle(surf, (32, 38, 48), (hx - 9, hy - 1), int(4 * s))
    pygame.draw.circle(surf, (32, 38, 48), (hx + 9, hy - 1), int(4 * s))
    pygame.draw.circle(surf, (255, 255, 255), (hx - 11, hy - 3), 2)
    pygame.draw.circle(surf, (255, 255, 255), (hx + 7, hy - 3), 2)

    pygame.draw.ellipse(surf, fur_hi, (hx - 10, hy + 9, 20, 10))
    pygame.draw.circle(surf, (42, 36, 34), (hx, hy + 12), 3)

    for dx, dy in ((-7, -9), (0, -11), (7, -9)):
        pygame.draw.line(surf, (240, 235, 230), (hx - 11, hy + 10), (hx - 24 + dx, hy - 4 + dy), 1)
        pygame.draw.line(surf, (240, 235, 230), (hx + 11, hy + 10), (hx + 24 + dx, hy - 4 + dy), 1)


for name, color, display_name in CATS:
    surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    draw_cat(surf, color)

    path = os.path.join(OUT_DIR, f"{name}.png")
    pygame.image.save(surf, path)
    print(f"✓ {display_name} → {path}")

pygame.quit()
print("\n全部生成完毕！")