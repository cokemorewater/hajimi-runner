"""Detect lane markings ONLY within the road surface area."""

import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

pygame.display.init()
pygame.display.set_mode((1, 1))

from assets import load_road_texture, clear_road_cache
clear_road_cache()

TARGET_W, TARGET_H = 720, 960


def scale_and_crop(tex):
    tw, th = tex.get_size()
    scale = max(TARGET_W / tw, TARGET_H / th)
    new_w = int(tw * scale)
    new_h = int(th * scale)
    scaled = pygame.transform.smoothscale(tex, (new_w, new_h))
    crop_y = (new_h - TARGET_H) // 2
    crop_x = (new_w - TARGET_W) // 2
    return scaled, crop_x, crop_y


for scene_name in ["suburb", "desert", "coast"]:
    tex = load_road_texture(scene_name)
    if tex is None:
        continue

    scaled, crop_x, crop_y = scale_and_crop(tex)
    print(f"\n=== {scene_name} ===")

    all_lane_marks = {240: [], 360: [], 480: [], 600: [], 720: []}

    for sy in [240, 360, 480, 600, 720]:
        # Step 1: find road area (dark continuous region in center)
        pixels = []
        for sx in range(TARGET_W):
            r, g, b, _ = scaled.get_at((crop_x + sx, crop_y + sy))
            pixels.append((r + g + b) / 3)

        avg = sum(pixels) / len(pixels)
        threshold = avg * 0.82

        road_segments = []
        in_road = False
        seg_start = 0
        for sx in range(TARGET_W):
            if pixels[sx] < threshold:
                if not in_road:
                    seg_start = sx
                    in_road = True
            else:
                if in_road:
                    w = sx - seg_start
                    if w > 80:
                        road_segments.append((seg_start, sx))
                    in_road = False
        if in_road:
            w = TARGET_W - seg_start
            if w > 80:
                road_segments.append((seg_start, TARGET_W))

        if not road_segments:
            continue

        main_road = max(road_segments, key=lambda s: s[1] - s[0])
        road_left, road_right = main_road

        # Step 2: find bright lines within road area
        bright_xs = []
        for sx in range(road_left, road_right):
            r, g, b, _ = scaled.get_at((crop_x + sx, crop_y + sy))
            if (r + g + b) / 3 > 130:
                bright_xs.append(sx)

        if bright_xs:
            groups = []
            g_start = bright_xs[0]
            g_end = bright_xs[0]
            for i in range(1, len(bright_xs)):
                if bright_xs[i] - bright_xs[i-1] <= 6:
                    g_end = bright_xs[i]
                else:
                    if g_end - g_start >= 2:
                        groups.append((g_start + g_end) // 2)
                    g_start = bright_xs[i]
                    g_end = bright_xs[i]
            if g_end - g_start >= 2:
                groups.append((g_start + g_end) // 2)

            all_lane_marks[sy] = groups
            print(f"  row {sy}: road={road_left}..{road_right}  marks={groups}")

    # Collect consistent markings across rows
    all_marks = []
    for marks in all_lane_marks.values():
        all_marks.extend(marks)
    if not all_marks:
        continue

    # Cluster similar x positions
    all_marks.sort()
    clusters = []
    for m in all_marks:
        found = False
        for c in clusters:
            if abs(c["avg"] - m) < 20:
                c["sum"] += m
                c["count"] += 1
                c["avg"] = c["sum"] / c["count"]
                found = True
                break
        if not found:
            clusters.append({"sum": m, "count": 1, "avg": float(m)})

    clusters.sort(key=lambda c: c["avg"])
    print(f"\n  Clustered marks: {[int(c['avg']) for c in clusters]}")

    # Identify lane dividers (lines between lanes)
    # A 3-lane road has 2 lane dividers + 2 edge lines = 4 lines
    # Or sometimes 3 lane dividers for 4 lanes
    marks = [int(c["avg"]) for c in clusters]

    # Filter to likely lane markings (within road, reasonable spacing)
    if len(marks) >= 2:
        # The lane dividers are the middle markings
        # For 3 lanes: 2 dividers between 3 lanes
        if len(marks) == 4:
            # 4 lines = 2 edges + 2 lane dividers (3 lanes)
            left_edge, div1, div2, right_edge = marks
            l0 = (left_edge + div1) // 2
            l1 = (div1 + div2) // 2
            l2 = (div2 + right_edge) // 2
            print(f"  >> 3-lane interpretation: [{l0}, {l1}, {l2}]")
        elif len(marks) == 3:
            # 3 lines = left edge, center divider, right edge (2 lanes)
            # Or left edge + 2 lane dividers with implicit right edge
            print(f"  >> 3 marks, manual interpretation needed")
        elif len(marks) >= 5:
            # 5+ lines = more lanes or double lines
            # Take middle ones as lane dividers
            mid = len(marks) // 2
            print(f"  >> {len(marks)} marks, likely multi-lane")

    print()

pygame.quit()