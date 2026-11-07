"""Regressions for enemy roles and exploration memory."""
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D
from game_models import Enemy
from exploration import Exploration


class NewFeaturesTests(unittest.TestCase):
    def test_merged_mask_preserves_unknown_cells_and_caches_geometry(self):
        from exploration import CELL_SIZE
        memory = Exploration()
        size = CELL_SIZE * 5 - 10
        memory.discovered.update({(1, 1), (2, 1), (2, 2), (4, 4)})
        rectangles = memory.unknown_rectangles(size)
        for x in range(5):
            for y in range(5):
                px = min(size-1, x*CELL_SIZE+CELL_SIZE/2)
                py = min(size-1, y*CELL_SIZE+CELL_SIZE/2)
                covered = sum(x1 <= px < x2 and y1 <= py < y2
                              for x1, y1, x2, y2 in rectangles)
                self.assertEqual(covered, int((x, y) not in memory.discovered))
        self.assertIs(rectangles, memory.unknown_rectangles(size))
        memory.discovered.add((0, 0))
        self.assertIsNot(rectangles, memory.unknown_rectangles(size))

    def game(self, keys=()):
        game = DarkRuins2D.__new__(DarkRuins2D)
        game.relics = [SimpleNamespace(key=key, collected=True) for key in keys]
        game.px = game.py = 0
        game.hp, game.max_hp, game.attack, game.skill = 50, 100, 18, "none"
        game.dodge_time = 0
        game._blocked = Mock(return_value=False)
        game._line_blocked = Mock(return_value=False)
        for name in ("_spawn_visual_effect", "_start_screen_shake", "_play_sound", "_say", "_damage_player"):
            setattr(game, name, Mock())
        return game

    def enemy(self, behavior="normal"):
        return Enemy("test", 60, 0, 100, 10, 100, 20, "red", behavior=behavior)

    def test_shield_reduces_front_damage_but_allows_flanking(self):
        game = self.game()
        front = self.enemy("shield")
        front.guard_angle = math.pi
        game._hit_enemy(front)
        back = self.enemy("shield")
        back.guard_angle = 0
        game._hit_enemy(back)
        self.assertEqual(front.hp, 94)
        self.assertEqual(back.hp, 82)

    def test_healer_cannot_heal_boss_dead_or_through_wall(self):
        game = self.game()
        healer, wounded, dead, boss = (self.enemy(role) for role in ("healer", "normal", "normal", "normal"))
        wounded.hp, dead.hp, boss.hp, boss.boss = 50, 0, 30, True
        game.enemies = [healer, wounded, dead, boss]
        game._line_blocked.return_value = True
        game._update_enemy_ability(healer, 100, 0.016)
        self.assertEqual(wounded.hp, 50)
        game._line_blocked.return_value = False
        game._update_enemy_ability(healer, 100, 0.016)
        self.assertEqual(wounded.hp, 65)
        self.assertEqual((dead.hp, boss.hp), (0, 30))
        self.assertEqual(healer.ability_cd, 5)

    def test_charge_stops_at_wall_without_tunneling(self):
        game = self.game()
        enemy = self.enemy("charger")
        enemy.x, enemy.charge_time, enemy.charge_dx = 100, 0.5, 1
        game._blocked.side_effect = lambda x, y, r: x >= 115
        game._update_enemy_ability(enemy, 100, 0.05)
        self.assertLess(enemy.x, 115)
        self.assertEqual(enemy.charge_time, 0)
        game._damage_player.assert_not_called()

    def test_map_remembers_previous_area_and_hides_occluded_cells(self):
        memory = Exploration()
        memory.update(144, 144, 2000, lambda *args: False)
        start = memory.cell(144, 144)
        memory.update(1400, 1400, 2000, lambda *args: False)
        self.assertIn(start, memory.discovered)
        self.assertNotIn(start, memory.visible)
        blocked = Exploration()
        blocked.update(144, 144, 2000, lambda *args: True)
        self.assertEqual(blocked.discovered, {start})

    def test_gate_change_reveals_area_without_player_moving(self):
        memory = Exploration()
        memory.update(144, 144, 2000, lambda *args: True, False)
        before = len(memory.discovered)
        memory.update(144, 144, 2000, lambda *args: False, True)
        self.assertGreater(len(memory.discovered), before)


if __name__ == "__main__":
    unittest.main()
