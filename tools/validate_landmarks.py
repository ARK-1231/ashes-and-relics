"""Validate actual Tk landmark placement and sprite overlap; export a preview."""

import argparse
import base64
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D
from validate_sprites import read_alpha, opaque_bounds


def export_preview(game, output):
    """Export actual Tk coordinates/stacking as SVG, without desktop capture."""
    root = Path(__file__).resolve().parents[1]
    images = {str(image): (root / "assets/sprites/landmarks" / f"{key}.png", image)
              for key, image in game.landmark_sprites.items()}
    images[str(game.player_sprites["idle_down"][0])] = (
        root / "assets/sprites/player/frames_v5/down/idle/01.png", game.player_sprites["idle_down"][0])
    images[str(game._ally_sprite("ミラ"))] = (
        root / "assets/sprites/allies/frames_v2/mira/idle_down/00.png", game._ally_sprite("ミラ"))
    svg = ET.Element("svg", xmlns="http://www.w3.org/2000/svg", width="1080", height="840")
    for item in game.canvas.find_all():
        kind, coords = game.canvas.type(item), game.canvas.coords(item)
        fill = game.canvas.itemcget(item, "fill") if kind != "image" else ""
        if kind == "image":
            path, image = images[game.canvas.itemcget(item, "image")]
            ET.SubElement(svg, "image", x=str(coords[0]-image.width()/2),
                          y=str(coords[1]-image.height()), width=str(image.width()), height=str(image.height()),
                          href="data:image/png;base64," + base64.b64encode(path.read_bytes()).decode())
        elif kind == "text":
            node = ET.SubElement(svg, "text", x=str(coords[0]), y=str(coords[1]), fill=fill,
                                 attrib={"text-anchor": "middle", "dominant-baseline": "central",
                                         "font-family": "Yu Gothic UI, sans-serif", "font-size": "14"})
            node.text = game.canvas.itemcget(item, "text")
        elif kind == "rectangle":
            ET.SubElement(svg, "rect", x=str(coords[0]), y=str(coords[1]),
                          width=str(coords[2]-coords[0]), height=str(coords[3]-coords[1]), fill=fill or "none")
        elif kind in ("line", "polygon"):
            outline = fill if kind == "line" else game.canvas.itemcget(item, "outline")
            ET.SubElement(svg, "polyline" if kind == "line" else "polygon",
                          points=" ".join(f"{coords[i]},{coords[i+1]}" for i in range(0, len(coords), 2)),
                          fill="none" if kind == "line" else fill, stroke=outline or "none",
                          attrib={"stroke-width": game.canvas.itemcget(item, "width")})
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(svg).write(output, encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    game = DarkRuins2D(hidden=True)
    try:
        assert set(game.landmark_sprites) == {"shrine", "stairs", "exit"}
        for key, sprite in game.landmark_sprites.items():
            path = Path(__file__).resolve().parents[1] / "assets/sprites/landmarks" / f"{key}.png"
            width, height, alpha = read_alpha(path)
            left, top, right, bottom, count = opaque_bounds(alpha)
            assert (width, height) == (128, 128) and count > 0
            assert game.landmark_ground_offsets[key] == height - bottom - 1
            print(f"{key}: frame={width}x{height}, visible={right-left+1}x{bottom-top+1}, "
                  f"ground offset={game.landmark_ground_offsets[key]}")

        # Verify player, companion and enemy sprites on both sides of each object.
        sprites = [game.player_sprites["idle_down"][0], game.ally_sprites["ミラ"],
                   game.enemy_sprites["灰の兵士"]["idle_down"][0]]
        checks = 0
        for key in ("shrine", "stairs", "exit"):
            for sprite in sprites:
                for dy in (-35, 0, 35):
                    game.canvas.begin_frame()
                    landmark = game._draw_landmark(key, 200, 200, 34, "blue", key)
                    actor = game.canvas.create_image(200, 200 + dy + 7, image=sprite, anchor="s")
                    hud = game.canvas.create_text(200, 30, text="overlay")
                    game._order_landmark_overlaps(
                        [] if key == "stairs" else [(200, 200, landmark)], [(200, 200 + dy, actor)])
                    order = list(game.canvas.find_all())
                    assert (order.index(landmark) > order.index(actor)) == (key != "stairs" and dy < 0)
                    assert order.index(hud) > max(order.index(landmark), order.index(actor))
                    game.canvas.end_frame()
                    checks += 1

        # Exercise the complete renderer at the real map coordinates as well.
        game.root.geometry("1280x720+10000+10000")
        game.root.deiconify()
        game.root.update_idletasks()
        game.ui_mode = "playing"
        game.enemies = []
        game.ally_candidate_name = ""
        for dungeon, key, world_y in ((1, "shrine", 2490), (1, "stairs", 345),
                                      (2, "stairs", 345), (3, "exit", 345)):
            game.dungeon_number = dungeon
            _, _, alpha = read_alpha(Path(__file__).resolve().parents[1]
                                      / "assets/sprites/landmarks" / f"{key}.png")
            left, top, right, bottom, _ = opaque_bounds(alpha)
            visual = (1440 - 64 + left, world_y - bottom - 1 + top,
                      right - left + 1, bottom - top + 1)
            assert not any(game._rects_overlap(visual, wall, 0) for wall in game.walls)
            for dy in (-35, 0, 35):
                game.px, game.py = 1440, world_y + dy
                assert not game._blocked(game.px, game.py, 20)
                game._draw()
                game.root.update_idletasks()
                assert any(game.canvas.type(item) == "image"
                           and game.canvas.itemcget(item, "image") == str(game.landmark_sprites[key])
                           for item in game.canvas.find_all())
        print("Map placement passed: 12 complete scene draws, floor variants, wall clearance.")

        if args.preview:
            game.root.geometry("1080x840+10000+10000")
            game.root.deiconify()
            game.root.update_idletasks()
            game.canvas.begin_frame()
            game.canvas.create_rectangle(0, 0, 1080, 840, fill="#303541", outline="")
            for col, key in enumerate(("shrine", "stairs", "exit")):
                for row, (label, dy) in enumerate((("Behind", -35), ("At base", 0), ("In front", 35))):
                    x, y = col * 360 + 180, row * 280 + 185
                    game.canvas.create_text(x, row * 280 + 25, text=f"{key} / {label}", fill="white")
                    game.canvas.create_line(x-110, y, x+110, y, fill="#718093", dash=(3, 4))
                    landmark = game._draw_landmark(key, x, y, 34, "blue", key)
                    player = game.canvas.create_image(x-18, y+dy+7,
                                                     image=game.player_sprites["idle_down"][0], anchor="s")
                    ally = game._draw_ally("ミラ", x+40, y+dy)
                    game._order_landmark_overlaps(
                        [] if key == "stairs" else [(x, y, landmark)],
                        [(x-18, y+dy, player), (x+40, y+dy, ally)])
            game.canvas.end_frame()
            game.root.update_idletasks()
            export_preview(game, args.preview.resolve())
            print(f"Preview: {args.preview.resolve()}")
        print(f"Landmark validation passed: {checks} actual Tk overlap cases, ground alignment, HUD layering.")
    finally:
        game.root.destroy()


if __name__ == "__main__":
    main()
