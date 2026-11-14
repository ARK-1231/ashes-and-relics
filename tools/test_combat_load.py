"""Check crowded combat behavior independently of Tk and timing thresholds."""

import copy
import math
import random
import sys
import unittest
from unittest.mock import Mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D, MAX_PARTICLES, MAX_LIGHT_RINGS
from game_models import Enemy, Projectile, Particle, LightRing


def separate_reference(game):
    """Original all-pairs behavior, retained as a regression oracle."""
    for index, first in enumerate(game.enemies):
        for second in game.enemies[index + 1:]:
            dx, dy = second.x - first.x, second.y - first.y
            distance = math.hypot(dx, dy)
            minimum = first.radius + second.radius + 6
            if distance >= minimum:
                continue
            if distance < .001:
                angle = game.rng.random() * math.tau
                ux, uy = math.cos(angle), math.sin(angle)
                push = minimum / 2
            else:
                ux, uy = dx / distance, dy / distance
                push = (minimum - distance) / 2
            x, y = first.x - ux * push, first.y - uy * push
            xx, yy = second.x + ux * push, second.y + uy * push
            if not game._blocked(x, y, first.radius):
                first.x, first.y = x, y
            if not game._blocked(xx, yy, second.radius):
                second.x, second.y = xx, yy


class CombatLoadTests(unittest.TestCase):
    def test_repeated_combat_effects_have_bounded_storage(self):
        game = DarkRuins2D.__new__(DarkRuins2D)
        game.rng = random.Random(5)
        game.particles = []
        game.light_rings = []
        game.screen_flash_time = 0
        for _ in range(100):
            game._spawn_visual_effect(10, 10, "red", 24, 40, "white", .1)
        self.assertEqual(len(game.particles), MAX_PARTICLES)
        self.assertEqual(len(game.light_rings), MAX_LIGHT_RINGS)
        game.screen_shake_time = game.screen_shake_strength = 0
        game._update_effects(1)
        self.assertEqual(game.particles, [])
        self.assertEqual(game.light_rings, [])

    def test_offscreen_effects_are_culled_but_visible_edges_are_drawn(self):
        game = DarkRuins2D.__new__(DarkRuins2D)
        game.canvas = Mock()
        game.screen_flash_time = 0
        game.particles = [Particle(-100, -100, 0, 0, "red", 1, 1, 5),
                          Particle(-2, 50, 0, 0, "red", 1, 1, 5)]
        game.light_rings = [LightRing(500, 500, "red", .2, 1, 10, 40),
                            LightRing(-5, 50, "red", .2, 1, 10, 40)]
        game._draw_effects(lambda x: x, lambda y: y, 100, 100)
        self.assertEqual(game.canvas.create_oval.call_count, 2)

    def test_grid_preserves_all_pairs_separation_and_random_order(self):
        for seed in range(40):
            rng = random.Random(seed)
            game = DarkRuins2D.__new__(DarkRuins2D)
            game.rng = random.Random(seed)
            game._blocked = lambda x, y, radius: x + radius > 400 or y - radius < -400
            game.enemies = [Enemy("test", rng.uniform(-400, 400), rng.uniform(-400, 400),
                                  100, 10, 40, rng.choice((12, 20, 60)), "red")
                            for _ in range(80)]
            # Exercise coincident centers, chained pushes, and large boss radii.
            for enemy in game.enemies[:10]:
                enemy.x = enemy.y = 0
            reference = copy.deepcopy(game)
            for _ in range(3):
                separate_reference(reference)
                game._separate_enemies()
                self.assertEqual([(e.x, e.y) for e in game.enemies],
                                 [(e.x, e.y) for e in reference.enemies], seed)
                self.assertEqual(game.rng.getstate(), reference.rng.getstate())

    def test_mixed_projectile_removals_preserve_order_and_list_identity(self):
        game = DarkRuins2D.__new__(DarkRuins2D)
        game.px = game.py = 0
        game._line_blocked = lambda x, y, xx, yy, radius: xx > 500
        hits = []
        game._damage_player = lambda damage, *args, **kwargs: hits.append(damage)
        survivor = Projectile(100, 100, 10, 0, 1, life=4)
        twin = copy.copy(survivor)
        expired = Projectile(200, 100, 0, 0, 2, life=.001)
        blocked = Projectile(600, 100, 0, 0, 3)
        hit = Projectile(0, 0, 0, 0, 4)
        game.projectiles = [survivor, expired, twin, blocked, hit]
        original_list = game.projectiles
        game._update_projectiles(1 / 60)
        self.assertIs(game.projectiles, original_list)
        self.assertEqual(len(game.projectiles), 2)
        self.assertIs(game.projectiles[0], survivor)
        self.assertIs(game.projectiles[1], twin)
        self.assertEqual(hits, [4])
        self.assertGreater(survivor.x, 100)

    def test_empty_and_single_enemy(self):
        game = DarkRuins2D.__new__(DarkRuins2D)
        for enemies in ([], [Enemy("test", 0, 0, 10, 1, 1, 20, "red")]):
            game.enemies = enemies
            game._separate_enemies()
            self.assertEqual(game.enemies, enemies)


if __name__ == "__main__":
    unittest.main()
