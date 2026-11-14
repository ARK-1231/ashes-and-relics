"""Perfect-dodge timing/reward and tactical companion command regressions."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D
from game_models import Companion, DODGE_DURATION, Enemy, Projectile
from game_options import GameOptions


class DodgeAndCommandTests(unittest.TestCase):
    def setUp(self):
        game = self.game = DarkRuins2D.__new__(DarkRuins2D)
        game.px = game.py = 0
        game.hp = game.max_hp = 100
        game.player_shield = 0
        game.ally_shield_cd = game.hurt_invincible = 0
        game.dodge_cd = 10
        game.dodge_time = DODGE_DURATION
        game.perfect_dodge_awarded = False
        game.perfect_dodge_boost = 0
        game.ally_command = "follow"
        game.door_open = True
        game.enemies = []
        game.projectiles = []
        game.ally_bolts = []
        game.allies = {"灰騎士レオン"}
        game.has_ally = True
        game.companions = {"灰騎士レオン": Companion("灰騎士レオン", 50, 0)}
        game._line_blocked = Mock(return_value=False)
        game._spawn_visual_effect = Mock()
        game._say = Mock()
        game._play_sound = Mock()
        game.game_over = False
        game.attack_cd = game.attack_flash = 0
        game.facing = (1, 0)
        game.options = GameOptions()
        game.keys = set()
        game.ui_mode = "playing"

    def enemy(self, x=60, y=0):
        return Enemy("test", x, y, 100, 10, 45, 20, "red")

    def test_melee_threat_requires_late_windup_range_and_clear_path(self):
        enemy = self.enemy()
        enemy.pending_attack = "melee"
        self.game.enemies = [enemy]
        for windup, distance, blocked, expected in (
            (.1, 60, False, True), (.2, 60, False, False),
            (.1, 100, False, False), (.1, 60, True, False),
        ):
            with self.subTest(windup=windup, distance=distance, blocked=blocked):
                enemy.windup, enemy.x = windup, distance
                self.game._line_blocked.return_value = blocked
                self.assertEqual(self.game._imminent_dodge_threat(), expected)

    def test_projectile_prediction_rejects_early_away_expired_and_wall_hidden(self):
        game = self.game
        for x, vx, life, blocked, expected in (
            (55, -300, 2, False, True), (200, -300, 2, False, False),
            (55, 300, 2, False, False), (55, -300, .001, False, False),
            (55, -300, 2, True, False),
        ):
            with self.subTest(x=x, vx=vx, life=life, blocked=blocked):
                game.projectiles = [Projectile(x, 0, vx, 0, 10, life=life)]
                game._line_blocked.return_value = blocked
                self.assertEqual(game._imminent_dodge_threat(), expected)

    def test_actual_early_dodge_hit_awards_once_without_damage(self):
        game = self.game
        game._damage_player(50, "first")
        game._damage_player(50, "second")
        self.assertEqual(game.hp, 100)
        self.assertEqual(game.dodge_cd, 7)
        self.assertEqual(game.perfect_dodge_boost, 3)
        game._spawn_visual_effect.assert_called_once()

    def test_starting_dodge_against_imminent_melee_grants_reward(self):
        game = self.game
        enemy = self.enemy()
        enemy.pending_attack, enemy.windup = "melee", .1
        game.enemies = [enemy]
        game.keys = {"space"}
        game.dodge_cd = game.dodge_time = 0
        game.canvas = SimpleNamespace(
            winfo_width=lambda: 1280, winfo_height=lambda: 720,
            winfo_pointerx=lambda: 300, winfo_pointery=lambda: 0,
            winfo_rootx=lambda: 0, winfo_rooty=lambda: 0,
        )
        game._move_player = Mock()
        game._update_player_movement(.02)
        self.assertEqual(game.dodge_cd, 7)
        self.assertEqual(game.perfect_dodge_boost, 3)
        game._damage_player(50, "same attack")
        self.assertEqual(game.dodge_cd, 7)
        game._spawn_visual_effect.assert_called_once()

    def test_late_dodge_or_existing_hurt_protection_has_no_reward(self):
        game = self.game
        for dodge, invincible in ((.05, 0), (DODGE_DURATION, .5)):
            game.dodge_time, game.hurt_invincible = dodge, invincible
            game._damage_player(50, "late")
            self.assertEqual(game.dodge_cd, 10)
            self.assertFalse(game.perfect_dodge_awarded)

    def test_melee_release_reports_dodged_hit_for_reward(self):
        game = self.game
        enemy = self.enemy()
        enemy.pending_attack = "melee"
        game._release_enemy_attack(enemy)
        self.assertEqual(game.hp, 100)
        self.assertEqual(game.dodge_cd, 7)

    def test_boost_applies_to_whole_swing_once_and_expires(self):
        game = self.game
        game.enemies = [self.enemy(), self.enemy(80)]
        game._aim_at_cursor = Mock()
        game._hit_enemy = Mock(side_effect=lambda enemy: self.assertEqual(game._swing_multiplier, 1.5))
        game._remove_dead = Mock()
        game.perfect_dodge_boost = 3
        game._attack()
        self.assertEqual(game._hit_enemy.call_count, 2)
        self.assertEqual(game.perfect_dodge_boost, 0)

    def test_boost_changes_real_damage_and_is_not_reused(self):
        game = self.game
        enemy = self.enemy()
        enemy.shield = 10
        game.enemies = [enemy]
        game.attack = 20
        game.skill = "none"
        game.stage_events = ()
        game._blocked = Mock(return_value=False)
        game._aim_at_cursor = Mock()
        game._start_screen_shake = Mock()
        game.perfect_dodge_boost = 3
        game._attack()
        self.assertEqual((enemy.hp, enemy.shield), (80, 0))
        game.attack_cd = 0
        game._attack()
        self.assertEqual(enemy.hp, 60)
        self.assertEqual(game._swing_multiplier, 1)
        game._update_player_movement = Mock()
        game.perfect_dodge_boost = 3
        game._update_player_input(3.1)
        self.assertEqual(game.perfect_dodge_boost, 0)

    def test_command_cycles_once_per_press_and_supports_remapping(self):
        game = self.game
        for expected in ("attack", "guard", "follow"):
            game._key_down(SimpleNamespace(keysym="c"))
            self.assertEqual(game.ally_command, expected)
            game._key_down(SimpleNamespace(keysym="c"))
            self.assertEqual(game.ally_command, expected)
            game._key_up(SimpleNamespace(keysym="c"))
        game.options.bindings = {"v": "c"}
        game._key_down(SimpleNamespace(keysym="v"))
        self.assertEqual(game.ally_command, "attack")

    def test_follow_attack_and_guard_have_different_destinations(self):
        game = self.game
        game.ally_candidate_name = ""
        game.enemies = [self.enemy(300)]
        game._update_one_companion = Mock()
        expected_x = {"follow": 52, "attack": 210, "guard": 32}
        for command, x in expected_x.items():
            game.ally_command = command
            game._update_ally(.02)
            self.assertAlmostEqual(game._update_one_companion.call_args.args[1], x)

    def test_attack_prioritizes_firing_guard_prioritizes_shield(self):
        game = self.game
        companion = game.companions["灰騎士レオン"]
        game.enemies = [self.enemy(90)]
        game.ally_command = "attack"
        game._perform_companion_action(companion)
        self.assertEqual(len(game.ally_bolts), 1)
        self.assertEqual(game.player_shield, 0)
        game.ally_command = "guard"
        game._perform_companion_action(companion)
        self.assertEqual(game.player_shield, 20)

    def test_guard_targets_threat_to_player_and_ignores_distant_enemy(self):
        game = self.game
        companion = Companion("星詠みノア", 100, 0)
        far, close = self.enemy(150), self.enemy(20)
        game.enemies = [far, close, self.enemy(300)]
        game.ally_command = "guard"
        game.player_shield = 20
        game._perform_companion_action(companion)
        self.assertIs(game.ally_bolts[-1].target, close)
        self.assertNotIn(game.enemies[-1], game._companion_targets(companion, 380))

    def test_closed_boss_room_and_walls_prevent_attack_orders(self):
        game = self.game
        enemy = self.enemy(90)
        enemy.boss = True
        game.enemies = [enemy]
        game.ally_command = "attack"
        game.door_open = False
        companion = game.companions["灰騎士レオン"]
        self.assertEqual(game._companion_targets(companion, 520), [])
        game.door_open = True
        game._line_blocked.return_value = True
        self.assertEqual(game._companion_targets(companion, 520), [])


if __name__ == "__main__":
    unittest.main()
