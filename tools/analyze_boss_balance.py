"""Inspect current boss/shield numbers through the actual combat methods.

These scripted scenarios assume every player attack hits, with no movement,
misses, hit-stop delay, or companion attack damage. They are not playtest results.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D
import dark_ruins_rpg as combat
from game_models import Companion, PLAYER_ATTACK_COOLDOWN
from boss_attacks import create_fan, create_ring, create_lance, create_wave, create_spiral


def scenario(tier, skill):
    game = DarkRuins2D.__new__(DarkRuins2D)
    game.dungeon_number = tier
    game.px = game.py = 0
    game.relics = []
    game._random_open_position = lambda *args, **kwargs: (100, 100)
    boss = next(enemy for enemy in game._make_enemies() if enemy.boss)
    boss.x, boss.y, boss.cooldown = 100, 0, 100
    game.enemies = [boss]
    game.door_open = True
    game._blocked = lambda *args: True
    game._line_blocked = lambda *args: False
    game._separate_enemies = lambda: None
    game._say = game._play_sound = game._spawn_visual_effect = game._start_screen_shake = lambda *args, **kw: None
    game._knockback_player = lambda *args: None
    game.attack = (30, 46, 70)[tier - 1]
    game.armor_bonus = (0, 5, 13)[tier - 1]
    game.hp = game.max_hp = (100, 130, 180)[tier - 1]
    game.skill = skill
    game.allies = set(("ミラ", "灰騎士レオン", "星詠みノア")[:tier])
    game.has_ally = True
    game.player_shield = 0
    game.ally_shield_cd = 0
    game.dodge_time = game.hurt_invincible = game.hit_stop_time = 0
    game.game_over = False
    game.retry_used = False
    game.companions = {name: Companion(name, 0, 0) for name in game.allies}
    game.ally_bolts = []
    return game, boss


def boss_hits(tier, skill):
    game, boss = scenario(tier, skill)
    hp, shield = boss.hp, boss.shield
    phase_hits = [0, 0]
    while boss.hp > 0:
        phase_hits[boss.boss_phase - 1] += 1
        before = boss.hp + boss.shield
        game._hit_enemy(boss)
        damage = before - boss.hp - boss.shield
        if sum(phase_hits) == 1:
            per_hit = damage
        if boss.hp > 0:
            game._update_enemies(0)
    return {"tier": tier, "skill": skill, "hp_per_phase": hp, "shield_per_phase": shield,
            "approx_total_durability": hp * 1.5 + shield * 2,
            "player_hit": per_hit, "phase_hits": phase_hits,
            "ideal_seconds": round((sum(phase_hits) - 1) * PLAYER_ATTACK_COOLDOWN, 2)}


def damage_table(tier, skill):
    game, boss = scenario(tier, skill)
    patterns = {"melee": boss.damage,
                **{key: maker(boss, 0, 0)[0].damage for key, maker in
                   (("fan", create_fan), ("ring", create_ring), ("lance", create_lance),
                    ("wave", create_wave), ("spiral", create_spiral))}}
    result = {}
    for key, damage in patterns.items():
        game.hp, game.hurt_invincible, game.player_shield = game.max_hp, 0, 0
        game._damage_player(damage, key)
        result[key] = game.max_hp - game.hp
    return {"tier": tier, "skill": skill, "capacity": game._player_shield_capacity(),
            "best_case_shield_per_second": game._player_shield_capacity() / combat.ALLY_SHIELD_COOLDOWN,
            "hp_damage_without_shield": result}


def sustain(tier, skill, seconds=60, shield_enabled=True, cooldown_on_break=True):
    game, boss = scenario(tier, skill)
    # A training target avoids ending the test; companion attacks are excluded.
    game.enemies = []
    if not shield_enabled:
        game.ally_shield_cd = float("inf")
    boss.hp = boss.max_hp = 10**9
    boss.shield = 0
    hits = grants = 0
    next_attack = next_melee = 0
    step = 1 / 120
    for frame in range(int(seconds / step)):
        now = frame * step
        game.hurt_invincible = max(0, game.hurt_invincible - step)
        game.ally_shield_cd = max(0, game.ally_shield_cd - step)
        for name in sorted(game.companions):
            companion = game.companions[name]
            companion.cooldown = max(0, companion.cooldown - step)
            before = game.player_shield
            if companion.cooldown == 0:
                game._perform_companion_action(companion)
            if game.player_shield > before:
                grants += 1
                if not cooldown_on_break:
                    game.ally_shield_cd = combat.ALLY_SHIELD_COOLDOWN
        if now + 1e-8 >= next_attack:
            game._hit_enemy(boss)
            next_attack += PLAYER_ATTACK_COOLDOWN
        if now + 1e-8 >= next_melee:
            shield_before, cd_before = game.player_shield, game.ally_shield_cd
            game._damage_player(boss.damage, "scripted melee")
            if not cooldown_on_break and shield_before > 0 and game.player_shield == 0:
                game.ally_shield_cd = cd_before
            next_melee += 1.35  # Actual melee windup .55 + cooldown .8.
            hits += 1
        if game.hp == 0:
            break
    return {"tier": tier, "skill": skill, "shield_enabled": shield_enabled,
            "cooldown_starts": "break" if cooldown_on_break else "grant",
            "survived_seconds": round(now + step, 2),
            "melee_hits": hits, "shield_grants": grants, "hp": game.hp, "shield": game.player_shield}


def main():
    offense = ("dark", "gauntlet", "ember")
    defense = ("lantern", "wing", "ward")
    builds = ((1, "dark"), (2, "wing"), (2, "chalice"), (3, "ward"), (3, "dew"))
    comparison = [sustain(t, skill, shield_enabled=enabled)
                  for t, skill in builds for enabled in (True, False)]
    original = (combat.ALLY_SHIELD_AMOUNT, combat.ALLY_SHIELD_PER_EXTRA_ALLY, combat.ALLY_SHIELD_COOLDOWN)
    try:
        # Compare the previous settings in this process only.
        combat.ALLY_SHIELD_AMOUNT = 20
        combat.ALLY_SHIELD_PER_EXTRA_ALLY = 15
        combat.ALLY_SHIELD_COOLDOWN = 8
        previous = [sustain(t, skill, cooldown_on_break=False) for t, skill in builds]
    finally:
        (combat.ALLY_SHIELD_AMOUNT, combat.ALLY_SHIELD_PER_EXTRA_ALLY,
         combat.ALLY_SHIELD_COOLDOWN) = original
    print(json.dumps({"assumptions": __doc__,
                      "boss_hits": [boss_hits(t, skills[t-1]) for skills in (offense, defense) for t in (1, 2, 3)],
                      "incoming_damage": [damage_table(t, skills[t-1]) for skills in (offense, defense) for t in (1, 2, 3)],
                      "standing_melee_sustain": comparison,
                      "before_adjustment_20_35_50_cooldown8": previous}, indent=2))


if __name__ == "__main__":
    main()
