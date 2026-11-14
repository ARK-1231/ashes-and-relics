"""Exercise terrain reuse, layer order, menus, and alpha composition in real Tk."""
import sys
import tkinter as tk
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D
from game_models import Enemy, Projectile


def main():
    game = DarkRuins2D(hidden=True)
    try:
        game.root.geometry("1280x720+10000+10000")
        game.root.deiconify()
        game.root.update()
        for callback in game.root.tk.splitlist(game.root.tk.call("after", "info")):
            game.root.after_cancel(callback)
        game.ui_mode = "playing"
        game._draw()
        background = tuple(item[1] for item in game.canvas._background_items)
        assert background
        for _ in range(5):
            game._draw()
            assert background == tuple(item[1] for item in game.canvas._background_items)
        first = Enemy("test", game.px + 40, game.py, 100, 10, 45, 20, "red")
        second = Enemy("test", game.px + 80, game.py, 100, 10, 45, 20, "red")
        bolt = Projectile(game.px + 30, game.py, 20, 0, 5)
        game.enemies = [first, second]
        game.projectiles = [bolt]
        game._draw()
        retained = {key: tuple(item[1] for item in game.canvas._groups[key])
                    for key in (("enemy", id(second)), ("projectile", id(bolt)), "player")}
        game.enemies.remove(first)
        second.x += 4
        bolt.x += 10
        game._draw()
        for key, items in retained.items():
            assert tuple(item[1] for item in game.canvas._groups[key]) == items
        assert ("enemy", id(first)) not in game.canvas._groups
        # Minimap updates at 10 Hz, but a resize invalidates it immediately.
        game._minimap_key = None
        game._draw_minimap_contents = Mock(wraps=game._draw_minimap_contents)
        for instant, expected in ((10, 1), (10.05, 1), (10.11, 2)):
            with patch("dark_ruins_rpg.time.perf_counter", return_value=instant):
                game._draw()
            assert game._draw_minimap_contents.call_count == expected
        with patch("dark_ruins_rpg.time.perf_counter", return_value=10.12):
            game.canvas.begin_frame()
            game._draw_minimap(1200, 720)
            game.canvas.end_frame()
        assert game._draw_minimap_contents.call_count == 3
        # Change the number and kind of foreground items, then move the camera.
        game.enemies.clear()
        game.attack_flash = 0.1
        game._draw()
        game.px += 48
        game._draw()
        stack = list(game.canvas.find_all())
        assert max(stack.index(item[1]) for item in game.canvas._background_items) < min(
            stack.index(item[1]) for item in game.canvas._frame_items)
        game.ui_mode = "title"
        game._draw()
        assert all(game.canvas.itemcget(item[1], "state") == "hidden"
                   for item in game.canvas._background_items)
        game.ui_mode = "playing"
        game._draw()
        assert all(game.canvas.itemcget(item[1], "state") == "normal"
                   for item in game.canvas._background_items)
        # A fully transparent pixel must retain the original terrain backing.
        source = tk.PhotoImage(master=game.root, width=2, height=1)
        source.put("#ff0000", to=(0, 0))
        flat = game._opaque_texture(source, "#303541")
        assert flat.get(0, 0) == (255, 0, 0)
        assert flat.get(1, 0) == (48, 53, 65)
        assert not flat.transparency_get(1, 0)
        game.ally_command = "guard"
        game.perfect_dodge_boost = 3
        game._draw()
        labels = [game.canvas.itemcget(item, "text") for item in game.canvas.find_all()
                  if game.canvas.type(item) == "text"]
        assert any("護衛" in label and "1.5" in label for label in labels)
        game._reset_game(stage_seed=1017, preserve_progress=True)
        assert game.ally_command == "guard" and game.perfect_dodge_boost == 0
        game._draw()
        game.root.update_idletasks()
        print("Terrain/entity reuse, minimap throttling, foreground order, camera movement, menus, and alpha checks passed.")
    finally:
        game.root.destroy()


if __name__ == "__main__":
    main()
