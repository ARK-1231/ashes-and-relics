"""Check that boss attack variety grows without losing unlocked attacks."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D


class BossProgressionTests(unittest.TestCase):
    def test_spawned_boss_health_and_damage_increase_each_tier(self):
        game = DarkRuins2D.__new__(DarkRuins2D)
        game.px = game.py = 0
        game.relics = []
        game._random_open_position = lambda *args, **kwargs: (100, 100)
        for tier, hp, damage in ((1, 240, 22), (2, 420, 31), (3, 600, 40)):
            with self.subTest(tier=tier):
                game.dungeon_number = tier
                boss = next(enemy for enemy in game._make_enemies() if enemy.boss)
                self.assertEqual(boss.hp, hp)
                self.assertEqual(boss.max_hp, hp)
                self.assertEqual(boss.damage, damage)

    def test_each_tier_and_phase_adds_attacks(self):
        game = DarkRuins2D.__new__(DarkRuins2D)
        previous_final = set()
        for tier, new_attack in enumerate(
            ("boss_lance", "boss_wave", "boss_spiral"), start=1,
        ):
            game.dungeon_number = tier
            first = game._boss_attack_pool(SimpleNamespace(boss_phase=1))
            second = game._boss_attack_pool(SimpleNamespace(boss_phase=2))
            self.assertEqual(len(first), tier + 1)
            self.assertEqual(len(second), tier + 2)
            self.assertTrue(previous_final <= set(first))
            self.assertEqual(set(second) - set(first), {new_attack})
            self.assertTrue(set(first) < set(second))
            self.assertEqual(len(second), len(set(second)))
            # The no-repeat selector must always have another attack available.
            for last_attack in second:
                self.assertTrue([attack for attack in first if attack != last_attack])
            previous_final = set(second)


if __name__ == "__main__":
    unittest.main()
