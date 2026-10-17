"""Shared game constants and lightweight state models."""

from dataclasses import dataclass, field


# Window and world geometry
WIDTH, HEIGHT = 1280, 720
STAGE_SCALE = 1.5
WORLD_SIZE = int(1920 * STAGE_SCALE)

# Player movement and animation tuning
PLAYER_SPEED = 260.0
PLAYER_RADIUS = 20.0
PLAYER_ATTACK_COOLDOWN = 0.65
PLAYER_ATTACK_ANIMATION_DURATION = 0.20
PLAYER_IDLE_FPS = 3.0
PLAYER_WALK_FPS = 7.0
ENEMY_IDLE_FPS = 2.5
ENEMY_WALK_FPS = 6.0

# Dodge tuning
DODGE_SPEED = 600.0
DODGE_DURATION = 0.26
DODGE_COOLDOWN = 10.0


def stage(value: float) -> float:
    """Convert an original map coordinate to the enlarged stage."""
    return value * STAGE_SCALE


@dataclass
class Relic:
    """A collectible relic placed in the dungeon."""
    key: str
    name: str
    x: float
    y: float
    color: str
    truth: int
    collected: bool = False


@dataclass
class Enemy:
    """Runtime state shared by regular enemies and bosses."""
    name: str
    x: float
    y: float
    hp: int
    damage: int
    speed: float
    radius: float
    color: str
    boss: bool = False
    cooldown: float = 0.0
    ranged: bool = False
    windup: float = 0.0
    windup_max: float = 0.0
    pending_attack: str = ""
    aim_x: float = 0.0
    aim_y: float = 0.0
    boss_phase: int = 1
    last_boss_attack: str = ""
    moving: bool = False
    walk_time: float = 0.0
    attack_pose: str = ""
    attack_pose_time: float = 0.0
    spiral_shots_remaining: int = 0
    max_hp: int = 0
    shield: int = 0
    max_shield: int = 0

    def __post_init__(self) -> None:
        if self.max_hp <= 0:
            self.max_hp = self.hp
        if self.max_shield <= 0 and self.shield > 0:
            self.max_shield = self.shield


@dataclass
class AllyBolt:
    """A projectile fired by a companion toward a live enemy target."""
    x: float
    y: float
    target: Enemy
    damage: int
    speed: float = 420.0
    life: float = 1.5


@dataclass
class Companion:
    """A recruited ally's movement, animation, and ability state."""
    name: str
    x: float
    y: float
    cooldown: float = 0.0
    cooldown_max: float = 0.0
    path_timer: float = 0.0
    path: list[tuple[float, float]] = field(default_factory=list)
    facing: str = "down"
    facing_candidate: str = ""
    facing_candidate_time: float = 0.0
    moving: bool = False
    walk_time: float = 0.0
    pose_time: float = 0.0
    pose: str = "attack"


@dataclass
class Projectile:
    """A hostile projectile and its movement/effect parameters."""
    x: float
    y: float
    vx: float
    vy: float
    damage: int
    life: float = 3.0
    radius: float = 8.0
    boss_attack: bool = False
    style: str = "normal"
    color: str = "#9d55d6"
    outline: str = "#efc8ff"
    turn_rate: float = 0.0


@dataclass
class Particle:
    """One short-lived visual-effect particle."""
    x: float
    y: float
    vx: float
    vy: float
    color: str
    life: float
    max_life: float
    size: float


@dataclass
class LightRing:
    """An expanding ring used by combat visual effects."""
    x: float
    y: float
    color: str
    life: float
    max_life: float
    start_radius: float
    end_radius: float
