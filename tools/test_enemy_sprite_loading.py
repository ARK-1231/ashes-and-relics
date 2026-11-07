"""A broken enemy set must not disable unrelated enemies."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D, tk


class EnemySpriteLoadingTests(unittest.TestCase):
    def test_bad_set_is_excluded_atomically_and_other_sets_load(self):
        for failure in ("missing", "size"):
            with self.subTest(failure=failure):
                game = DarkRuins2D.__new__(DarkRuins2D)
                game.root = Mock()
                def load(**kwargs):
                    broken = "ash_healer" in kwargs["file"] and kwargs["file"].endswith("04.png")
                    if broken and failure == "missing":
                        raise tk.TclError("test missing frame")
                    return Mock(width=lambda: 48 if broken else 96, height=lambda: 96)
                with patch("dark_ruins_rpg.tk.PhotoImage", side_effect=load), patch("sys.stderr"):
                    sprites = game._load_enemy_sprites()
                self.assertEqual(len(sprites), 5)
                self.assertNotIn("灰の祈祷師", sprites)
                self.assertIn("灰の兵士", sprites)
                self.assertIn("盾の廃騎士", sprites)
                self.assertTrue(all(len(animations) == 12 for animations in sprites.values()))


if __name__ == "__main__":
    unittest.main()
