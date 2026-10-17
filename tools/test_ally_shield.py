"""Companion shield granting, absorption, and cooldown regressions."""
import unittest
from unittest.mock import Mock

import test_projectile_invincibility
from game_models import Companion


class AllyShieldTests(unittest.TestCase):
    def setUp(self):
        self.game = test_projectile_invincibility.ProjectileInvincibilityTests().make_game("lance")
        self.game.max_hp = 100
        self.game.allies = {"ミラ"}
        self.game.ally_shield_cd = 0.0
        self.game.enemies = []
        self.game._spawn_visual_effect = Mock()

    def test_grant_is_shared_and_does_not_stack(self):
        game = self.game
        mira = Companion("ミラ", 0, 0)
        game._perform_companion_action(mira)
        self.assertEqual(game.player_shield, 20)
        self.assertEqual(game.ally_shield_cd, 8)
        game._perform_companion_action(Companion("灰騎士レオン", 0, 0))
        self.assertEqual(game.player_shield, 20)
        game.player_shield = 0
        game._perform_companion_action(Companion("星詠みノア", 0, 0))
        self.assertEqual(game.player_shield, 0)
        game.ally_shield_cd = 0
        game._perform_companion_action(mira)
        self.assertEqual(game.player_shield, 20)

    def test_capacity_and_granted_shield_scale_with_recruited_allies(self):
        game = self.game
        names = ("ミラ", "灰騎士レオン", "星詠みノア")
        game.allies.clear()
        self.assertEqual(game._player_shield_capacity(), 0)
        for name, expected in zip(names, (20, 35, 50)):
            game.allies.add(name)
            game.player_shield = 0
            game.ally_shield_cd = 0
            game._perform_companion_action(Companion(name, 0, 0))
            self.assertEqual(game.player_shield, expected)
            self.assertEqual(game._player_shield_capacity(), expected)

    def test_damage_consumes_shield_before_hp(self):
        game = self.game
        game.player_shield = 20
        game._damage_player(10, "test", invincibility_duration=0)
        self.assertEqual((game.player_shield, game.hp), (10, 100))
        game._damage_player(20, "test", invincibility_duration=0)
        self.assertEqual((game.player_shield, game.hp), (0, 90))

    def test_healing_has_priority(self):
        game = self.game
        game.hp = 40
        game._perform_companion_action(Companion("ミラ", 0, 0))
        self.assertEqual(game.hp, 54)
        self.assertEqual(game.player_shield, 0)

    def test_distant_or_obstructed_companion_cannot_grant(self):
        game = self.game
        game._perform_companion_action(Companion("ミラ", 300, 0))
        self.assertEqual(game.player_shield, 0)
        game._line_blocked.return_value = True
        game._perform_companion_action(Companion("ミラ", 0, 0))
        self.assertEqual(game.player_shield, 0)


if __name__ == "__main__":
    unittest.main()
