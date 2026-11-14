"""Measure scheduled Tk input -> handler -> state change -> repaint idle.

Uses the real game loop and Tk event queue in an offscreen window. Results
exclude hardware/OS input delivery, compositor latency, and monitor scanout.
"""
import argparse
import json
import math
import statistics
import time
from types import SimpleNamespace

from benchmark_combat import DarkRuins2D, populate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=12)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    game = DarkRuins2D(hidden=True)
    game.root.geometry("1280x720+10000+10000")
    game.root.deiconify()
    game.root.update()
    game.ui_mode = "playing"
    game._play_sound = lambda *_: None
    game._reset_game(stage_seed=1017)
    populate(game, 30, 100, 1017)
    game._draw()
    game.root.update_idletasks()
    # Keep normal enemy movement/rendering but avoid combat ending a sample.
    game.hurt_invincible = 10000
    original_draw = game._draw
    original_move = game._move_player
    original_attack = game._attack
    original_movement = game._update_player_movement
    pending = None
    results = {action: [] for action in ("move", "attack", "dodge")}
    actions = [action for _ in range(args.samples) for action in results]
    action_index = 0
    failed = []

    def mark_state(action):
        if pending is not None and pending["action"] == action:
            pending.setdefault("state", time.perf_counter())

    def move(dx, dy):
        previous = game.px, game.py
        original_move(dx, dy)
        if previous != (game.px, game.py):
            mark_state("move")

    def attack():
        previous = game.attack_cd
        original_attack()
        if previous == 0 and game.attack_cd > 0:
            mark_state("attack")

    def movement(dt):
        previous = game.dodge_cd
        original_movement(dt)
        if previous == 0 and game.dodge_cd > 0:
            mark_state("dodge")

    def completed():
        nonlocal pending, action_index
        if pending is None:
            return
        end = time.perf_counter()
        results[pending["action"]].append({
            "queue_ms": (pending["handled"] - pending["due"]) * 1000,
            "state_ms": (pending["state"] - pending["due"]) * 1000,
            "repaint_idle_ms": (end - pending["due"]) * 1000,
        })
        game._clear_input()
        pending = None
        action_index += 1
        if action_index == len(actions):
            game.root.quit()
        else:
            game.root.after(25, prepare)

    def draw():
        original_draw()
        if pending is not None and "state" in pending and not pending.get("finishing"):
            pending["finishing"] = True
            # Canvas schedules its repaint idle task during original_draw().
            game.root.after_idle(completed)

    def handle(_event):
        if pending is None:
            return
        pending["handled"] = time.perf_counter()
        action = pending["action"]
        key = {"move": "d", "attack": "f", "dodge": "space"}[action]
        game._key_down(SimpleNamespace(keysym=key))

    def prepare():
        nonlocal pending
        game._clear_input()
        game.px, game.py = 1440, 2760
        game.attack_cd = game.dodge_cd = game.dodge_time = 0
        game.hit_stop_time = 0
        delay = 7 + action_index % 13
        pending = {"action": actions[action_index], "due": time.perf_counter() + delay / 1000}
        game.root.after(delay, lambda: game.root.event_generate("<<LatencyProbe>>", when="tail"))

    def timeout():
        failed.append("Input latency benchmark timed out")
        game.root.quit()

    game._move_player = move
    game._attack = attack
    game._update_player_movement = movement
    game._draw = draw
    game.root.bind("<<LatencyProbe>>", handle)
    game.last_time = time.perf_counter()
    game.root.after(100, prepare)
    game.root.after(max(15000, args.samples * 3000), timeout)
    try:
        game.root.mainloop()
        if failed:
            raise RuntimeError(failed[0])
        summary = {}
        for action, samples in results.items():
            summary[action] = {"samples": len(samples)}
            for name in ("queue_ms", "state_ms", "repaint_idle_ms"):
                values = sorted(sample[name] for sample in samples)
                summary[action][name] = {
                    "median": round(statistics.median(values), 3),
                    "p95": round(values[max(0, math.ceil(len(values) * .95) - 1)], 3),
                }
        print(json.dumps({"enemies_at_start": 30, "bullets_at_start": 100,
                          "measurement": "synthetic Tk input to repaint idle; excludes display scanout",
                          "results": summary}, indent=2))
    finally:
        game.root.destroy()


if __name__ == "__main__":
    main()
