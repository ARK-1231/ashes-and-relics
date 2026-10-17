"""Input timing regressions; no display or sound device required."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D
from game_models import PLAYER_ATTACK_COOLDOWN


class InputResponseTests(unittest.TestCase):
    def setUp(self):
        self.game = DarkRuins2D.__new__(DarkRuins2D)
        self.game.ui_mode = "playing"
        self.game.game_over = False
        self.game.keys = set()
        self.game.ally_shield_cd = 0.0
        self.game.attack_cd = self.game.attack_flash = 0.0
        self.game.enemies = []
        self.game._play_sound = Mock()
        self.game._update_player_movement = Mock()

    def test_held_attack_does_not_wait_for_os_repeat(self):
        for key in ("f", "Return"):
            with self.subTest(key=key):
                self.setUp()
                self.game._key_down(SimpleNamespace(keysym=key))
                self.assertEqual(self.game._play_sound.call_count, 1)
                self.game._update_player_input(PLAYER_ATTACK_COOLDOWN / 2)
                self.assertEqual(self.game._play_sound.call_count, 1)
                self.game._update_player_input(PLAYER_ATTACK_COOLDOWN / 2)
                self.assertEqual(self.game._play_sound.call_count, 2)
                self.game._key_up(SimpleNamespace(keysym=key))
                self.game._update_player_input(PLAYER_ATTACK_COOLDOWN)
                self.assertEqual(self.game._play_sound.call_count, 2)

    def test_hit_stop_keeps_attack_and_movement_responsive(self):
        game = self.game
        game.keys = {"f", "d"}
        game.attack_cd = 0.01
        game.hit_stop_time = 0.045
        game.last_time = 1.0
        game.root = Mock()
        game._update_boss_gate = Mock()
        game._update_effects = Mock()
        game._draw = Mock()
        with patch("dark_ruins_rpg.time.perf_counter", return_value=1.02):
            game._loop()
        self.assertEqual(game._play_sound.call_count, 1)
        game._update_player_movement.assert_called_once()
        self.assertEqual(game.attack_cd, PLAYER_ATTACK_COOLDOWN)

    def test_attack_hits_all_enemies_inside_sector_but_not_through_walls(self):
        game = self.game
        game.px = game.py = 0
        game.facing = (1, 0)
        inside = [SimpleNamespace(x=30, y=0, radius=10),
                  SimpleNamespace(x=70, y=25, radius=10)]
        wall_hidden = SimpleNamespace(x=90, y=0, radius=10)
        outside = SimpleNamespace(x=-60, y=0, radius=10)
        game.enemies = inside + [wall_hidden, outside]
        game._line_blocked = lambda x1, y1, x2, y2, r: x2 == 90
        game._hit_enemy = Mock()
        game._remove_dead = Mock()
        game._attack()
        self.assertEqual([call.args[0] for call in game._hit_enemy.call_args_list], inside)
        game._remove_dead.assert_called_once()

    def test_sector_includes_overlapping_edges(self):
        game = self.game
        game.px = game.py = 0
        game.facing = (1, 0)
        for x, y, radius, expected in [
            (0, 0, 10, True), (110, 0, 0, True),
            (119, 0, 10, True), (121, 0, 10, False),
            (40, 75, 10, True), (40, 100, 10, False),
            (-50, 0, 10, False),
        ]:
            with self.subTest(x=x, y=y):
                self.assertEqual(game._in_attack_sector(
                    SimpleNamespace(x=x, y=y, radius=radius)), expected)


if __name__ == "__main__":
    unittest.main()
