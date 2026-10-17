"""Projectile patterns used by the boss encounter."""

import math

from game_models import Enemy, Projectile


def create_fan(enemy: Enemy, target_x: float, target_y: float) -> list[Projectile]:
    base_angle = math.atan2(target_y - enemy.y, target_x - enemy.x)
    offsets = (-0.24, 0.0, 0.24)
    if enemy.boss_phase == 2:
        offsets = (-0.38, -0.19, 0.0, 0.19, 0.38)
    return [
        _projectile(
            enemy, base_angle + offset, 310.0, max(10, enemy.damage - 6),
            10, "fan", "#a34ee8", "#f0c4ff",
        )
        for offset in offsets
    ]


def create_ring(enemy: Enemy, target_x: float, target_y: float) -> list[Projectile]:
    shot_count = 16 if enemy.boss_phase == 2 else 12
    base_angle = math.atan2(target_y - enemy.y, target_x - enemy.x)
    speed = 270.0 if enemy.boss_phase == 2 else 235.0
    return [
        _projectile(
            enemy, base_angle + math.tau * shot / shot_count, speed,
            max(8, enemy.damage - 8), 9, "ring", "#e44f9e", "#ffd0e8",
            life=4.0,
        )
        for shot in range(shot_count)
    ]


def create_lance(enemy: Enemy, target_x: float, target_y: float) -> list[Projectile]:
    base_angle = math.atan2(target_y - enemy.y, target_x - enemy.x)
    offsets = (-0.06, 0.0, 0.06) if enemy.boss_phase == 2 else (-0.04, 0.04)
    speeds = (280.0, 370.0, 460.0) if enemy.boss_phase == 2 else (310.0, 410.0)
    return [
        _projectile(
            enemy, base_angle + offset, speed, max(12, enemy.damage - 3),
            8, "lance", "#39c7df", "#d5fbff",
        )
        for offset, speed in zip(offsets, speeds)
    ]


def create_spiral(enemy: Enemy, target_x: float, target_y: float) -> list[Projectile]:
    """Create a rotating spiral used by phase and dungeon-specific attack sets."""
    shot_count = 18
    base_angle = math.atan2(target_y - enemy.y, target_x - enemy.x)
    projectiles = []
    for shot in range(shot_count):
        projectile = _projectile(
            enemy,
            base_angle + math.tau * shot / shot_count,
            225.0,
            max(8, enemy.damage - 9),
            8,
            "spiral",
            "#ff8b38",
            "#ffe0a3",
            life=4.2,
        )
        projectile.turn_rate = 0.62
        projectiles.append(projectile)
    return projectiles


def create_wave(enemy: Enemy, target_x: float, target_y: float) -> list[Projectile]:
    """Create a wide, parallel wall of shots with two dodgeable gaps."""
    angle = math.atan2(target_y - enemy.y, target_x - enemy.x)
    dx, dy = math.cos(angle), math.sin(angle)
    perpendicular_x, perpendicular_y = -dy, dx
    projectiles = []
    for offset in (-150, -105, -60, 60, 105, 150):
        projectiles.append(Projectile(
            enemy.x + dx * (enemy.radius + 15) + perpendicular_x * offset,
            enemy.y + dy * (enemy.radius + 15) + perpendicular_y * offset,
            dx * 345.0,
            dy * 345.0,
            max(11, enemy.damage - 5),
            life=3.5,
            radius=11,
            boss_attack=True,
            style="wave",
            color="#f0ca48",
            outline="#fff6bd",
        ))
    return projectiles


def _projectile(
    enemy: Enemy,
    angle: float,
    speed: float,
    damage: int,
    radius: float,
    style: str,
    color: str,
    outline: str,
    life: float = 3.5,
) -> Projectile:
    dx, dy = math.cos(angle), math.sin(angle)
    return Projectile(
        enemy.x + dx * (enemy.radius + 12),
        enemy.y + dy * (enemy.radius + 12),
        dx * speed,
        dy * speed,
        damage,
        life=life,
        radius=radius,
        boss_attack=True,
        style=style,
        color=color,
        outline=outline,
    )
