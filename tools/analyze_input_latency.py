"""Measure Canvas submission and Tk repaint separately; use an offscreen window."""
import json
import statistics
import time
import tkinter as tk

from benchmark_combat import DarkRuins2D, populate


def main():
    game = DarkRuins2D(hidden=True)
    game.root.geometry("1280x720+10000+10000")
    game.root.deiconify()
    game.root.update()
    # Stop the scheduled game loop so only the measured frames run.
    for callback in game.root.tk.splitlist(game.root.tk.call("after", "info")):
        game.root.after_cancel(callback)
    game._play_sound = lambda *_: None
    textures = game.environment_textures
    minimap = game._draw_minimap
    results = []
    try:
        for mode in ("baseline", "opaque_environment", "no_environment_textures", "no_floor_texture", "no_wall_texture", "no_minimap", "no_enemy_sprites"):
            game._reset_game(stage_seed=1017)
            game.ui_mode = "playing"
            game.environment_textures = {} if mode == "no_environment_textures" else textures
            if mode == "opaque_environment":
                game.environment_textures = {
                    key: tk.PhotoImage(data=value.data(format="ppm"), format="ppm")
                    for key, value in textures.items()
                }
            game.floor_texture_canvases.clear()
            game.wall_texture_sizes.clear()
            if mode in {"no_floor_texture", "no_wall_texture"}:
                omitted = "floor" if mode == "no_floor_texture" else "wall"
                game.environment_textures = {key: value for key, value in textures.items() if key != omitted}
            game._draw_minimap = (lambda *_: None) if mode == "no_minimap" else minimap
            game._enemy_sprite = (lambda *_: None) if mode == "no_enemy_sprites" else DarkRuins2D._enemy_sprite.__get__(game)
            timings = []
            for frame in range(35):
                populate(game, 30, 100, 1017 + frame)
                start = time.perf_counter()
                game._update(1 / 60)
                game._update_effects(1 / 60)
                updated = time.perf_counter()
                game._draw()
                submitted = time.perf_counter()
                game.root.update_idletasks()
                painted = time.perf_counter()
                if frame >= 5:
                    timings.append(((updated-start)*1000, (submitted-updated)*1000,
                                    (painted-submitted)*1000, (painted-start)*1000))
            results.append({"mode": mode, "median_ms": dict(zip(
                ("update", "canvas_commands", "tk_repaint", "total"),
                (round(statistics.median(values), 3) for values in zip(*timings)))),
                "canvas_items": len(game.canvas.find_all())})
        print(json.dumps(results, indent=2))
    finally:
        game.root.destroy()


if __name__ == "__main__":
    main()
