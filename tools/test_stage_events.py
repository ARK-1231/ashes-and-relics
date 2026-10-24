"""Regression tests for cumulative stage-event behavior and combinations."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dark_ruins_rpg import DarkRuins2D  # noqa: E402
from game_models import Enemy  # noqa: E402


def enemy(name: str = "灰の兵士", *, boss: bool = False, hp: int = 40) -> Enemy:
    return Enemy(name, 100, 100, hp, 10, 90, 23, "#999", boss, max_hp=40)


class StageEventTests(unittest.TestCase):
    def test_floor_events_accumulate_without_duplicates(self) -> None:
        rng = random.Random(1234)
        events: list[str] = []
        for _ in range(3):
            events.append(DarkRuins2D._roll_stage_event(events, rng))
        self.assertEqual(len(events), 3)
        self.assertEqual(len(set(events)), 3)
        self.assertNotEqual(events[1], "calm")
        self.assertNotEqual(events[2], "calm")

    def test_dangerous_combinations_are_softened(self) -> None:
        self.assertEqual(
            DarkRuins2D._event_enemy_multipliers({"fortified", "ferocious"}),
            (1.25, 1.20, 1.0),
        )
        self.assertEqual(
            DarkRuins2D._event_enemy_multipliers({"fog", "haste"})[2],
            1.15,
        )

    def test_enemy_revives_only_once(self) -> None:
        game = DarkRuins2D.__new__(DarkRuins2D)
        target = enemy(hp=0)
        game.enemies = [target]
        game.stage_events = ("undying",)
        game.pending_revives = []
        game._spawn_visual_effect = Mock()
        game._say = Mock()
        game._remove_dead()
        self.assertTrue(target.revived_once)
        self.assertEqual(len(game.pending_revives), 1)
        game._update_enemy_revives(3.1)
        self.assertEqual(target.hp, 20)
        target.hp = 0
        game._remove_dead()
        self.assertEqual(game.pending_revives, [])

    def test_both_twin_bosses_are_required(self) -> None:
        game = DarkRuins2D.__new__(DarkRuins2D)
        first = enemy("王国の守護者", boss=True, hp=0)
        second = enemy("王国の守護者", boss=True, hp=40)
        game.enemies = [first, second]
        game.stage_events = ("twin_boss",)
        game.pending_revives = []
        game.boss_gate_locked = True
        game.dungeon_number = 3
        game.truth = 0
        game.retry_used = False
        game.game_over = False
        game._spawn_visual_effect = Mock()
        game._say = Mock()
        game._remove_dead()
        self.assertFalse(game.game_over)
        second.hp = 0
        game._remove_dead()
        self.assertTrue(game.game_over)

    def test_summoned_enemy_cap_is_enforced(self) -> None:
        game = DarkRuins2D.__new__(DarkRuins2D)
        boss = enemy("王国の守護者", boss=True)
        game.enemies = [boss] + [enemy() for _ in range(10)]
        for summoned in game.enemies[1:]:
            summoned.summoned = True
        game.stage_events = ("boss_command",)
        game.dungeon_number = 1
        game.rng = random.Random(1)
        game._blocked = Mock(return_value=False)
        game._spawn_visual_effect = Mock()
        game._say = Mock()
        game._summon_boss_reinforcements()
        self.assertEqual(len(game.enemies), 11)

    def test_blood_price_never_reduces_hp_below_one(self) -> None:
        game = DarkRuins2D.__new__(DarkRuins2D)
        game.game_over = False
        game.attack_cd = 0.0
        game.attack_flash = 0.0
        game.hp = 1
        game.stage_events = ("blood_price",)
        game.facing = (1.0, 0.0)
        game.enemies = []
        game._aim_at_cursor = Mock()
        game._play_sound = Mock()
        game._say = Mock()
        game._attack()
        self.assertEqual(game.hp, 1)


if __name__ == "__main__":
    unittest.main()
