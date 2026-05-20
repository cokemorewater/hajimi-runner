"""Generate sprite sheets for all cats (or a specific one).

Sprite sheet format (for import into the game):
  - Single PNG image, rows = actions, columns = frames
  - Row 0: run frames, Row 1: jump frames, Row 2: slide frames
  - Each frame: 70×70 pixels
  - Columns per row = number of frames

Usage:
  python generate_sheet.py           # generate for all cats
  python generate_sheet.py cat_blue  # generate for a specific cat
"""

import math
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)

import pygame

from cat_player import Player

CATS = {
    "cat_orange": (232, 140, 60),
    "cat_gray": (140, 140, 150),
    "cat_white": (245, 240, 230),
    "cat_black": (50, 45, 55),
    "cat_pink": (255, 180, 200),
    "cat_gold": (255, 215, 0),
    "cat_blue": (100, 150, 255),
}

FW, FH = 70, 70


def generate_sheet(name: str, color: tuple[int, int, int]) -> str:
    player = Player()

    # 跑动动画：10帧
    run_phases = [i / 10 for i in range(10)]
    jump_progresses = [0.05, 0.15, 0.3, 0.5, 0.7, 0.85, 0.95, 0.95, 0.95, 0.95]
    slide_progresses = [0.05, 0.15, 0.3, 0.5, 0.7, 0.85, 0.95, 0.95, 0.95, 0.95]

    cols = max(len(run_phases), len(jump_progresses), len(slide_progresses))
    rows = 3
    sheet = pygame.Surface((cols * FW, rows * FH), pygame.SRCALPHA)

    for i, phase in enumerate(run_phases):
        frame = pygame.Surface((FW, FH), pygame.SRCALPHA)
        player._draw_run_procedural(frame, FW // 2, FH // 2 + 6, phase, color)
        sheet.blit(frame, (i * FW, 0))

    for i, prog in enumerate(jump_progresses):
        frame = pygame.Surface((FW, FH), pygame.SRCALPHA)
        player._draw_jump_procedural(frame, FW // 2, FH // 2 + 6, color)
        sheet.blit(frame, (i * FW, FH))

    for i, prog in enumerate(slide_progresses):
        frame = pygame.Surface((FW, FH), pygame.SRCALPHA)
        slide_scale = 0.35 + 0.15 * math.sin(prog * math.pi)
        player._draw_slide_procedural(frame, FW // 2, FH // 2 + 4, slide_scale, color)
        sheet.blit(frame, (i * FW, FH * 2))

    out_path = os.path.join(_ROOT, "assets", "cats", f"{name}_sheet.png")
    pygame.image.save(sheet, out_path)
    print(f"  {name}_sheet.png  ({sheet.get_width()}x{sheet.get_height()})  run:{len(run_phases)} jump:{len(jump_progresses)} slide:{len(slide_progresses)}")
    return out_path


def main() -> None:
    pygame.init()

    target = sys.argv[1] if len(sys.argv) > 1 else None

    if target:
        if target in CATS:
            print(f"Generating sprite sheet for: {target}")
            generate_sheet(target, CATS[target])
        else:
            print(f"Unknown cat: {target}")
            print(f"Available: {', '.join(CATS.keys())}")
    else:
        print(f"Generating sprite sheets for all {len(CATS)} cats...")
        for name, color in CATS.items():
            generate_sheet(name, color)
        print("Done!")

    pygame.quit()


if __name__ == "__main__":
    main()