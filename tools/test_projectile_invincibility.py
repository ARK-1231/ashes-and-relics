"""Verify hit protection for each boss projectile without a GUI."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D
from game_models import Projectile


class ProjectileInvincibilityTests(unittest.TestCase):
    def make_game(self, style):
        game = DarkRuins2D.__new__(DarkRuins2D)
        game.px = game.py = 0
        game.hp = 100
        game.player_shield = 0
        game.dodge_time = game.hurt_invincible = game.hit_stop_time = 0
        game.has_ally = False
        game.allies = set()
        game.armor_bonus = 0
        game.skill = "blade"
        game._inside_boss_arena = Mock(return_value=True)
        game._line_blocked = Mock(return_value=False)
        for name in ("_start_screen_shake", "_play_sound", "_knockback_player", "_say"):
            setattr(game, name, Mock())
        game.projectiles = [
            Projectile(0, 0, 0, 0, 10, boss_attack=True, style=style)
            for _ in range(2)
        ]
        return game

    def test_only_lance_and_spiral_allow_consecutive_hits(self):
        for style in ("lance", "spiral", "fan", "ring", "wave", "normal"):
            with self.subTest(style=style):
                game = self.make_game(style)
                game._update_projectiles(0)
                unprotected = style in {"lance", "spiral"}
                self.assertEqual(game.hp, 80 if unprotected else 90)
                self.assertEqual(game.hurt_invincible, 0 if unprotected else 0.55)

    def test_dodge_and_existing_hit_protection_are_preserved(self):
        for style in ("lance", "spiral"):
            for timer in ("dodge_time", "hurt_invincible"):
                with self.subTest(style=style, timer=timer):
                    game = self.make_game(style)
                    setattr(game, timer, 0.2)
                    game._update_projectiles(0)
                    self.assertEqual(game.hp, 100)
                    self.assertEqual(getattr(game, timer), 0.2)

    def test_melee_keeps_default_hit_protection(self):
        game = self.make_game("normal")
        game._damage_player(10, "melee")
        game._damage_player(10, "melee")
        self.assertEqual(game.hp, 90)
        self.assertEqual(game.hurt_invincible, 0.55)


if __name__ == "__main__":
    unittest.main()
