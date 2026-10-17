"""Repeatable crowded combat benchmark; --tk includes actual Tk rendering."""

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D
from game_models import Enemy, Projectile


def populate(game, enemies, bullets, seed):
    rng = random.Random(seed)
    game.enemies = [Enemy("灰の兵士", game.px + rng.uniform(-900, 900),
                          game.py + rng.uniform(-600, 600), 100, 10, 45, 20, "#aa6666",
                          cooldown=10) for _ in range(enemies)]
    game.projectiles = [Projectile(
        game.px + rng.uniform(-1500, 1500), game.py + rng.uniform(-1000, 1000),
        rng.uniform(-150, 150), rng.uniform(-150, 150), 10,
        life=0.001 if i % 3 == 0 else 4,
    ) for i in range(bullets)]
    game.hurt_invincible = 100
    game.screen_shake_time = 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tk", action="store_true")
    parser.add_argument("--frames", type=int, default=60)
    args = parser.parse_args()
    if args.frames < 1:
        parser.error("--frames must be positive")
    if args.tk:
        game = DarkRuins2D(hidden=True)
        # Map offscreen so Tk allocates a real 1280x720 viewport.
        game.root.geometry("1280x720+10000+10000")
        game.root.deiconify()
        game.root.update()
        assert (game.canvas.winfo_width(), game.canvas.winfo_height()) == (1280, 720)
    else:
        game = DarkRuins2D.__new__(DarkRuins2D)
    game._reset_game(stage_seed=1017)
    game.ui_mode = "playing"
    game._play_sound = lambda *_: None
    results = []
    try:
        for enemies, bullets in ((30, 100), (120, 600), (240, 1200)):
            timings = {"update_ms": [], "draw_ms": []}
            for frame in range(args.frames + 5):
                # Replenish each frame so collision/expiry does not drain the load.
                populate(game, enemies, bullets, 1017 + frame)
                start = time.perf_counter()
                game._update(1 / 60)
                game._update_effects(1 / 60)
                updated = time.perf_counter()
                if args.tk:
                    game._draw()
                    game.root.update_idletasks()
                drawn = time.perf_counter()
                if frame >= 5:
                    timings["update_ms"].append((updated - start) * 1000)
                    timings["draw_ms"].append((drawn - updated) * 1000)
            totals = [a + b for a, b in zip(*timings.values())]
            results.append({"enemies": enemies, "bullets": bullets,
                            "update_median_ms": round(statistics.median(timings["update_ms"]), 3),
                            "draw_median_ms": round(statistics.median(timings["draw_ms"]), 3),
                            "total_median_ms": round(statistics.median(totals), 3),
                            "total_p95_ms": round(sorted(totals)[int((len(totals) - 1) * .95)], 3)})
        print(json.dumps({"tk": args.tk, "frames": args.frames, "results": results}, indent=2))
    finally:
        if args.tk:
            game.root.destroy()


if __name__ == "__main__":
    main()
