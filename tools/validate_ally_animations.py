"""Validate actual Tk PNG loading and companion animation selection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D, ALLY_STYLES
from game_models import Companion


def main():
    game = DarkRuins2D(hidden=True)
    try:
        assert set(game.ally_animations) == set(ALLY_STYLES)
        for name, animations in game.ally_animations.items():
            assert len(animations) == 10
            for frames in animations.values():
                for frame in frames:
                    assert (frame.width(), frame.height()) == (84, 84)
                    assert frame.transparency_get(0, 0)
            companion = Companion(name, game.px, game.py)
            for direction in ("up", "down", "left", "right"):
                companion.facing = direction
                companion.moving = False
                assert game._ally_sprite(name, companion) is animations[f"idle_{direction}"][0]
                companion.moving = True
                for index in range(2):
                    companion.walk_time = (index + 0.1) / 7
                    assert game._ally_sprite(name, companion) is animations[f"walk_{direction}"][index]
            companion.pose = "attack"
            companion.pose_time = 0.45
            assert game._ally_sprite(name, companion) is animations["attack"][0]
            companion.pose_time = 0.1
            assert game._ally_sprite(name, companion) is animations["attack"][1]
            companion.pose = "heal"
            assert game._ally_sprite(name, companion) is animations["heal"][0]
            game._draw_ally(name, 100, 100, companion)
        companion = Companion("test", 0, 0, facing="left")
        for dx in (1, -1, 1, -1, 1, -1):
            game._update_companion_facing(companion, dx, 0, 1 / 60)
        assert companion.facing == "left", "jitter must not repeatedly flip the facing"
        for _ in range(8):
            game._update_companion_facing(companion, 1, 0, 1 / 60)
        assert companion.facing == "right", "sustained movement must update the facing"
        print("Companion validation passed: 45 actual transparent PNGs, four directions, walk, attack, heal, Canvas rendering.")
    finally:
        game.root.destroy()


if __name__ == "__main__":
    main()
