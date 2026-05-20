"""Generate reference road texture PNGs for each scene (720x960)."""

import os
import sys

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

from constants import HEIGHT, WIDTH
from road_scenes import RoadScene, build_road

pygame.display.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))

out_dir = os.path.join("assets", "roads")
os.makedirs(out_dir, exist_ok=True)

scenes = [
    (RoadScene.SUBURB, "suburb"),
    (RoadScene.DESERT, "desert"),
    (RoadScene.COAST, "coast"),
]

for scene, fname in scenes:
    surf = build_road(scene)
    path = os.path.join(out_dir, f"{fname}.png")
    pygame.image.save(surf, path)
    print(f"Saved {path}  ({surf.get_width()}x{surf.get_height()})")

pygame.quit()
print("\nDone! You can replace these PNGs with your own artwork.")