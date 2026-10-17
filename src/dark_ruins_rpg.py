from __future__ import annotations
import math
import random
import sys
import time
import tkinter as tk
from pathlib import Path
from ally_navigation import find_path
from boss_attacks import create_fan, create_lance, create_ring, create_spiral, create_wave
from game_models import (
    DODGE_DURATION,
    DODGE_COOLDOWN,
    DODGE_SPEED,
    HEIGHT,
    ENEMY_IDLE_FPS,
    ENEMY_WALK_FPS,
    PLAYER_ATTACK_ANIMATION_DURATION,
    PLAYER_ATTACK_COOLDOWN,
    PLAYER_IDLE_FPS,
    PLAYER_RADIUS,
    PLAYER_SPEED,
    PLAYER_WALK_FPS,
    WIDTH,
    WORLD_SIZE,
    AllyBolt,
    Companion,
    Enemy,
    LightRing,
    Particle,
    Projectile,
    Relic,
    stage,
)


ALLY_STYLES = {
    "ミラ": ("#e7b94c", "ミラ"),
    "灰騎士レオン": ("#9aa7bd", "レオン"),
    "星詠みノア": ("#9d7de2", "ノア"),
}

# Companion configuration lives here so loading, movement, and combat code do
# not each maintain their own copy of character names and tuning values.
ALLY_DIRECTIONS = ("down", "up", "left", "right")
ALLY_ANIMATION_FRAME_COUNTS = {
    **{f"idle_{direction}": 1 for direction in ALLY_DIRECTIONS},
    **{f"walk_{direction}": 2 for direction in ALLY_DIRECTIONS},
    "attack": 2,
    "heal": 1,
}
ALLY_IMAGE_ZOOM = 7
ALLY_IMAGE_SUBSAMPLE = 8
ALLY_FOLLOW_DISTANCE = 52
ALLY_FACING_CONFIRM_SECONDS = 0.12

RELIC_KEYS = (
    "blade", "lantern", "heart", "chalice", "gauntlet",
    "wing", "ember", "ward", "dew",
)
BOSS_PROJECTILE_STYLES = ("fan", "ring", "lance", "spiral", "wave")
BOSS_PROJECTILE_DIRECTIONS = 16
PLAYER_ATTACK_RADIUS = 110
ALLY_SHIELD_AMOUNT = 20
ALLY_SHIELD_PER_EXTRA_ALLY = 15
ALLY_SHIELD_COOLDOWN = 8.0
PLAYER_ATTACK_HALF_ANGLE = math.pi / 3


class FrameCanvas(tk.Canvas):
    """Reuse canvas items in draw order instead of rebuilding them every frame."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._frame_items = []
        self._frame_cursor = 0

    def begin_frame(self):
        self._frame_cursor = 0

    def _create(self, itemType, args, kw):
        index = self._frame_cursor
        self._frame_cursor += 1
        if index < len(self._frame_items):
            kind, item, old_args, old_kw = self._frame_items[index]
            if kind == itemType:
                if args != old_args:
                    self.coords(item, *args)
                if kw != old_kw:
                    # Recreate if an option disappeared, restoring Tk defaults.
                    if old_kw.keys() - kw.keys():
                        self.delete(item)
                    else:
                        self.itemconfigure(item, **kw)
                        self._frame_items[index] = (kind, item, args, dict(kw))
                        return item
                else:
                    self._frame_items[index] = (kind, item, args, dict(kw))
                    return item
            else:
                self.delete(item)
        item = super()._create(itemType, args, kw)
        if index < len(self._frame_items):
            self._frame_items[index] = (itemType, item, args, dict(kw))
            if index:
                self.tag_raise(item, self._frame_items[index - 1][1])
            else:
                self.tag_lower(item)
        else:
            self._frame_items.append((itemType, item, args, dict(kw)))
        return item

    def end_frame(self):
        for _, item, _, _ in self._frame_items[self._frame_cursor:]:
            self.delete(item)
        del self._frame_items[self._frame_cursor:]


class DarkRuins2D:
    """Coordinate the game state, update loop, input, and rendering."""

    def __init__(self, hidden: bool = False) -> None:
        self.root = tk.Tk()
        if hidden:
            self.root.withdraw()
        self.root.title("灰の王国と記憶の遺物 - 2D")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.minsize(900, 560)
        self.canvas = FrameCanvas(self.root, bg="#303541", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.environment_textures = self._load_environment_textures()
        self.landmark_sprites = self._load_landmark_sprites()
        self.floor_texture_canvases: dict[tuple[int, int], tk.PhotoImage] = {}
        self.wall_texture_sizes: dict[tuple[int, int], tk.PhotoImage] = {}
        self.player_sprites = self._load_player_sprites()
        self.enemy_sprites = self._load_enemy_sprites()
        self.ally_sprites = self._load_ally_sprites()
        self.ally_animations = self._load_ally_animations()
        self.relic_sprites = self._load_relic_sprites()
        self.boss_sprite = self._load_boss_sprite()
        self.boss_attack_sprites = self._load_boss_attack_sprites()
        self.boss_walk_sprites = self._load_boss_walk_sprites()
        self.boss_projectile_sprites = self._load_boss_projectile_sprites()

        self.retry_used = False
        self._reset_game()
        self.ui_mode = "title"
        self.menu_index = 0
        self.menu_return_mode = "title"

        self.root.bind("<KeyPress>", self._key_down)
        self.root.bind("<KeyRelease>", self._key_up)
        self.root.bind("<FocusOut>", lambda event: self.keys.clear())
        self.canvas.bind("<Motion>", self._aim_with_mouse)
        self.canvas.bind("<Button-1>", self._mouse_attack)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.last_time = time.perf_counter()
        self.root.after(16, self._loop)

    def _load_landmark_sprites(self) -> dict[str, tk.PhotoImage]:
        """Load small transparent landmarks once; retain shape fallbacks."""
        root = Path(__file__).resolve().parent.parent / "assets" / "sprites" / "landmarks"
        sprites = {}
        for name in ("shrine", "stairs", "exit"):
            try:
                sprites[name] = tk.PhotoImage(master=self.root, file=str(root / f"{name}.png"))
            except (tk.TclError, OSError) as exc:
                print(f"Could not load landmark {name}: {exc}", file=sys.stderr)
        return sprites

    def _load_environment_textures(self) -> dict[str, tk.PhotoImage]:
        """Load optimized floor and wall tiles, with colored-shape fallbacks."""
        root = Path(__file__).resolve().parent.parent / "assets" / "environment"
        try:
            return {
                "floor": tk.PhotoImage(file=str(root / "floor_tile.png")),
                "wall": tk.PhotoImage(file=str(root / "wall_tile.png")),
            }
        except (tk.TclError, OSError):
            return {}

    @staticmethod
    def _build_tiled_image(
        source: tk.PhotoImage, width: int, height: int, tile_size: int,
    ) -> tk.PhotoImage:
        """Compose many tiles once so each surface needs one Canvas item per frame."""
        result = tk.PhotoImage(width=width, height=height)
        for y in range(0, height, tile_size):
            for x in range(0, width, tile_size):
                result.tk.call(result, "copy", source, "-to", x, y)
        return result

    def _floor_texture_for_view(self, width: int, height: int) -> tk.PhotoImage:
        padded_width = math.ceil(width / 96) * 96 + 96
        padded_height = math.ceil(height / 96) * 96 + 96
        key = (padded_width, padded_height)
        if key not in self.floor_texture_canvases:
            self.floor_texture_canvases[key] = self._build_tiled_image(
                self.environment_textures["floor"], padded_width, padded_height, 96,
            )
        return self.floor_texture_canvases[key]

    def _wall_texture_for_size(self, width: int, height: int) -> tk.PhotoImage:
        """Return one cached, exactly sized texture for a complete wall rectangle."""
        key = (width, height)
        if key not in self.wall_texture_sizes:
            self.wall_texture_sizes[key] = self._build_tiled_image(
                self.environment_textures["wall"], width, height, 32,
            )
        return self.wall_texture_sizes[key]

    def _load_player_sprites(self) -> dict[str, list[tk.PhotoImage]]:
        """Load normalized 96 px PNG frames, with a shape fallback."""
        frames_path = (
            Path(__file__).resolve().parent.parent
            / "assets" / "sprites" / "player"
            / "frames_v5"
        )
        if not frames_path.exists():
            return {}
        try:
            frames: dict[str, list[tk.PhotoImage]] = {}
            for direction in ("up", "down", "left", "right"):
                for animation in ("idle", "walk", "attack"):
                    key = f"{animation}_{direction}"
                    frames[key] = [
                        tk.PhotoImage(
                            file=str(frames_path / direction / animation / f"{index:02}.png")
                        )
                        for index in range(1, 5)
                    ]
            return frames
        except (tk.TclError, OSError) as exc:
            print(f"Could not load player animation: {exc}", file=sys.stderr)
            return {}

    def _player_sprite(self) -> tk.PhotoImage | None:
        if not self.player_sprites:
            return None
        fx, fy = self.facing
        if abs(fx) > abs(fy):
            direction = "right" if fx >= 0 else "left"
        else:
            direction = "down" if fy >= 0 else "up"
        moving = any(key in self.keys for key in ("w", "a", "s", "d", "up", "down", "left", "right"))
        if self.attack_flash > 0:
            animation = "attack"
            progress = 1.0 - self.attack_flash / PLAYER_ATTACK_ANIMATION_DURATION
            frame_index = min(3, max(0, int(progress * 4)))
        elif moving:
            animation = "walk"
            frame_index = int(time.perf_counter() * PLAYER_WALK_FPS) % 4
        else:
            animation = "idle"
            frame_index = int(time.perf_counter() * PLAYER_IDLE_FPS) % 4
        return self.player_sprites[f"{animation}_{direction}"][frame_index]

    def _load_ally_sprites(self) -> dict[str, tk.PhotoImage]:
        """Keep transparent companion sprites alive for the Canvas."""
        root = Path(__file__).resolve().parent.parent / "assets" / "sprites" / "allies"
        sprites = {}
        for name, filename in (("ミラ", "mira"), ("灰騎士レオン", "leon"), ("星詠みノア", "noa")):
            try:
                image = tk.PhotoImage(master=self.root, file=str(root / f"{filename}_v2.png"))
                sprites[name] = self._scale_ally_image(image)
            except (tk.TclError, OSError) as exc:
                print(f"Could not load companion {name}: {exc}", file=sys.stderr)
        return sprites

    def _load_ally_animations(self) -> dict:
        root = Path(__file__).resolve().parent.parent / "assets/sprites/allies/frames_v2"
        if not root.exists():
            return {}
        result = {}
        for name, folder in (("ミラ", "mira"), ("灰騎士レオン", "leon"), ("星詠みノア", "noa")):
            try:
                result[name] = {
                    key: [self._scale_ally_image(tk.PhotoImage(
                              master=self.root, file=str(root / folder / key / f"{i:02}.png")
                          ))
                          for i in range(count)]
                    for key, count in ALLY_ANIMATION_FRAME_COUNTS.items()
                }
            except (tk.TclError, OSError) as exc:
                print(f"Could not load companion animation {name}: {exc}", file=sys.stderr)
        return result

    @staticmethod
    def _scale_ally_image(image: tk.PhotoImage) -> tk.PhotoImage:
        """Render companions just below the player's apparent sprite size."""
        return image.zoom(ALLY_IMAGE_ZOOM, ALLY_IMAGE_ZOOM).subsample(
            ALLY_IMAGE_SUBSAMPLE, ALLY_IMAGE_SUBSAMPLE,
        )

    def _ally_sprite(self, name: str, companion: Companion | None = None):
        frames = self.ally_animations.get(name)
        if not frames:
            return self.ally_sprites.get(name)
        if companion is None:
            return frames["idle_down"][0]
        if companion.pose_time > 0:
            poses = frames[companion.pose]
            return poses[min(len(poses) - 1, int((0.45 - companion.pose_time) * len(poses) / 0.45))]
        state = "walk" if companion.moving else "idle"
        poses = frames[f"{state}_{companion.facing}"]
        return poses[int(companion.walk_time * 7) % len(poses)]

    def _draw_ally(self, name: str, x: float, y: float, companion: Companion | None = None) -> None:
        color, label = ALLY_STYLES.get(name, ("#e7b94c", name))
        sprite = self._ally_sprite(name, companion)
        self.canvas.create_polygon(
            x - 25, y + 12, x, y + 2, x + 25, y + 12, x, y + 22,
            fill="#30291b", outline="#f2ca70", width=2,
        )
        if sprite is None:
            self._draw_actor(x, y, 18, color, "")
        else:
            self.canvas.create_image(x, y + 12, image=sprite, anchor="s")
        display_label = label if companion is not None else f"加入前 · {label}"
        self._draw_role_label(x, y - 91, display_label, "#f2ca70")

    def _draw_role_label(self, x: float, y: float, text: str, color: str) -> None:
        """Draw a readable role badge without creating image assets."""
        half_width = max(32, len(text) * 7 + 8)
        self.canvas.create_rectangle(
            x - half_width, y - 11, x + half_width, y + 11,
            fill="#101722", outline=color, width=1,
        )
        self.canvas.create_text(
            x, y, text=text, fill=color, font=("Yu Gothic UI", 10, "bold"),
        )

    def _load_relic_sprites(self) -> dict[str, tk.PhotoImage]:
        """Load compact field/HUD sprites for every collectible relic."""
        root = Path(__file__).resolve().parent.parent / "assets" / "sprites" / "relics"
        sprites = {}
        for key in RELIC_KEYS:
            try:
                image = tk.PhotoImage(master=self.root, file=str(root / f"{key}.png"))
                sprites[key] = image.subsample(2, 2)
            except (tk.TclError, OSError) as exc:
                print(f"Could not load relic {key}: {exc}", file=sys.stderr)
        return sprites

    def _draw_relic(self, relic: Relic, x: float, y: float) -> None:
        """Draw a collectible with a ground marker and its localized name."""
        sprite = self.relic_sprites.get(relic.key)
        if sprite is None:
            self._draw_marker(x, y, 18, relic.color, relic.name)
            return
        self.canvas.create_oval(
            x - 14, y + 7, x + 14, y + 15,
            fill="#171923", outline=relic.color,
        )
        self.canvas.create_image(x, y + 12, image=sprite, anchor="s")
        self.canvas.create_text(
            x, y + 29, text=relic.name, fill="#e7dfca",
            font=("Yu Gothic UI", 9),
        )

    def _load_boss_sprite(self) -> tk.PhotoImage | None:
        """Load and scale the guardian once, keeping frame rendering inexpensive."""
        path = Path(__file__).resolve().parent.parent / "assets" / "sprites" / "boss" / "kingdom_guardian_spellblade.png"
        try:
            return tk.PhotoImage(master=self.root, file=str(path)).subsample(8, 8)
        except (tk.TclError, OSError) as exc:
            print(f"Could not load boss sprite: {exc}", file=sys.stderr)
            return None

    def _load_boss_attack_sprites(self) -> dict[str, tk.PhotoImage]:
        root = Path(__file__).resolve().parent.parent / "assets" / "sprites" / "boss" / "attacks"
        sprites = {}
        for attack in ("melee", "boss_fan", "boss_ring", "boss_lance", "boss_spiral", "boss_wave"):
            try:
                sprites[attack] = tk.PhotoImage(master=self.root, file=str(root / f"{attack}.png"))
            except (tk.TclError, OSError) as exc:
                print(f"Could not load boss attack {attack}: {exc}", file=sys.stderr)
        return sprites

    def _load_boss_walk_sprites(self) -> list[tk.PhotoImage]:
        root = Path(__file__).resolve().parent.parent / "assets" / "sprites" / "boss" / "walk"
        try:
            return [tk.PhotoImage(master=self.root, file=str(root / f"{i:02}.png")) for i in range(1, 5)]
        except (tk.TclError, OSError) as exc:
            print(f"Could not load boss walk cycle: {exc}", file=sys.stderr)
            return []

    def _load_boss_projectile_sprites(self) -> dict[str, list[tk.PhotoImage]]:
        """Load pre-rotated boss projectiles so drawing stays inexpensive."""
        root = Path(__file__).resolve().parent.parent / "assets" / "sprites" / "boss_projectiles"
        sprites = {}
        for style in BOSS_PROJECTILE_STYLES:
            try:
                sprites[style] = [
                    tk.PhotoImage(master=self.root, file=str(root / style / f"{index:02}.png"))
                    for index in range(BOSS_PROJECTILE_DIRECTIONS)
                ]
            except (tk.TclError, OSError) as exc:
                print(f"Could not load boss projectile {style}: {exc}", file=sys.stderr)
        return sprites

    def _boss_projectile_sprite(self, projectile: Projectile) -> tk.PhotoImage | None:
        """Select the nearest pre-rotated frame for a projectile's velocity."""
        frames = self.boss_projectile_sprites.get(projectile.style)
        if not frames:
            return None
        angle = math.atan2(projectile.vy, projectile.vx) % math.tau
        index = round(angle / math.tau * BOSS_PROJECTILE_DIRECTIONS) % BOSS_PROJECTILE_DIRECTIONS
        return frames[index]

    def _boss_sprite_for_attack(self, enemy: Enemy) -> tk.PhotoImage | None:
        if enemy.windup > 0:
            return self.boss_attack_sprites.get(enemy.pending_attack, self.boss_sprite)
        if enemy.attack_pose_time > 0:
            return self.boss_attack_sprites.get(enemy.attack_pose, self.boss_sprite)
        if enemy.moving and self.boss_walk_sprites:
            return self.boss_walk_sprites[int(enemy.walk_time * 6) % len(self.boss_walk_sprites)]
        return self.boss_sprite

    def _load_enemy_sprites(self) -> dict[str, dict[str, list[tk.PhotoImage]]]:
        """Load the normalized basic animation sets for the three regular enemies."""
        root = Path(__file__).resolve().parent.parent / "assets" / "sprites" / "enemies" / "frames_v6"
        enemy_ids = {
            "灰の兵士": "ash_soldier",
            "廃騎士": "ruined_knight",
            "さまよう影": "wandering_shadow",
        }
        loaded: dict[str, dict[str, list[tk.PhotoImage]]] = {}
        try:
            for enemy_name, enemy_id in enemy_ids.items():
                loaded[enemy_name] = {}
                for direction in ("up", "down", "left", "right"):
                    for animation in ("idle", "walk", "attack"):
                        key = f"{animation}_{direction}"
                        loaded[enemy_name][key] = [
                            tk.PhotoImage(file=str(root / enemy_id / direction / animation / f"{index:02}.png"))
                            for index in range(1, 5)
                        ]
            return loaded
        except (tk.TclError, OSError) as exc:
            print(f"Could not load enemy animation: {exc}", file=sys.stderr)
            return {}

    def _enemy_sprite(self, enemy: Enemy) -> tk.PhotoImage | None:
        sprites = self.enemy_sprites.get(enemy.name)
        if not sprites:
            return None
        dx, dy = self.px - enemy.x, self.py - enemy.y
        if abs(dx) > abs(dy):
            direction = "right" if dx >= 0 else "left"
        else:
            direction = "down" if dy >= 0 else "up"
        if enemy.windup > 0 or enemy.pending_attack:
            animation = "attack"
            progress = 1.0 - enemy.windup / max(0.001, enemy.windup_max)
            frame_index = min(3, max(0, int(progress * 4)))
        elif self._distance(self.px, self.py, enemy.x, enemy.y) < 360:
            animation = "walk"
            frame_index = int(time.perf_counter() * ENEMY_WALK_FPS) % 4
        else:
            animation = "idle"
            frame_index = int(time.perf_counter() * ENEMY_IDLE_FPS) % 4
        return sprites[f"{animation}_{direction}"][frame_index]

    def _player_sprite_offset(self) -> int:
        """Keep each direction's feet on the collision position."""
        # The 84 px runtime frames retain the source contact point and leave
        # a seven-pixel transparent gap below the player's feet.
        return 7

    def _enemy_sprite_offset(self) -> int:
        """Keep the normalized enemy frame's contact point on its world position."""
        # Enemy frames use a foot/hover contact point at y=84 on a 96 px
        # canvas.  With a south anchor the 12 px transparent bottom margin
        # must sit below the enemy's collision position.
        return 12

    # ------------------------------------------------------------------
    # Game setup and map generation
    # ------------------------------------------------------------------

    def _reset_game(
        self,
        stage_seed: int | None = None,
        restart_message: str | None = None,
        preserve_progress: bool = False,
    ) -> None:
        progress = None
        if preserve_progress:
            progress = {
                "relics": {relic.key for relic in self.relics if relic.collected},
                "skill": self.skill,
                "attack": self.attack,
                "max_hp": self.max_hp,
                "armor_bonus": self.armor_bonus,
                "truth": self.truth,
                "allies": set(self.allies),
                "dungeon_number": getattr(self, "dungeon_number", 1) + 1,
            }
        self.dungeon_number = progress["dungeon_number"] if progress else 1
        self.keys: set[str] = set()
        self.px, self.py = stage(960), stage(1840)
        self.facing = (0.0, -1.0)
        self.dodge_direction = self.facing
        self.hp = self.max_hp = 100
        self.player_shield = 0
        self.ally_shield_cd = 0.0
        self.attack = 18
        self.armor_bonus = 0
        self.truth = 0
        self.skill = "none"
        self.message = restart_message or "遺跡を探索せよ。左クリック / F で攻撃。"
        self.message_until = time.perf_counter() + 5
        self.attack_cd = self.dodge_time = self.dodge_cd = 0.0
        self.attack_flash = 0.0
        self.hurt_invincible = 0.0
        self.hit_stop_time = 0.0
        self.screen_shake_time = 0.0
        self.screen_shake_strength = 0.0
        self.interact_cd = 0.0
        self.game_over = False
        self.next_dungeon_timer = 0.0
        self.has_ally = False
        self.allies: set[str] = set()
        ally_by_dungeon = {1: "ミラ", 2: "灰騎士レオン", 3: "星詠みノア"}
        self.ally_candidate_name = ally_by_dungeon.get(self.dungeon_number, "")
        self.inscription_found = False
        self.door_open = False
        self.boss_gate_locked = False
        self.stage_seed = stage_seed if stage_seed is not None else random.randrange(1_000_000)
        self.rng = random.Random(self.stage_seed)

        self.walls = self._make_walls()
        self.reachable_cells = self._reachable_cells(self.walls, door_open=False)
        self.ally_candidate_x, self.ally_candidate_y = self._random_open_position(30)
        self.relics = [
            Relic("blade", "灰刃の欠片", 0, 0, "#ef6246", 1),
            Relic("lantern", "灯火の小瓶", 0, 0, "#ffd65c", 1),
            Relic("heart", "黒い心臓石", 0, 0, "#7d269d", 2),
        ]
        if self.dungeon_number >= 2:
            self.relics.extend((
                Relic("chalice", "命脈の聖杯", 0, 0, "#69d6b0", 1),
                Relic("gauntlet", "巨人の籠手", 0, 0, "#d98b52", 1),
                Relic("wing", "白銀の翼章", 0, 0, "#b8d8ef", 1),
            ))
        if self.dungeon_number >= 3:
            self.relics.extend((
                Relic("ember", "暁火の結晶", 0, 0, "#ff765c", 1),
                Relic("ward", "古王の護符", 0, 0, "#9e8bd8", 1),
                Relic("dew", "月雫の宝珠", 0, 0, "#75c8ef", 1),
            ))
        occupied = [(self.ally_candidate_x, self.ally_candidate_y)]
        for relic in self.relics:
            relic.x, relic.y = self._random_open_position(24, occupied)
            occupied.append((relic.x, relic.y))
        if progress:
            for relic in self.relics:
                relic.collected = relic.key in progress["relics"]
            self.skill = progress["skill"]
            self.attack = progress["attack"]
            self.max_hp = progress["max_hp"]
            self.hp = self.max_hp
            self.armor_bonus = progress["armor_bonus"]
            self.truth = progress["truth"]
            self.allies = progress["allies"]
            self.has_ally = bool(self.allies)
            self.door_open = self._has("lantern")
            if self.ally_candidate_name in self.allies:
                self.ally_candidate_name = ""
        self.companions = {
            name: Companion(name, self.px + index * 12, self.py + index * 12)
            for index, name in enumerate(sorted(self.allies))
        }
        self.enemies = self._make_enemies()
        self.projectiles: list[Projectile] = []
        self.ally_bolts: list[AllyBolt] = []
        self.particles: list[Particle] = []
        self.light_rings: list[LightRing] = []
        self.screen_flash_color = "#ffffff"
        self.screen_flash_time = 0.0
        self.screen_flash_duration = 0.0
        self.last_time = time.perf_counter()

    def _make_walls(self) -> list[tuple[float, float, float, float]]:
        border = stage(35)
        walls = [
            (0, 0, WORLD_SIZE, border),
            (0, WORLD_SIZE - border, WORLD_SIZE, border),
            (0, 0, border, WORLD_SIZE),
            (WORLD_SIZE - border, 0, border, WORLD_SIZE),
            # Boss chamber: the opening in the south wall is the sealed door.
            (stage(560), stage(120), stage(800), stage(35)),
            (stage(560), stage(120), stage(35), stage(565)),
            (stage(1325), stage(120), stage(35), stage(565)),
            (stage(560), stage(650), stage(200), stage(35)),
            (stage(1160), stage(650), stage(200), stage(35)),
            # Shrine room: the gap in the south wall is its entrance.
            (stage(720), stage(1480), stage(480), stage(35)),
            (stage(720), stage(1480), stage(35), stage(300)),
            (stage(1165), stage(1480), stage(35), stage(300)),
            (stage(720), stage(1745), stage(200), stage(35)),
            (stage(1000), stage(1745), stage(200), stage(35)),
        ]

        protected = [
            (self.px, self.py),
            (stage(960), stage(1660)),  # shrine
            (stage(960), stage(230)),   # exit
            (stage(1110), stage(560)),  # inscription
            (stage(960), stage(430)),   # boss
            (stage(960), stage(650)),   # sealed door
        ]
        boss_chamber = (stage(560), stage(120), stage(800), stage(565))
        shrine_room = (stage(720), stage(1480), stage(480), stage(300))
        attempts = 0
        while len(walls) < 38 and attempts < 500:
            attempts += 1
            if self.rng.random() < 0.55:
                width = self.rng.randint(180, 460)
                height = self.rng.randint(38, 64)
            else:
                width = self.rng.randint(38, 64)
                height = self.rng.randint(180, 460)
            x = self.rng.randint(int(border + 90), int(WORLD_SIZE - border - width - 90))
            y = self.rng.randint(int(border + 90), int(WORLD_SIZE - border - height - 90))
            candidate = (float(x), float(y), float(width), float(height))
            if any(self._point_near_rect(px, py, candidate, 150) for px, py in protected):
                continue
            if self._rects_overlap(candidate, boss_chamber, 70):
                continue
            if self._rects_overlap(candidate, shrine_room, 70):
                continue
            if any(self._rects_overlap(candidate, wall, 55) for wall in walls[4:]):
                continue
            walls.append(candidate)
        # Remove the newest random obstacles until every required route is open.
        while len(walls) > 14 and not self._stage_routes_valid(walls):
            walls.pop()
        return walls

    def _stage_routes_valid(
        self,
        walls: list[tuple[float, float, float, float]],
    ) -> bool:
        """Check required routes on a coarse navigation grid."""
        snap = lambda point: (round(point[0] / 48), round(point[1] / 48))

        outside_targets = [
            (stage(960), stage(1660)),  # shrine
            (stage(960), stage(740)),   # outside the boss door
        ]
        inside_targets = [
            (stage(960), stage(430)),   # boss
            (stage(960), stage(230)),   # exit
        ]
        outside_cells = self._reachable_cells(walls, door_open=False)
        inside_cells = self._reachable_cells(walls, door_open=True)
        return (
            {snap(target) for target in outside_targets}.issubset(outside_cells)
            and {snap(target) for target in inside_targets}.issubset(inside_cells)
        )

    def _reachable_cells(
        self,
        walls: list[tuple[float, float, float, float]],
        door_open: bool,
    ) -> set[tuple[int, int]]:
        cell, radius = 48, 24
        start = (round(self.px / cell), round(self.py / cell))
        queue = [start]
        visited = {start}
        while queue:
            gx, gy = queue.pop()
            for nx, ny in ((gx + 1, gy), (gx - 1, gy), (gx, gy + 1), (gx, gy - 1)):
                if (nx, ny) in visited:
                    continue
                x, y = nx * cell, ny * cell
                if not (radius < x < WORLD_SIZE - radius and radius < y < WORLD_SIZE - radius):
                    continue
                if any(
                    wx - radius < x < wx + ww + radius
                    and wy - radius < y < wy + wh + radius
                    for wx, wy, ww, wh in walls
                ):
                    continue
                if (
                    not door_open
                    and stage(760) - radius < x < stage(1160) + radius
                    and stage(615) - radius < y < stage(685) + radius
                ):
                    continue
                visited.add((nx, ny))
                queue.append((nx, ny))
        return visited

    def _make_enemies(self) -> list[Enemy]:
        tier = self.dungeon_number - 1
        hp_scale = 1.0 + tier * 0.45
        damage_scale = 1.0 + tier * 0.25
        speed_scale = 1.0 + tier * 0.07
        specs = (
            [("灰の兵士", 45, 10, 95, 23, "#9e3129")] * 8
            + [("廃騎士", 70, 16, 78, 29, "#6f2623")] * 4
            + [("さまよう影", 32, 14, 125, 20, "#63377d")] * 5
        )
        occupied = [(self.px, self.py)] + [(r.x, r.y) for r in self.relics]
        enemies = []
        for name, hp, damage, speed, radius, color in specs:
            x, y = self._random_open_position(
                radius + 10, occupied, exclude_shrine_room=True,
            )
            occupied.append((x, y))
            enemies.append(Enemy(
                name, x, y,
                round(hp * hp_scale),
                round(damage * damage_scale),
                speed * speed_scale,
                radius, color,
                ranged=name == "さまよう影",
            ))
        boss_hp = 240 + tier * 180
        boss_damage = 22 + tier * 9
        boss_shield = round(180 * (1.0 + tier * 0.45))
        enemies.append(Enemy(
            "王国の守護者", stage(960), stage(430),
            boss_hp,
            boss_damage,
            68 * speed_scale,
            46, "#17151e", True,
            max_hp=boss_hp, shield=boss_shield, max_shield=boss_shield,
        ))
        return enemies

    def _random_open_position(
        self,
        radius: float,
        occupied: list[tuple[float, float]] | None = None,
        exclude_shrine_room: bool = False,
    ) -> tuple[float, float]:
        """Find a clear generated position away from important objects."""
        occupied = occupied or []
        margin = int(stage(70) + radius)
        for _ in range(800):
            x = float(self.rng.randint(margin, WORLD_SIZE - margin))
            y = float(self.rng.randint(margin, WORLD_SIZE - margin))
            reachable = getattr(self, "reachable_cells", None)
            if reachable is not None and (round(x / 48), round(y / 48)) not in reachable:
                continue
            if self._inside_boss_chamber(x, y, radius + 30):
                continue
            if exclude_shrine_room and self._inside_shrine_room(x, y, radius):
                continue
            if self._blocked(x, y, radius + 18):
                continue
            if self._distance(x, y, self.px, self.py) < 260:
                continue
            if any(self._distance(x, y, ox, oy) < 180 for ox, oy in occupied):
                continue
            return x, y
        # The sparse generator should never need this, but keep a safe fallback.
        return WORLD_SIZE / 2, WORLD_SIZE / 2

    @staticmethod
    def _inside_boss_chamber(x: float, y: float, margin: float = 0) -> bool:
        """Keep generated objects out of the boss arena."""
        left, top = stage(560), stage(120)
        right, bottom = stage(1360), stage(685)
        return (
            left - margin < x < right + margin
            and top - margin < y < bottom + margin
        )

    @staticmethod
    def _inside_shrine_room(x: float, y: float, margin: float = 0) -> bool:
        """Return whether a spawn circle overlaps the healing shrine room."""
        left, top = stage(720), stage(1480)
        right, bottom = stage(1200), stage(1780)
        return (
            left - margin < x < right + margin
            and top - margin < y < bottom + margin
        )

    @staticmethod
    def _inside_boss_arena(x: float, y: float, radius: float = 0) -> bool:
        """Return whether a circle is fully inside the boss room's inner walls."""
        left, top = stage(595), stage(155)
        right, bottom = stage(1325), stage(650)
        return (
            left + radius <= x <= right - radius
            and top + radius <= y <= bottom - radius
        )

    @staticmethod
    def _point_near_rect(
        x: float,
        y: float,
        rect: tuple[float, float, float, float],
        margin: float,
    ) -> bool:
        rx, ry, rw, rh = rect
        return rx - margin <= x <= rx + rw + margin and ry - margin <= y <= ry + rh + margin

    @staticmethod
    def _rects_overlap(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
        margin: float,
    ) -> bool:
        ax, ay, aw, ah = first
        bx, by, bw, bh = second
        return (
            ax < bx + bw + margin
            and ax + aw + margin > bx
            and ay < by + bh + margin
            and ay + ah + margin > by
        )

    # ------------------------------------------------------------------
    # Input and menu state
    # ------------------------------------------------------------------

    def _key_down(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if self.ui_mode != "playing":
            self._handle_menu_key(key)
            return
        if key in {"p", "escape"} and not self.game_over:
            self.ui_mode = "paused"
            self.menu_index = 0
            self.keys.clear()
            return
        if self.game_over and key in {"r", "n"}:
            self._restart(new_stage=key == "n")
            return
        self.keys.add(key)
        if key in {"f", "return"}:
            self._attack()
        elif key in {"1", "2", "3", "4", "5", "6", "7", "8", "9"}:
            self._select_skill(key)
        elif key == "escape":
            self.root.destroy()

    def _handle_menu_key(self, key: str) -> None:
        if self.ui_mode == "help":
            if key in {"escape", "backspace", "return", "space"}:
                self.ui_mode = self.menu_return_mode
            return

        options = 3 if self.ui_mode == "title" else 4
        if key in {"up", "w"}:
            self.menu_index = (self.menu_index - 1) % options
            return
        if key in {"down", "s"}:
            self.menu_index = (self.menu_index + 1) % options
            return
        if key == "escape":
            if self.ui_mode == "paused":
                self.ui_mode = "playing"
                self.last_time = time.perf_counter()
            else:
                self.root.destroy()
            return
        if key not in {"return", "space"}:
            return

        if self.ui_mode == "title":
            if self.menu_index == 0:
                self._reset_game()
                self.ui_mode = "playing"
                self.last_time = time.perf_counter()
            elif self.menu_index == 1:
                self.menu_return_mode = "title"
                self.ui_mode = "help"
            else:
                self.root.destroy()
        elif self.ui_mode == "paused":
            if self.menu_index == 0:
                self.ui_mode = "playing"
                self.last_time = time.perf_counter()
            elif self.menu_index == 1:
                self.menu_return_mode = "paused"
                self.ui_mode = "help"
            elif self.menu_index == 2:
                self.ui_mode = "title"
                self.menu_index = 0
            else:
                self.root.destroy()

    def _restart(self, new_stage: bool) -> None:
        if not new_stage and getattr(self, "retry_used", False):
            self._say("同じステージへの再挑戦は1回までです。N: 新しい遺跡  Esc: 終了", 999)
            return
        if new_stage:
            self.retry_used = False
        else:
            self.retry_used = True
        seed = None if new_stage else self.stage_seed
        message = (
            "新しい遺跡を生成した。探索を始めよう。"
            if new_stage
            else "同じ遺跡への再挑戦を開始した。"
        )
        self._reset_game(seed, message)

    def _end_options(self) -> str:
        if self.retry_used:
            return "N: 新しい遺跡  Esc: 終了"
        return "R: 再挑戦  N: 新しい遺跡  Esc: 終了"

    def _key_up(self, event: tk.Event) -> None:
        self.keys.discard(event.keysym.lower())

    def _aim_with_mouse(self, event: tk.Event) -> None:
        """Turn the player toward the mouse cursor."""
        if self.ui_mode in {"title", "paused"}:
            self._select_menu_with_mouse(event.y)
            return
        if self.ui_mode != "playing":
            return
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        cam_x = min(max(self.px - width / 2, 0), WORLD_SIZE - width)
        cam_y = min(max(self.py - height / 2, 0), WORLD_SIZE - height)
        mouse_world_x = event.x + cam_x
        mouse_world_y = event.y + cam_y
        dx = mouse_world_x - self.px
        dy = mouse_world_y - self.py
        length = math.hypot(dx, dy)
        if length > 1:
            self.facing = (dx / length, dy / length)

    def _mouse_attack(self, event: tk.Event) -> None:
        if self.ui_mode != "playing":
            if self.ui_mode == "help":
                self.ui_mode = self.menu_return_mode
                return
            if self._select_menu_with_mouse(event.y):
                self._handle_menu_key("return")
            return
        self._aim_with_mouse(event)
        self._attack()

    def _select_menu_with_mouse(self, mouse_y: float) -> bool:
        if self.ui_mode == "title":
            start_y = self.canvas.winfo_height() * 0.48
            option_count = 3
        elif self.ui_mode == "paused":
            start_y = 205
            option_count = 4
        else:
            return False
        for index in range(option_count):
            option_y = start_y + index * 58
            if option_y - 25 <= mouse_y <= option_y + 25:
                self.menu_index = index
                return True
        return False

    # ------------------------------------------------------------------
    # Main update loop and movement
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        now = time.perf_counter()
        dt = min(now - self.last_time, 0.05)
        self.last_time = now
        if self.hit_stop_time > 0:
            self.hit_stop_time = max(0.0, self.hit_stop_time - dt)
            if self.ui_mode == "playing" and not self.game_over:
                self._update_player_input(dt)
                self._update_boss_gate()
        elif self.ui_mode == "playing" and not self.game_over:
            self._update(dt)
        self._update_effects(dt)
        self._draw()
        elapsed = time.perf_counter() - now
        self.root.after(max(1, math.ceil((1 / 60 - elapsed) * 1000)), self._loop)

    def _update(self, dt: float) -> None:
        if self.next_dungeon_timer > 0:
            self.next_dungeon_timer = max(0.0, self.next_dungeon_timer - dt)
            if self.next_dungeon_timer == 0:
                self._reset_game(
                    restart_message=(
                        f"第{self.dungeon_number + 1}遺跡へ進んだ。"
                        "遺物とミラを引き継いで探索を続けよう。"
                    ),
                    preserve_progress=True,
                )
                return
        self.hurt_invincible = max(0.0, self.hurt_invincible - dt)
        self.interact_cd = max(0.0, self.interact_cd - dt)

        self._update_player_input(dt)

        self._update_boss_gate()
        self._collect_relics()
        self._interact()
        self._update_ally(dt)
        self._update_ally_bolts(dt)
        self._update_enemies(dt)
        self._update_projectiles(dt)
        self._check_ending()

    def _update_player_input(self, dt: float) -> None:
        """Poll held attack keys each frame, including during hit-stop."""
        self.ally_shield_cd = max(0.0, self.ally_shield_cd - dt)
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.attack_flash = max(0.0, self.attack_flash - dt)
        self._update_player_movement(dt)
        if self.keys.intersection({"f", "return"}) and self.attack_cd == 0:
            self._attack()

    def _update_player_movement(self, dt: float) -> None:
        """Keep movement and dodge responsive even during combat hit-stop."""
        self.dodge_time = max(0.0, self.dodge_time - dt)
        self.dodge_cd = max(0.0, self.dodge_cd - dt)
        dx = float("d" in self.keys or "right" in self.keys) - float("a" in self.keys or "left" in self.keys)
        dy = float("s" in self.keys or "down" in self.keys) - float("w" in self.keys or "up" in self.keys)
        if dx or dy:
            length = math.hypot(dx, dy)
            dx, dy = dx / length, dy / length
            self.facing = (dx, dy)
        if "space" in self.keys and self.dodge_cd == 0:
            width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
            cam_x = min(max(self.px - width / 2, 0), WORLD_SIZE - width)
            cam_y = min(max(self.py - height / 2, 0), WORLD_SIZE - height)
            cursor_dx = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx() + cam_x - self.px
            cursor_dy = self.canvas.winfo_pointery() - self.canvas.winfo_rooty() + cam_y - self.py
            length = math.hypot(cursor_dx, cursor_dy)
            self.dodge_direction = (
                (cursor_dx / length, cursor_dy / length) if length > 1 else self.facing
            )
            self.dodge_time, self.dodge_cd = DODGE_DURATION, DODGE_COOLDOWN
        if self.dodge_time:
            dx, dy = self.dodge_direction
            self.facing = self.dodge_direction
        speed = DODGE_SPEED if self.dodge_time else PLAYER_SPEED
        if dx or dy:
            self._move_player(dx * speed * dt, dy * speed * dt)

    def _move_player(self, dx: float, dy: float) -> None:
        nx = self.px + dx
        if not self._blocked(nx, self.py, PLAYER_RADIUS):
            self.px = nx
        ny = self.py + dy
        if not self._blocked(self.px, ny, PLAYER_RADIUS):
            self.py = ny

    def _blocked(self, x: float, y: float, radius: float) -> bool:
        for wx, wy, ww, wh in self.walls:
            if wx - radius < x < wx + ww + radius and wy - radius < y < wy + wh + radius:
                return True
        if (
            (not self.door_open or self.boss_gate_locked)
            and stage(760) < x < stage(1160)
            and stage(615) - radius < y < stage(685) + radius
        ):
            return True
        return False

    def _update_boss_gate(self) -> None:
        """Seal the entrance after the player has fully crossed into the arena."""
        if (
            self.door_open
            and not self.boss_gate_locked
            and any(enemy.boss for enemy in self.enemies)
            and stage(760) < self.px < stage(1160)
            and self.py <= stage(615) - PLAYER_RADIUS
            and self._inside_boss_arena(self.px, self.py)
        ):
            self.boss_gate_locked = True
            for index, companion in enumerate(self.companions.values()):
                companion.x = self.px + (index - len(self.companions) / 2) * 24
                companion.y = self.py - 35
                companion.path.clear()
            self._play_sound("warning")
            self._say("ボス部屋の入口が封鎖された。守護者を倒せ！", 2.4)

    def _line_blocked(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float = 0,
    ) -> bool:
        """Return whether a wall intersects the complete attack path."""
        distance = self._distance(x1, y1, x2, y2)
        steps = max(1, math.ceil(distance / 8))
        for step_number in range(1, steps + 1):
            ratio = step_number / steps
            x = x1 + (x2 - x1) * ratio
            y = y1 + (y2 - y1) * ratio
            if self._blocked(x, y, radius):
                return True
        return False

    def _collect_relics(self) -> None:
        for relic in self.relics:
            if not relic.collected and self._distance(self.px, self.py, relic.x, relic.y) < 45:
                relic.collected = True
                self._spawn_visual_effect(
                    relic.x, relic.y, relic.color,
                    particle_count=24, ring_size=105,
                    flash_color="#fff0a6", flash_duration=0.16,
                )
                self.truth += relic.truth
                if relic.key == "blade":
                    self.attack += 12
                if relic.key == "heart":
                    self.skill = "dark"
                if relic.key == "chalice":
                    self.max_hp += 30
                    self.hp += 30
                if relic.key == "gauntlet":
                    self.attack += 16
                if relic.key == "wing":
                    self.armor_bonus += 5
                if relic.key == "ember":
                    self.attack += 24
                if relic.key == "ward":
                    self.armor_bonus += 8
                if relic.key == "dew":
                    self.max_hp += 50
                    self.hp += 50
                self._say(f"遺物「{relic.name}」を入手した。")
        if self._has("lantern") and not self.door_open:
            self.door_open = True
            self._say("灯火が封印を暴き、扉が開いた。")

    def _interact(self) -> None:
        if "e" not in self.keys or self.interact_cd:
            return
        self.interact_cd = 0.6
        if self._distance(self.px, self.py, stage(960), stage(1660)) < 90:
            self.hp = self.max_hp
            self._spawn_visual_effect(
                stage(960), stage(1660), "#72d8ff",
                particle_count=30, ring_size=135,
                flash_color="#b9efff", flash_duration=0.2,
            )
            self._say("壊れた祠の光が傷を癒やした。")
        elif self._has("lantern") and not self.inscription_found and self._distance(self.px, self.py, stage(1110), stage(560)) < 75:
            self.inscription_found = True
            self.truth += 1
            self._say("隠された碑文を発見した。真相度が上昇。")

    # ------------------------------------------------------------------
    # Ally behavior
    # ------------------------------------------------------------------

    def _update_ally(self, dt: float) -> None:
        if self.ally_candidate_name and self._distance(
            self.px, self.py, self.ally_candidate_x, self.ally_candidate_y,
        ) < 60:
            joined_name = self.ally_candidate_name
            self.allies.add(joined_name)
            self.companions[joined_name] = Companion(
                joined_name, self.ally_candidate_x, self.ally_candidate_y,
            )
            self.ally_candidate_name = ""
            self.has_ally = True
            self.truth += 1
            self._say(f"{joined_name}が仲間になった。")
        if not self.has_ally:
            return
        companions = [self.companions[name] for name in sorted(self.companions)]
        for index, companion in enumerate(companions):
            angle = math.tau * index / max(1, len(companions))
            target_x = self.px + math.cos(angle) * ALLY_FOLLOW_DISTANCE
            target_y = self.py + math.sin(angle) * ALLY_FOLLOW_DISTANCE
            self._update_one_companion(companion, target_x, target_y, dt)

    def _update_one_companion(
        self, companion: Companion, target_x: float, target_y: float, dt: float,
    ) -> None:
        """Advance timers, follow movement, animation state, and combat for one ally."""
        companion.pose_time = max(0.0, companion.pose_time - dt)
        companion.cooldown = max(0.0, companion.cooldown - dt)
        companion.path_timer = max(0.0, companion.path_timer - dt)

        old_x, old_y = companion.x, companion.y
        self._update_companion_movement(companion, target_x, target_y, dt)
        dx, dy = companion.x - old_x, companion.y - old_y
        companion.moving = math.hypot(dx, dy) > 0.15
        if companion.moving:
            self._update_companion_facing(companion, dx, dy, dt)
            companion.walk_time += dt
        else:
            companion.walk_time = 0.0
        if companion.cooldown == 0:
            self._perform_companion_action(companion)

    @staticmethod
    def _update_companion_facing(
        companion: Companion, dx: float, dy: float, dt: float,
    ) -> None:
        """Change direction only after it stays stable, avoiding left/right flicker."""
        desired = (
            ("right" if dx > 0 else "left")
            if abs(dx) > abs(dy)
            else ("down" if dy > 0 else "up")
        )
        if desired == companion.facing:
            companion.facing_candidate = ""
            companion.facing_candidate_time = 0.0
            return
        if desired != companion.facing_candidate:
            companion.facing_candidate = desired
            companion.facing_candidate_time = 0.0
        companion.facing_candidate_time += dt
        if companion.facing_candidate_time >= ALLY_FACING_CONFIRM_SECONDS:
            companion.facing = desired
            companion.facing_candidate = ""
            companion.facing_candidate_time = 0.0

    def _update_companion_movement(
        self, companion: Companion, target_x: float, target_y: float, dt: float,
    ) -> None:
        if not self._line_blocked(companion.x, companion.y, target_x, target_y, 18):
            companion.path.clear()
            self._move_ally_toward(companion, target_x, target_y, dt)
            return
        if companion.path_timer == 0:
            companion.path = self._find_ally_path(companion, target_x, target_y)
            companion.path_timer = 0.35
        if companion.path:
            waypoint_x, waypoint_y = companion.path[0]
            if self._distance(companion.x, companion.y, waypoint_x, waypoint_y) < 14:
                companion.path.pop(0)
            if companion.path:
                self._move_ally_toward(companion, *companion.path[0], dt)

    def _player_shield_capacity(self) -> int:
        """Start at 20 shield points and add 15 per additional ally."""
        if not self.allies:
            return 0
        return ALLY_SHIELD_AMOUNT + ALLY_SHIELD_PER_EXTRA_ALLY * (len(self.allies) - 1)

    def _perform_companion_action(self, companion: Companion) -> None:
        if companion.name == "ミラ" and self.hp <= self.max_hp * 0.55:
            healed = min(14, self.max_hp - self.hp)
            self.hp += healed
            companion.cooldown = companion.cooldown_max = 4.0
            companion.pose, companion.pose_time = "heal", 0.45
            self._spawn_visual_effect(
                self.px, self.py, "#72efae", 12, 58, "#bfffd8", 0.08,
            )
            self._say(f"ミラの祈りでHPが{healed}回復した。")
            return
        if (
            self.player_shield == 0 and self.ally_shield_cd == 0
            and self._distance(companion.x, companion.y, self.px, self.py) <= 240
            and not self._line_blocked(companion.x, companion.y, self.px, self.py, 4)
        ):
            self.player_shield = self._player_shield_capacity()
            self.ally_shield_cd = ALLY_SHIELD_COOLDOWN
            companion.cooldown = companion.cooldown_max = 1.0
            companion.pose, companion.pose_time = "heal", 0.45
            self._spawn_visual_effect(
                self.px, self.py, "#70dfff", 12, 60, "#c9f6ff", 0.08,
            )
            self._say(f"{companion.name}がシールドを付与した！")
            return
        ranges = {"ミラ": 250, "灰騎士レオン": 150, "星詠みノア": 380}
        damages = {"ミラ": 8, "灰騎士レオン": 18, "星詠みノア": 13}
        cooldowns = {"ミラ": 2.0, "灰騎士レオン": 1.15, "星詠みノア": 2.35}
        attack_range = ranges.get(companion.name, 250)
        targets = [
            enemy for enemy in self.enemies
            if self._distance(companion.x, companion.y, enemy.x, enemy.y) < attack_range
            and not self._line_blocked(companion.x, companion.y, enemy.x, enemy.y, 4)
        ]
        if not targets:
            return
        target = min(
            targets,
            key=lambda enemy: self._distance(companion.x, companion.y, enemy.x, enemy.y),
        )
        damage = damages.get(companion.name, 8)
        if companion.name == "ミラ" and self.skill == "lantern":
            damage += 6
        self.ally_bolts.append(AllyBolt(companion.x, companion.y, target, damage))
        companion.pose, companion.pose_time = "attack", 0.45
        companion.cooldown = companion.cooldown_max = cooldowns.get(companion.name, 2.0)

    def _find_ally_path(
        self, companion: Companion, target_x: float, target_y: float,
    ) -> list[tuple[float, float]]:
        """Find a short collision-safe grid path around walls using A*."""
        return find_path(
            (companion.x, companion.y),
            (target_x, target_y),
            self._blocked,
            WORLD_SIZE,
        )

    def _update_ally_bolts(self, dt: float) -> None:
        for bolt in self.ally_bolts[:]:
            bolt.life -= dt
            if bolt.life <= 0 or bolt.target not in self.enemies:
                self.ally_bolts.remove(bolt)
                continue
            dx, dy = bolt.target.x - bolt.x, bolt.target.y - bolt.y
            distance = math.hypot(dx, dy)
            if distance <= bolt.target.radius + 8:
                self._damage_enemy(bolt.target, bolt.damage)
                self._spawn_visual_effect(
                    bolt.target.x, bolt.target.y, "#8de7ff", 6, 28, "#c9f6ff", 0.03,
                )
                self.ally_bolts.remove(bolt)
                self._remove_dead()
                continue
            travel = min(distance, bolt.speed * dt)
            old_x, old_y = bolt.x, bolt.y
            bolt.x += dx / max(1.0, distance) * travel
            bolt.y += dy / max(1.0, distance) * travel
            if self._line_blocked(old_x, old_y, bolt.x, bolt.y, 4):
                self.ally_bolts.remove(bolt)

    def _move_ally_toward(
        self, companion: Companion, target_x: float, target_y: float, dt: float,
    ) -> None:
        """Move the ally without tunnelling into or through walls."""
        radius = 18.0
        if self._blocked(companion.x, companion.y, radius):
            self._recover_ally_from_wall(companion, radius)

        dx = (target_x - companion.x) * min(1.0, dt * 5.0)
        dy = (target_y - companion.y) * min(1.0, dt * 5.0)
        steps = max(1, math.ceil(math.hypot(dx, dy) / 8.0))
        step_x, step_y = dx / steps, dy / steps
        for _ in range(steps):
            next_x = companion.x + step_x
            if not self._blocked(next_x, companion.y, radius):
                companion.x = next_x
            next_y = companion.y + step_y
            if not self._blocked(companion.x, next_y, radius):
                companion.y = next_y

    def _recover_ally_from_wall(self, companion: Companion, radius: float) -> None:
        """Place an already-overlapping ally at the nearest open position."""
        origin_x, origin_y = companion.x, companion.y
        for distance in range(8, 169, 8):
            for direction in range(16):
                angle = math.tau * direction / 16
                x = origin_x + math.cos(angle) * distance
                y = origin_y + math.sin(angle) * distance
                if not self._blocked(x, y, radius):
                    companion.x, companion.y = x, y
                    return

        if not self._blocked(self.px, self.py, radius):
            companion.x, companion.y = self.px, self.py

    # ------------------------------------------------------------------
    # Enemy and boss behavior
    # ------------------------------------------------------------------

    def _update_enemies(self, dt: float) -> None:
        for enemy in self.enemies:
            enemy.cooldown = max(0.0, enemy.cooldown - dt)
            enemy.attack_pose_time = max(0.0, enemy.attack_pose_time - dt)
            enemy.moving = False
            if enemy.boss and not self.door_open:
                continue
            if (
                enemy.boss
                and enemy.hp <= enemy.max_hp / 2
                and enemy.boss_phase == 1
            ):
                enemy.boss_phase = 2
                enemy.hp = enemy.max_hp
                enemy.shield = enemy.max_shield
                enemy.speed = 88 * (1.0 + (self.dungeon_number - 1) * 0.07)
                enemy.cooldown = 0.7
                self._spawn_visual_effect(
                    enemy.x, enemy.y, "#df65ff", 30, 135, "#b22cff", 0.22,
                )
                self._start_screen_shake(0.45, 15)
                self._play_sound("phase")
                self._say("守護者が第二形態へ移行し、HPとシールドを全回復した！", 2.4)
            if enemy.windup > 0:
                enemy.windup = max(0.0, enemy.windup - dt)
                if enemy.windup == 0:
                    self._release_enemy_attack(enemy)
                continue
            distance = self._distance(self.px, self.py, enemy.x, enemy.y)
            # Keep the boss's full move set available at the edge of melee
            # range. Only a true point-blank approach forces a melee cleave.
            boss_special_min_range = enemy.radius + 60
            if (
                enemy.boss
                and boss_special_min_range < distance < 680
                and not enemy.cooldown
            ):
                attack_pool = self._boss_attack_pool(enemy)
                choices = [
                    attack for attack in attack_pool
                    if attack != enemy.last_boss_attack
                ]
                attack_type = self.rng.choice(choices)
                enemy.last_boss_attack = attack_type
                windup = {
                    "boss_fan": 0.8,
                    "boss_ring": 1.05,
                    "boss_lance": 0.58,
                    "boss_spiral": 1.15,
                    "boss_wave": 0.9,
                }[attack_type]
                if enemy.boss_phase == 2:
                    windup *= 0.8
                self._start_enemy_attack(enemy, attack_type, windup)
                continue
            elif enemy.ranged and 150 < distance < 520 and not enemy.cooldown:
                self._start_enemy_attack(enemy, "ranged", 0.58)
                continue
            if distance < 360 and distance and (not enemy.ranged or distance > 230):
                dx, dy = (self.px - enemy.x) / distance, (self.py - enemy.y) / distance
                nx, ny = enemy.x + dx * enemy.speed * dt, enemy.y + dy * enemy.speed * dt
                if not self._blocked(nx, ny, enemy.radius):
                    enemy.moving = math.hypot(nx - enemy.x, ny - enemy.y) > 0.001
                    enemy.x, enemy.y = nx, ny
                    if enemy.moving:
                        enemy.walk_time += dt
            distance = self._distance(self.px, self.py, enemy.x, enemy.y)
            # The boss cleave covers the player's melee range.  Previously the
            # 55px reach left a safe ring where the player could orbit and hit
            # the boss without ever provoking an attack.
            melee_reach = 120 if enemy.boss else 55
            if distance <= enemy.radius + melee_reach and not enemy.cooldown:
                self._start_enemy_attack(enemy, "melee", 0.38 if not enemy.boss else 0.55)
        self._separate_enemies()

    def _boss_attack_pool(self, enemy: Enemy) -> list[str]:
        """Retain earlier attacks and unlock one more in each second phase."""
        attacks = ["boss_fan", "boss_ring", "boss_lance", "boss_wave", "boss_spiral"]
        tier = min(3, max(1, self.dungeon_number))
        count = tier + 1 + (enemy.boss_phase >= 2)
        return attacks[:count]

    def _start_enemy_attack(self, enemy: Enemy, attack_type: str, windup: float) -> None:
        enemy.pending_attack = attack_type
        enemy.windup = enemy.windup_max = windup
        enemy.aim_x, enemy.aim_y = self.px, self.py
        if attack_type == "boss_spiral":
            enemy.spiral_shots_remaining = 4
        if attack_type.startswith("boss_"):
            self._play_sound("warning")

    def _release_enemy_attack(self, enemy: Enemy) -> None:
        attack_type = enemy.pending_attack
        if enemy.boss:
            self._play_sound("boss_melee" if attack_type == "melee" else attack_type)
            enemy.attack_pose = attack_type
            enemy.attack_pose_time = 0.25
        elif attack_type in ("melee", "ranged"):
            self._play_sound(f"enemy_{attack_type}")
        enemy.pending_attack = ""
        if attack_type == "melee":
            enemy.cooldown = 0.8 if enemy.boss else 1.1
            melee_reach = 130 if enemy.boss else 55
            if (
                self._distance(self.px, self.py, enemy.x, enemy.y) <= enemy.radius + melee_reach
                and not self._line_blocked(enemy.x, enemy.y, self.px, self.py, 3)
                and not self.dodge_time
            ):
                self._damage_player(
                    enemy.damage, f"{enemy.name}の攻撃！", enemy.x, enemy.y,
                )
        elif attack_type == "ranged":
            self._fire_projectile(enemy, enemy.aim_x, enemy.aim_y)
            enemy.cooldown = 1.7
        elif attack_type == "boss_fan":
            self._fire_boss_volley(enemy, enemy.aim_x, enemy.aim_y)
            enemy.cooldown = 0.95 if enemy.boss_phase == 2 else 1.5
        elif attack_type == "boss_ring":
            self._fire_boss_ring(enemy, enemy.aim_x, enemy.aim_y)
            enemy.cooldown = 1.15 if enemy.boss_phase == 2 else 1.8
        elif attack_type == "boss_lance":
            self._fire_boss_lance(enemy, enemy.aim_x, enemy.aim_y)
            enemy.cooldown = 0.85 if enemy.boss_phase == 2 else 1.3
        elif attack_type == "boss_spiral":
            self._fire_boss_spiral(enemy, enemy.aim_x, enemy.aim_y)
            enemy.spiral_shots_remaining -= 1
            if enemy.spiral_shots_remaining > 0:
                enemy.pending_attack = "boss_spiral"
                enemy.windup = enemy.windup_max = 0.22
                enemy.aim_x, enemy.aim_y = self.px, self.py
            else:
                enemy.cooldown = 1.45
        elif attack_type == "boss_wave":
            self._fire_boss_wave(enemy, enemy.aim_x, enemy.aim_y)
            enemy.cooldown = 1.2

    def _damage_player(
        self,
        base_damage: int,
        source: str,
        source_x: float | None = None,
        source_y: float | None = None,
        *,
        invincibility_duration: float = 0.55,
    ) -> None:
        if self.dodge_time or self.hurt_invincible > 0:
            return
        guard = (
            (5 if self.has_ally else 0)
            + (3 if "灰騎士レオン" in self.allies else 0)
            + self.armor_bonus
            + (4 if self.skill == "lantern" else 0)
            + (7 if self.skill == "wing" else 0)
            + (10 if self.skill == "ward" else 0)
        )
        damage = max(2, base_damage - guard)
        absorbed = min(self.player_shield, damage)
        self.player_shield -= absorbed
        hp_damage = damage - absorbed
        self.hp = max(0, self.hp - hp_damage)
        self.hurt_invincible = invincibility_duration
        self.hit_stop_time = max(self.hit_stop_time, 0.045)
        self._start_screen_shake(0.18, 11)
        self._play_sound("hurt")
        if source_x is not None and source_y is not None:
            self._knockback_player(source_x, source_y, 34)
        if absorbed:
            self._say(f"{source} シールドが{absorbed}吸収、HPに{hp_damage}ダメージ。")
        else:
            self._say(f"{source} {hp_damage}ダメージ。")
        if self.hp == 0:
            self.game_over = True
            self._say(f"灰の中に倒れた。{self._end_options()}", 999)

    @staticmethod
    def _damage_enemy(enemy: Enemy, damage: int) -> tuple[int, int]:
        """Apply damage to an enemy's shield before reducing its HP."""
        shield_damage = min(enemy.shield, damage)
        enemy.shield -= shield_damage
        hp_damage = damage - shield_damage
        enemy.hp = max(0, enemy.hp - hp_damage)
        return shield_damage, hp_damage

    def _fire_projectile(self, enemy: Enemy, target_x: float, target_y: float) -> None:
        speed = 330.0
        distance = max(1.0, self._distance(enemy.x, enemy.y, target_x, target_y))
        dx = (target_x - enemy.x) / distance
        dy = (target_y - enemy.y) / distance
        self.projectiles.append(Projectile(
            enemy.x + dx * (enemy.radius + 10),
            enemy.y + dy * (enemy.radius + 10),
            dx * speed,
            dy * speed,
            enemy.damage,
        ))

    def _fire_boss_volley(self, enemy: Enemy, target_x: float, target_y: float) -> None:
        """Fire a widening fan; below half HP the boss fires five shots."""
        self.projectiles.extend(create_fan(enemy, target_x, target_y))
        self._say("守護者が闇の弾幕を放つ！", 1.2)

    def _fire_boss_ring(self, enemy: Enemy, target_x: float, target_y: float) -> None:
        """Fire projectiles in every direction, rotated toward the player."""
        self.projectiles.extend(create_ring(enemy, target_x, target_y))
        self._say("守護者が全方向へ闇を放った！", 1.2)

    def _fire_boss_lance(self, enemy: Enemy, target_x: float, target_y: float) -> None:
        """Fire a tight sequence of aimed shots with different speeds."""
        self.projectiles.extend(create_lance(enemy, target_x, target_y))
        self._say("守護者が闇の槍を狙い定めた！", 1.0)

    def _fire_boss_spiral(self, enemy: Enemy, target_x: float, target_y: float) -> None:
        self.projectiles.extend(create_spiral(enemy, target_x, target_y))
        self._say("守護者の周囲で炎が螺旋を描く！", 1.2)

    def _fire_boss_wave(self, enemy: Enemy, target_x: float, target_y: float) -> None:
        self.projectiles.extend(create_wave(enemy, target_x, target_y))
        self._say("守護者が光の波を放った！ 隙間を抜けろ！", 1.2)

    def _separate_enemies(self) -> None:
        """Push overlapping enemies apart without moving them through walls."""
        for index, first in enumerate(self.enemies):
            for second in self.enemies[index + 1:]:
                dx, dy = second.x - first.x, second.y - first.y
                distance = math.hypot(dx, dy)
                minimum = first.radius + second.radius + 6
                if distance >= minimum:
                    continue
                if distance < 0.001:
                    angle = self.rng.random() * math.tau
                    ux, uy = math.cos(angle), math.sin(angle)
                    push = minimum / 2
                else:
                    ux, uy = dx / distance, dy / distance
                    push = (minimum - distance) / 2
                first_x, first_y = first.x - ux * push, first.y - uy * push
                second_x, second_y = second.x + ux * push, second.y + uy * push
                if not self._blocked(first_x, first_y, first.radius):
                    first.x, first.y = first_x, first_y
                if not self._blocked(second_x, second_y, second.radius):
                    second.x, second.y = second_x, second_y

    def _update_projectiles(self, dt: float) -> None:
        for projectile in self.projectiles[:]:
            projectile.life -= dt
            old_x, old_y = projectile.x, projectile.y
            if projectile.turn_rate:
                turn = projectile.turn_rate * dt
                cos_turn, sin_turn = math.cos(turn), math.sin(turn)
                projectile.vx, projectile.vy = (
                    projectile.vx * cos_turn - projectile.vy * sin_turn,
                    projectile.vx * sin_turn + projectile.vy * cos_turn,
                )
            projectile.x += projectile.vx * dt
            projectile.y += projectile.vy * dt
            if (
                projectile.life <= 0
                or (
                    projectile.boss_attack
                    and not self._inside_boss_arena(
                        projectile.x, projectile.y, projectile.radius,
                    )
                )
                or self._line_blocked(
                    old_x, old_y, projectile.x, projectile.y, projectile.radius,
                )
            ):
                self.projectiles.remove(projectile)
                continue
            if self._distance(self.px, self.py, projectile.x, projectile.y) < PLAYER_RADIUS + projectile.radius:
                self.projectiles.remove(projectile)
                self._damage_player(
                    projectile.damage,
                    "闇の弾を受けた！",
                    projectile.x - projectile.vx,
                    projectile.y - projectile.vy,
                    invincibility_duration=(
                        0.0 if projectile.boss_attack and projectile.style in {"lance", "spiral"}
                        else 0.55
                    ),
                )

    def _knockback_player(self, source_x: float, source_y: float, strength: float) -> None:
        dx, dy = self.px - source_x, self.py - source_y
        distance = math.hypot(dx, dy)
        if distance < 0.001:
            return
        self._move_player(dx / distance * strength, dy / distance * strength)

    def _start_screen_shake(self, duration: float, strength: float) -> None:
        if self.screen_shake_time <= 0:
            self.screen_shake_strength = 0.0
        self.screen_shake_time = max(self.screen_shake_time, duration)
        self.screen_shake_strength = max(self.screen_shake_strength, strength)

    def _play_sound(self, cue: str) -> None:
        """Play a short WAV asynchronously so audio never delays input handling."""
        path = Path(__file__).resolve().parent.parent / "assets" / "sounds" / f"{cue}.wav"
        if not path.is_file():
            return
        try:
            import winsound
            winsound.PlaySound(
                str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
        except (ImportError, RuntimeError):
            # Sound is optional on platforms without the Windows audio backend.
            pass

    # ------------------------------------------------------------------
    # Combat feedback and player attacks
    # ------------------------------------------------------------------

    def _spawn_visual_effect(
        self,
        x: float,
        y: float,
        color: str,
        particle_count: int,
        ring_size: float,
        flash_color: str,
        flash_duration: float,
    ) -> None:
        for _ in range(particle_count):
            angle = self.rng.random() * math.tau
            speed = self.rng.uniform(65, 210)
            life = self.rng.uniform(0.45, 0.9)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                color,
                life,
                life,
                self.rng.uniform(2.5, 6.0),
            ))
        self.light_rings.append(LightRing(
            x, y, color,
            life=0.65,
            max_life=0.65,
            start_radius=10,
            end_radius=ring_size,
        ))
        if flash_duration >= self.screen_flash_time:
            self.screen_flash_color = flash_color
            self.screen_flash_time = flash_duration
            self.screen_flash_duration = flash_duration

    def _update_effects(self, dt: float) -> None:
        self.screen_flash_time = max(0.0, self.screen_flash_time - dt)
        self.screen_shake_time = max(0.0, self.screen_shake_time - dt)
        if self.screen_shake_time == 0:
            self.screen_shake_strength = 0.0
        for particle in self.particles[:]:
            particle.life -= dt
            if particle.life <= 0:
                self.particles.remove(particle)
                continue
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vx *= max(0.0, 1.0 - dt * 2.2)
            particle.vy = particle.vy * max(0.0, 1.0 - dt * 2.2) + 25 * dt
        for ring in self.light_rings[:]:
            ring.life -= dt
            if ring.life <= 0:
                self.light_rings.remove(ring)

    def _attack(self) -> None:
        if self.game_over:
            return
        if self.attack_cd:
            return
        self.attack_cd = PLAYER_ATTACK_COOLDOWN
        self.attack_flash = PLAYER_ATTACK_ANIMATION_DURATION
        candidates = [enemy for enemy in self.enemies if self._in_attack_sector(enemy)
                      and not self._line_blocked(self.px, self.py, enemy.x, enemy.y, 5)]
        if not candidates:
            self._play_sound("swing")
            self._say("剣は空を切った。")
            return
        for enemy in candidates:
            self._hit_enemy(enemy)
        self._remove_dead()

    def _in_attack_sector(self, enemy: Enemy) -> bool:
        """Test the enemy circle against the entire filled attack sector."""
        dx, dy = enemy.x - self.px, enemy.y - self.py
        distance = math.hypot(dx, dy)
        angle = math.atan2(dy, dx) - math.atan2(self.facing[1], self.facing[0])
        angle = abs((angle + math.pi) % math.tau - math.pi)
        if angle <= PLAYER_ATTACK_HALF_ANGLE:
            return distance <= PLAYER_ATTACK_RADIUS + enemy.radius
        # Outside the angle, overlap with either radial edge still counts.
        delta = angle - PLAYER_ATTACK_HALF_ANGLE
        along = min(PLAYER_ATTACK_RADIUS, max(0.0, distance * math.cos(delta)))
        separation = math.hypot(distance * math.cos(delta) - along,
                                distance * math.sin(delta))
        return separation <= enemy.radius

    def _hit_enemy(self, enemy: Enemy) -> None:
        """Apply one melee hit to an enemy overlapping the attack sector."""
        skill_damage = {
            "blade": 10,
            "dark": 18,
            "gauntlet": 22,
            "ember": 30,
        }.get(self.skill, 0)
        damage = self.attack + skill_damage
        if self.skill == "lantern" and ("影" in enemy.name or enemy.boss):
            damage += 8
        shield_damage, hp_damage = self._damage_enemy(enemy, damage)
        dx, dy = enemy.x - self.px, enemy.y - self.py
        hit_distance = max(1.0, math.hypot(dx, dy))
        knockback = 12 if enemy.boss else 28
        enemy_x = enemy.x + dx / hit_distance * knockback
        enemy_y = enemy.y + dy / hit_distance * knockback
        if not self._blocked(enemy_x, enemy_y, enemy.radius):
            enemy.x, enemy.y = enemy_x, enemy_y
        self.hit_stop_time = 0.065 if enemy.boss else 0.045
        self._start_screen_shake(0.12, 7 if enemy.boss else 4)
        self._play_sound("hit")
        self._spawn_visual_effect(
            enemy.x, enemy.y, "#ffe39a", 7, 34, "#fff1bf", 0.04,
        )
        if self.skill == "dark":
            self.hp = min(self.max_hp, self.hp + 3)
        elif self.skill == "chalice":
            self.hp = min(self.max_hp, self.hp + 5)
        elif self.skill == "dew":
            self.hp = min(self.max_hp, self.hp + 8)
        damage_messages = []
        if shield_damage:
            damage_messages.append(f"シールドに{shield_damage}")
        if hp_damage:
            damage_messages.append(f"HPに{hp_damage}")
        self._say(f"{enemy.name}へ" + "、".join(damage_messages) + "ダメージ。")
    def _remove_dead(self) -> None:
        defeated = [e for e in self.enemies if e.hp <= 0]
        boss_defeated = any(enemy.boss for enemy in defeated)
        for enemy in defeated:
            self._spawn_visual_effect(
                enemy.x, enemy.y, enemy.color,
                particle_count=38 if enemy.boss else 18,
                ring_size=150 if enemy.boss else 75,
                flash_color="#e7c5ff" if enemy.boss else "#ffb09b",
                flash_duration=0.28 if enemy.boss else 0.1,
            )
            self.enemies.remove(enemy)
            self._say(f"{enemy.name}を倒した。")
        if boss_defeated:
            self.boss_gate_locked = False
            if self.dungeon_number >= 3:
                self._complete_game()
            else:
                self.next_dungeon_timer = 1.0
                self._say("王国の守護者を倒した。次の遺跡へ進む……", 1.0)

    def _select_skill(self, number: str) -> None:
        skill, relic, name = {
            "1": ("blade", "blade", "灰刃"),
            "2": ("lantern", "lantern", "灯火"),
            "3": ("dark", "heart", "黒心"),
            "4": ("chalice", "chalice", "聖杯"),
            "5": ("gauntlet", "gauntlet", "籠手"),
            "6": ("wing", "wing", "翼章"),
            "7": ("ember", "ember", "暁火"),
            "8": ("ward", "ward", "護符"),
            "9": ("dew", "dew", "月雫"),
        }[number]
        if not self._has(relic):
            self._say("その遺物はまだ見つけていない。")
        else:
            self.skill = skill
            self._say(name + "に切り替えた。")

    def _equipped_relic_info(self) -> tuple[str, str, str, str]:
        """Return the HUD label, effect, color, and shortcut of the active relic."""
        return {
            "blade": ("灰刃の欠片", "攻撃ダメージ +10", "#ef6246", "1"),
            "lantern": ("灯火の小瓶", "影・ボスへ +8 / 被ダメージ -4", "#ffd65c", "2"),
            "dark": ("黒い心臓石", "攻撃 +18 / 命中時 HP回復 +3", "#7d269d", "3"),
            "chalice": ("命脈の聖杯", "命中時 HP回復 +5", "#69d6b0", "4"),
            "gauntlet": ("巨人の籠手", "攻撃ダメージ +22", "#d98b52", "5"),
            "wing": ("白銀の翼章", "被ダメージ -7", "#b8d8ef", "6"),
            "ember": ("暁火の結晶", "攻撃ダメージ +30", "#ff765c", "7"),
            "ward": ("古王の護符", "被ダメージ -10", "#9e8bd8", "8"),
            "dew": ("月雫の宝珠", "命中時 HP回復 +8", "#75c8ef", "9"),
            "none": ("未装備", "数字キーで入手済みの遺物を装備", "#777f91", "-")
        }.get(self.skill, (self.skill, "効果不明", "#777f91", "-"))

    def _check_ending(self) -> None:
        if self.next_dungeon_timer > 0:
            return
        boss_alive = any(e.boss for e in self.enemies)
        if not boss_alive and self._distance(self.px, self.py, stage(960), stage(230)) < 80:
            self._complete_game()

    def _complete_game(self) -> None:
        """Finish the run and show the ending after the final boss falls."""
        self.game_over = True
        self.next_dungeon_timer = 0.0
        if self.truth >= 6:
            ending = "真相エンド：灰の夜の真実と自らの罪を受け入れ、王国の記憶を解放した。"
        elif self.truth >= 4:
            ending = "断片エンド：自分が王国崩壊に関わった記憶を取り戻したが、全貌は闇に残った。"
        else:
            ending = "通常エンド：真実を知らぬまま、灰の王国を脱出した。"
        self._say("GAME CLEAR！ " + ending + "  " + self._end_options(), 999)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        self.canvas.begin_frame()
        try:
            self._draw_scene()
        finally:
            self.canvas.end_frame()

    def _draw_scene(self) -> None:
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if self.ui_mode == "title":
            self._draw_title_screen(width, height)
            return
        if self.ui_mode == "help":
            self._draw_help_screen(width, height)
            return
        cam_x = min(max(self.px - width / 2, 0), WORLD_SIZE - width)
        cam_y = min(max(self.py - height / 2, 0), WORLD_SIZE - height)
        if self.screen_shake_time > 0:
            cam_x += self.rng.uniform(-self.screen_shake_strength, self.screen_shake_strength)
            cam_y += self.rng.uniform(-self.screen_shake_strength, self.screen_shake_strength)
        sx, sy = lambda x: x - cam_x, lambda y: y - cam_y

        self.canvas.create_rectangle(0, 0, width, height, fill="#303541", outline="")
        floor_texture = self.environment_textures.get("floor")
        if floor_texture is not None:
            self.canvas.create_image(
                -(cam_x % 96), -(cam_y % 96),
                image=self._floor_texture_for_view(width, height), anchor="nw",
            )
        for x in range(max(0, math.ceil(cam_x / 96) * 96), min(WORLD_SIZE, math.ceil((cam_x + width) / 96) * 96), 96):
            self.canvas.create_line(sx(x), sy(0), sx(x), sy(WORLD_SIZE), fill="#3b4250")
        for y in range(max(0, math.ceil(cam_y / 96) * 96), min(WORLD_SIZE, math.ceil((cam_y + height) / 96) * 96), 96):
            self.canvas.create_line(sx(0), sy(y), sx(WORLD_SIZE), sy(y), fill="#3b4250")
        for wx, wy, ww, wh in self.walls:
            if not self._rect_in_view(sx(wx), sy(wy), ww, wh, width, height, 2):
                continue
            self.canvas.create_rectangle(sx(wx), sy(wy), sx(wx + ww), sy(wy + wh), fill="#626978", outline="#929aaa", width=2)
            wall_texture = self.environment_textures.get("wall")
            if wall_texture is not None and not (
                sx(wx + ww) < 0 or sx(wx) > width or sy(wy + wh) < 0 or sy(wy) > height
            ):
                self.canvas.create_image(
                    sx(wx), sy(wy),
                    image=self._wall_texture_for_size(math.ceil(ww), math.ceil(wh)),
                    anchor="nw",
                )
                self.canvas.create_rectangle(
                    sx(wx), sy(wy), sx(wx + ww), sy(wy + wh),
                    fill="", outline="#929aaa", width=2,
                )

        self._draw_landmark("shrine", sx(stage(960)), sy(stage(1660)), 34, "#4b80ad", "祠")
        exit_label = "階段" if self.dungeon_number in (1, 2) else "出口"
        self._draw_landmark(
            "stairs" if self.dungeon_number in (1, 2) else "exit",
            sx(stage(960)), sy(stage(230)), 38, "#208c70", exit_label,
        )
        self._draw_marker(sx(stage(1110)), sy(stage(560)), 23, "#ad8b41" if self.inscription_found else "#292932", "碑文")
        if not self.door_open or self.boss_gate_locked:
            self.canvas.create_rectangle(sx(stage(760)), sy(stage(615)), sx(stage(1160)), sy(stage(685)), fill="#8f35ad", outline="#e3aaef", width=3)
            gate_label = "戦闘封鎖" if self.boss_gate_locked else "封印扉"
            self.canvas.create_text(sx(stage(960)), sy(stage(650)), text=gate_label, fill="white")

        for projectile in self.projectiles:
            x, y = sx(projectile.x), sy(projectile.y)
            radius = projectile.radius
            projectile_sprite = self._boss_projectile_sprite(projectile)
            if projectile_sprite is not None:
                self.canvas.create_image(x, y, image=projectile_sprite)
            elif projectile.style in {"lance", "wave"}:
                angle = math.atan2(projectile.vy, projectile.vx)
                ux, uy = math.cos(angle), math.sin(angle)
                px, py = -uy, ux
                length = radius * (2.2 if projectile.style == "lance" else 1.4)
                self.canvas.create_polygon(
                    x + ux * length, y + uy * length,
                    x + px * radius, y + py * radius,
                    x - ux * length, y - uy * length,
                    x - px * radius, y - py * radius,
                    fill=projectile.color, outline=projectile.outline, width=2,
                )
            else:
                self.canvas.create_oval(
                    x - radius, y - radius, x + radius, y + radius,
                    fill=projectile.color, outline=projectile.outline,
                    width=3 if projectile.style == "ring" else 2,
                )

        for bolt in self.ally_bolts:
            x, y = sx(bolt.x), sy(bolt.y)
            self.canvas.create_oval(
                x - 7, y - 7, x + 7, y + 7,
                fill="#70dfff", outline="#e0fbff", width=2,
            )
            self.canvas.create_oval(
                x - 12, y - 12, x + 12, y + 12,
                outline="#70dfff", width=1, dash=(3, 3),
            )

        for relic in self.relics:
            if not relic.collected and self._rect_in_view(
                sx(relic.x), sy(relic.y), 0, 0, width, height, 100,
            ):
                self._draw_relic(relic, sx(relic.x), sy(relic.y))
        if self.ally_candidate_name:
            color, _ = ALLY_STYLES.get(
                self.ally_candidate_name, ("#e7b94c", self.ally_candidate_name),
            )
            self._draw_ally(
                self.ally_candidate_name, sx(self.ally_candidate_x), sy(self.ally_candidate_y),
            )
        for enemy in self.enemies:
            # Keep windup indicators: their aim lines can cross the viewport
            # even when the attacking enemy is outside it.
            if enemy.windup <= 0 and not self._rect_in_view(
                sx(enemy.x), sy(enemy.y), 0, 0, width, height,
                300 if enemy.boss else 160,
            ):
                continue
            warning_on = enemy.windup > 0 and int(enemy.windup * 14) % 2 == 0
            enemy_color = "#ffd36a" if warning_on else enemy.color
            enemy_sprite = self._boss_sprite_for_attack(enemy) if enemy.boss else self._enemy_sprite(enemy)
            if enemy_sprite is not None:
                self.canvas.create_image(
                    sx(enemy.x), sy(enemy.y) + (enemy.radius if enemy.boss else self._enemy_sprite_offset()),
                    image=enemy_sprite, anchor="s",
                )
            else:
                self._draw_actor(sx(enemy.x), sy(enemy.y), enemy.radius, enemy_color, enemy.name)
            if enemy.windup > 0:
                progress = 1.0 - enemy.windup / max(0.001, enemy.windup_max)
                warning_colors = {
                    "melee": "#ff554f",
                    "boss_fan": "#b45cff",
                    "boss_ring": "#ff5bab",
                    "boss_lance": "#48e1f2",
                    "boss_spiral": "#ff943d",
                    "boss_wave": "#ffe05b",
                }
                warning_color = warning_colors.get(enemy.pending_attack, "#d783ff")
                warning_radius = enemy.radius + (55 if enemy.pending_attack == "melee" else 32)
                self.canvas.create_oval(
                    sx(enemy.x) - warning_radius,
                    sy(enemy.y) - warning_radius,
                    sx(enemy.x) + warning_radius,
                    sy(enemy.y) + warning_radius,
                    outline=warning_color,
                    width=max(2, round(5 * progress)),
                    dash=(5, 3),
                )
                if enemy.pending_attack in {
                    "ranged", "boss_fan", "boss_lance", "boss_wave",
                }:
                    self.canvas.create_line(
                        sx(enemy.x), sy(enemy.y),
                        sx(enemy.aim_x), sy(enemy.aim_y),
                        fill=warning_color,
                        width=2 if enemy.pending_attack == "ranged" else 4,
                        dash=(8, 6),
                    )
                elif enemy.pending_attack in {"boss_ring", "boss_spiral"}:
                    ring_radius = enemy.radius + 45 + 55 * progress
                    self.canvas.create_oval(
                        sx(enemy.x) - ring_radius,
                        sy(enemy.y) - ring_radius,
                        sx(enemy.x) + ring_radius,
                        sy(enemy.y) + ring_radius,
                        outline=warning_color,
                        width=4,
                        dash=(4, 4),
                    )
                    if enemy.pending_attack == "boss_spiral":
                        inner_radius = ring_radius * 0.62
                        self.canvas.create_oval(
                            sx(enemy.x) - inner_radius,
                            sy(enemy.y) - inner_radius,
                            sx(enemy.x) + inner_radius,
                            sy(enemy.y) + inner_radius,
                            outline="#ffd09a", width=3, dash=(3, 5),
                        )
            bar = max(0, enemy.hp) / max(1, enemy.max_hp)
            self.canvas.create_rectangle(sx(enemy.x) - 28, sy(enemy.y) - enemy.radius - 13, sx(enemy.x) + 28, sy(enemy.y) - enemy.radius - 8, fill="#351519", outline="")
            self.canvas.create_rectangle(sx(enemy.x) - 28, sy(enemy.y) - enemy.radius - 13, sx(enemy.x) - 28 + 56 * bar, sy(enemy.y) - enemy.radius - 8, fill="#d14848", outline="")
            if enemy.max_shield > 0:
                shield_ratio = enemy.shield / enemy.max_shield
                shield_top = sy(enemy.y) - enemy.radius - 21
                self.canvas.create_rectangle(
                    sx(enemy.x) - 28, shield_top,
                    sx(enemy.x) + 28, shield_top + 5,
                    fill="#16263a", outline="",
                )
                self.canvas.create_rectangle(
                    sx(enemy.x) - 28, shield_top,
                    sx(enemy.x) - 28 + 56 * shield_ratio, shield_top + 5,
                    fill="#4ab8ed", outline="",
                )
        if self.has_ally:
            for ally_name in sorted(self.companions):
                companion = self.companions[ally_name]
                color, label = ALLY_STYLES.get(ally_name, ("#e7b94c", ally_name))
                self._draw_ally(ally_name, sx(companion.x), sy(companion.y), companion)
                cooldown_ratio = (
                    companion.cooldown / companion.cooldown_max
                    if companion.cooldown_max > 0 else 0.0
                )
                bar_left = sx(companion.x) - 22
                bar_top = sy(companion.y) - 70
                self.canvas.create_rectangle(
                    bar_left, bar_top, bar_left + 44, bar_top + 5,
                    fill="#252735", outline="#e7d58a",
                )
                self.canvas.create_rectangle(
                    bar_left, bar_top,
                    bar_left + 44 * (1.0 - cooldown_ratio), bar_top + 5,
                    fill="#70dfff", outline="",
                )

        player_color = "#74a7e8" if not self.dodge_time else "#d7efff"
        player_visible = (
            self.hurt_invincible <= 0
            or int(self.hurt_invincible * 24) % 2 == 0
        )
        player_x, player_y = sx(self.px), sy(self.py)
        # Keep identity markers visible while the hurt sprite blinks.
        self.canvas.create_oval(
            player_x - 28, player_y + 1, player_x + 28, player_y + 23,
            fill="#142d3b", outline="#63e6ff", width=3,
        )
        self.canvas.create_oval(
            player_x - 22, player_y + 5, player_x + 22, player_y + 19,
            outline="#e5fbff", width=1,
        )
        if player_visible:
            player_sprite = self._player_sprite()
            if player_sprite is not None:
                self.canvas.create_image(
                    sx(self.px), sy(self.py) + self._player_sprite_offset(),
                    image=player_sprite, anchor="s",
                )
            else:
                self._draw_actor(sx(self.px), sy(self.py), PLAYER_RADIUS, player_color, "")
        fx, fy = self.facing
        if not self.player_sprites:
            self.canvas.create_line(sx(self.px), sy(self.py), sx(self.px + fx * 42), sy(self.py + fy * 42), fill="#e8edf4", width=5)
        if self.attack_flash:
            attack_angle = -math.degrees(math.atan2(fy, fx))
            self.canvas.create_arc(
                sx(self.px) - PLAYER_ATTACK_RADIUS, sy(self.py) - PLAYER_ATTACK_RADIUS,
                sx(self.px) + PLAYER_ATTACK_RADIUS, sy(self.py) + PLAYER_ATTACK_RADIUS,
                start=attack_angle - math.degrees(PLAYER_ATTACK_HALF_ANGLE),
                extent=math.degrees(PLAYER_ATTACK_HALF_ANGLE) * 2,
                style="arc", outline="#fff0a6", width=6,
            )
        self._draw_effects(sx, sy, width, height)
        if self.player_shield > 0:
            self.canvas.create_oval(
                player_x - 37, player_y - 65, player_x + 37, player_y + 24,
                outline="#70dfff", width=3,
            )
        self._draw_role_label(player_x, player_y - 98, "プレイヤー", "#63e6ff")
        self.canvas.create_polygon(
            player_x - 6, player_y - 84, player_x + 6, player_y - 84,
            player_x, player_y - 77, fill="#63e6ff", outline="#101722",
        )
        self._draw_ui(width, height, sx(self.px), sy(self.py))
        self._draw_minimap(width, height)
        if self.ui_mode == "paused":
            self._draw_pause_menu(width, height)

    def _draw_title_screen(self, width: int, height: int) -> None:
        self.canvas.create_rectangle(0, 0, width, height, fill="#080a10", outline="")
        for index in range(9):
            margin = index * 34
            self.canvas.create_rectangle(
                margin, margin, width - margin, height - margin,
                outline="#171c29" if index % 2 else "#202437",
            )
        self.canvas.create_text(
            width / 2, height * 0.24,
            text="灰の王国と記憶の遺物",
            fill="#e9dfc5", font=("Yu Gothic UI", 31, "bold"),
        )
        self.canvas.create_text(
            width / 2, height * 0.32,
            text="DARK RUINS",
            fill="#786f83", font=("Consolas", 14),
        )
        self._draw_menu_options(
            width, height, ("ゲーム開始", "操作説明", "終了"), height * 0.48,
        )
        self.canvas.create_text(
            width / 2, height - 38,
            text="↑↓ / W S：選択　 Enter / Space：決定",
            fill="#777f91", font=("Yu Gothic UI", 10),
        )

    def _draw_help_screen(self, width: int, height: int) -> None:
        self.canvas.create_rectangle(0, 0, width, height, fill="#0b0e15", outline="")
        self.canvas.create_text(
            width / 2, 70, text="操作説明",
            fill="#f0e5c8", font=("Yu Gothic UI", 26, "bold"),
        )
        controls = (
            "【基本操作】\n"
            "移動　　　　WASD / 矢印キー\n"
            "向き　　　　マウスを動かした方向へ向く\n"
            "攻撃　　　　左クリック / F / Enter（向いている敵を攻撃）\n"
            "回避　　　　Space（カーソル方向へ回避し、短時間無敵）\n"
            "調べる　　　E（祠や隠された碑文の近くで使用）\n"
            "遺物切替　　1：灰刃　2：灯火　3：黒心\n"
            "　　　　　　4：聖杯　5：籠手　6：翼章\n"
            "　　　　　　7：暁火　8：護符　9：月雫\n"
            "ポーズ　　　P / Esc\n\n"
            "【冒険の目的】\n"
            "遺物を集めて封印を解き、仲間のミラと守護者を倒す。\n"
            "守護者を倒した後、部屋上側の出口へ向かう。\n"
            "遺物・仲間・碑文で真相度を集めると結末が変化する。\n"
            "ミラは自動で支援弾を撃ち、HP低下時には回復してくれる。"
        )
        self.canvas.create_rectangle(
            width / 2 - 330, 120, width / 2 + 330, height - 100,
            fill="#111722", outline="#5c6170", width=2,
        )
        self.canvas.create_text(
            width / 2, 160, anchor="n", text=controls,
            fill="#d7dce7", font=("Yu Gothic UI", 12),
            justify="left",
        )
        self.canvas.create_text(
            width / 2, height - 54,
            text="Esc / Backspace / Enter：戻る",
            fill="#9aa4b8", font=("Yu Gothic UI", 11),
        )

    def _draw_pause_menu(self, width: int, height: int) -> None:
        self.canvas.create_rectangle(
            0, 0, width, height, fill="#05070b", outline="", stipple="gray50",
        )
        panel_left, panel_right = width / 2 - 230, width / 2 + 230
        self.canvas.create_rectangle(
            panel_left, 85, panel_right, height - 85,
            fill="#0b0e15", outline="#777081", width=3,
        )
        self.canvas.create_text(
            width / 2, 135, text="PAUSE",
            fill="#eee5d1", font=("Consolas", 27, "bold"),
        )
        self._draw_menu_options(
            width, height,
            ("ゲームに戻る", "操作説明", "タイトルへ戻る", "終了"),
            205,
        )

    def _draw_menu_options(
        self, width: int, height: int, options: tuple[str, ...], start_y: float,
    ) -> None:
        for index, option in enumerate(options):
            y = start_y + index * 58
            selected = index == self.menu_index
            if selected:
                self.canvas.create_rectangle(
                    width / 2 - 170, y - 21, width / 2 + 170, y + 21,
                    fill="#31263b", outline="#d7a7ef", width=2,
                )
            self.canvas.create_text(
                width / 2, y,
                text=("◆  " if selected else "　　") + option,
                fill="#fff0cc" if selected else "#adb3c0",
                font=("Yu Gothic UI", 14, "bold" if selected else "normal"),
            )

    def _draw_actor(self, x: float, y: float, radius: float, color: str, label: str) -> None:
        self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=color, outline="#e7e2d8", width=2)
        if label:
            self.canvas.create_text(x, y + radius + 13, text=label, fill="#ddd9ce", font=("Yu Gothic UI", 9))

    def _draw_landmark(self, key: str, x: float, y: float, radius: float, color: str, label: str) -> None:
        sprite = self.landmark_sprites.get(key)
        if sprite is None:
            self._draw_marker(x, y, radius, color, label)
            return
        # Source frames share a ground anchor at (64, 120).
        self.canvas.create_image(x, y + 8, image=sprite, anchor="s")
        self.canvas.create_text(
            x, y + 20, text=label, fill="#e7dfca", font=("Yu Gothic UI", 10, "bold"),
        )

    def _draw_marker(self, x: float, y: float, radius: float, color: str, label: str) -> None:
        self.canvas.create_polygon(x, y - radius, x + radius, y, x, y + radius, x - radius, y, fill=color, outline="#eee3bd", width=2)
        self.canvas.create_text(x, y + radius + 13, text=label, fill="#e7dfca", font=("Yu Gothic UI", 9))

    def _draw_effects(self, sx, sy, width: int, height: int) -> None:
        for ring in self.light_rings:
            progress = 1.0 - ring.life / ring.max_life
            radius = ring.start_radius + (ring.end_radius - ring.start_radius) * progress
            line_width = max(1, round(5 * (1.0 - progress)))
            x, y = sx(ring.x), sy(ring.y)
            self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                outline=ring.color, width=line_width,
            )
            if progress < 0.55:
                inner = radius * 0.68
                self.canvas.create_oval(
                    x - inner, y - inner, x + inner, y + inner,
                    outline="#ffffff", width=1,
                )

        for particle in self.particles:
            life_ratio = particle.life / particle.max_life
            size = max(1.0, particle.size * life_ratio)
            x, y = sx(particle.x), sy(particle.y)
            stipple = "" if life_ratio > 0.55 else "gray50"
            self.canvas.create_oval(
                x - size, y - size, x + size, y + size,
                fill=particle.color, outline="",
                stipple=stipple,
            )

        if self.screen_flash_time > 0:
            ratio = self.screen_flash_time / max(0.001, self.screen_flash_duration)
            stipple = "gray25" if ratio > 0.55 else "gray12"
            self.canvas.create_rectangle(
                0, 0, width, height,
                fill=self.screen_flash_color, outline="",
                stipple=stipple,
            )

    def _draw_ui(self, width: int, height: int, player_x: float, player_y: float) -> None:
        relic_name, relic_effect, relic_color, relic_key = self._equipped_relic_info()
        # Move the HUD away when the player is forced into the top-left corner
        # by the world boundary. This prevents the sprite and HP bar overlapping.
        hud_bottom = player_x < 450 and player_y < 205
        offset_y = height - 208 if hud_bottom else 0
        self.canvas.create_rectangle(18, 18 + offset_y, 430, 190 + offset_y, fill="#090b11", outline="#454a58", width=2)
        self.canvas.create_rectangle(34, 38 + offset_y, 254, 59 + offset_y, fill="#30141a", outline="")
        self.canvas.create_rectangle(34, 38 + offset_y, 34 + 220 * self.hp / self.max_hp, 59 + offset_y, fill="#b52c3b", outline="")
        self.canvas.create_text(144, 48 + offset_y, text=f"HP {self.hp}/{self.max_hp}", fill="white", font=("Yu Gothic UI", 11, "bold"))
        self.canvas.create_text(270, 48 + offset_y, anchor="w", text=f"攻撃 {self.attack}   真相 {self.truth}", fill="#d8dce7", font=("Yu Gothic UI", 11))
        self.canvas.create_rectangle(30, 70 + offset_y, 418, 122 + offset_y, fill="#151824", outline=relic_color, width=2)
        equipped_sprite = self.relic_sprites.get(self.skill)
        if equipped_sprite is None:
            self.canvas.create_polygon(46, 82 + offset_y, 57, 96 + offset_y, 46, 110 + offset_y, 35, 96 + offset_y, fill=relic_color, outline="#fff4cf")
        else:
            self.canvas.create_image(46, 96 + offset_y, image=equipped_sprite)
        self.canvas.create_text(
            68, 83 + offset_y, anchor="w",
            text=f"装備中  [{relic_key}] {relic_name}",
            fill=relic_color, font=("Yu Gothic UI", 12, "bold"),
        )
        self.canvas.create_text(
            68, 108 + offset_y, anchor="w", text=relic_effect,
            fill="#e8e2d5", font=("Yu Gothic UI", 10),
        )
        dodge_status = "READY" if self.dodge_cd == 0 else f"{self.dodge_cd:.1f}秒"
        shield_capacity = self._player_shield_capacity()
        shield_ratio = min(1.0, max(0.0, self.player_shield / max(1, shield_capacity)))
        self.canvas.create_rectangle(
            268, 129 + offset_y, 418, 151 + offset_y,
            fill="#142333", outline="#70dfff", width=1,
        )
        if shield_ratio > 0:
            self.canvas.create_rectangle(
                269, 130 + offset_y, 269 + 148 * shield_ratio, 150 + offset_y,
                fill="#237491", outline="",
            )
        self.canvas.create_text(
            343, 140 + offset_y,
            text=f"シールド {self.player_shield}/{shield_capacity}",
            fill="#e5fbff", font=("Yu Gothic UI", 10, "bold"),
        )
        self.canvas.create_text(
            34, 140 + offset_y, anchor="w", text=f"回避クールタイム: {dodge_status}",
            fill="#8de7ff" if self.dodge_cd == 0 else "#c2a7db",
            font=("Yu Gothic UI", 10, "bold"),
        )
        objective = (
            f"第{self.dungeon_number}遺跡：守護者を倒す"
            if self.door_open
            else f"第{self.dungeon_number}遺跡：灯火の小瓶を探して封印を解く"
        )
        self.canvas.create_text(34, 168 + offset_y, anchor="w", text=objective, fill="#9fc3e8", font=("Yu Gothic UI", 10))
        if time.perf_counter() < self.message_until:
            message_top = 24 if hud_bottom else height - 72
            self.canvas.create_rectangle(180, message_top, width - 180, message_top + 48, fill="#090b11", outline="#72664d", width=2)
            self.canvas.create_text(width / 2, message_top + 24, text=self.message, fill="#f2d992", font=("Yu Gothic UI", 13, "bold"))

    def _draw_minimap(self, width: int, height: int) -> None:
        size = min(210, max(150, height - 120))
        left, top = width - size - 18, 52
        scale = size / WORLD_SIZE
        mx = lambda x: left + x * scale
        my = lambda y: top + y * scale

        self.canvas.create_rectangle(
            left - 5, top - 5, left + size + 5, top + size + 24,
            fill="#080a0f", outline="#596171", width=2,
        )
        for wx, wy, ww, wh in self.walls:
            self.canvas.create_rectangle(
                mx(wx), my(wy), mx(wx + ww), my(wy + wh),
                fill="#555b68", outline="",
            )
        if not self.door_open or self.boss_gate_locked:
            self.canvas.create_rectangle(
                mx(stage(760)), my(stage(615)),
                mx(stage(1160)), my(stage(685)),
                fill="#b34bcf", outline="",
            )

        for relic in self.relics:
            if not relic.collected:
                self.canvas.create_oval(
                    mx(relic.x) - 3, my(relic.y) - 3,
                    mx(relic.x) + 3, my(relic.y) + 3,
                    fill=relic.color, outline="",
                )
        for enemy in self.enemies:
            radius = 4 if enemy.boss else 2
            self.canvas.create_oval(
                mx(enemy.x) - radius, my(enemy.y) - radius,
                mx(enemy.x) + radius, my(enemy.y) + radius,
                fill="#ee5b55", outline="",
            )

        self.canvas.create_oval(
            mx(stage(960)) - 3, my(stage(1660)) - 3,
            mx(stage(960)) + 3, my(stage(1660)) + 3,
            fill="#65b8f2", outline="",
        )
        self.canvas.create_oval(
            mx(self.px) - 4, my(self.py) - 4,
            mx(self.px) + 4, my(self.py) + 4,
            fill="#ffffff", outline="#74a7e8",
        )

        cam_x = min(max(self.px - width / 2, 0), WORLD_SIZE - width)
        cam_y = min(max(self.py - height / 2, 0), WORLD_SIZE - height)
        self.canvas.create_rectangle(
            mx(cam_x), my(cam_y), mx(cam_x + width), my(cam_y + height),
            outline="#9fc3e8",
        )
        self.canvas.create_text(
            left, top + size + 13, anchor="w",
            text=f"MAP  seed:{self.stage_seed:06d}",
            fill="#aeb5c4", font=("Consolas", 8),
        )

    # ------------------------------------------------------------------
    # Small shared helpers
    # ------------------------------------------------------------------

    def _say(self, message: str, seconds: float = 3.0) -> None:
        self.message = message
        self.message_until = time.perf_counter() + seconds

    def _has(self, key: str) -> bool:
        return any(r.key == key and r.collected for r in self.relics)

    @staticmethod
    def _rect_in_view(
        x: float, y: float, w: float, h: float,
        view_width: int, view_height: int, margin: float = 0,
    ) -> bool:
        """Include edge-overlapping sprites and outlines when culling draws."""
        return (
            x + w >= -margin and y + h >= -margin
            and x <= view_width + margin and y <= view_height + margin
        )

    @staticmethod
    def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
        return math.hypot(x2 - x1, y2 - y1)

    def run(self) -> None:
        self.root.mainloop()

    def verify_startup(self) -> None:
        """Exercise initialization and runtime sprite loading without showing a window."""
        self.root.update_idletasks()
        if len(self.player_sprites) != 12:
            raise RuntimeError(f"player sprite groups: {len(self.player_sprites)}, expected 12")
        if len(self.enemy_sprites) != 3:
            raise RuntimeError(f"enemy sprite sets: {len(self.enemy_sprites)}, expected 3")
        if set(self.ally_sprites) != set(ALLY_STYLES):
            raise RuntimeError("one or more companion sprites failed to load")
        if self.ally_animations and set(self.ally_animations) != set(ALLY_STYLES):
            raise RuntimeError("one or more companion animations failed to load")
        if set(self.relic_sprites) != set(RELIC_KEYS):
            raise RuntimeError("one or more relic sprites failed to load")
        if set(self.boss_projectile_sprites) != set(BOSS_PROJECTILE_STYLES):
            raise RuntimeError("one or more boss projectile sprite sets failed to load")
        if any(
            len(frames) != BOSS_PROJECTILE_DIRECTIONS
            for frames in self.boss_projectile_sprites.values()
        ):
            raise RuntimeError("a boss projectile sprite set is incomplete")
        if any(len(frames) != 4 for frames in self.player_sprites.values()):
            raise RuntimeError("a player animation does not contain four frames")
        if any(
            len(frames) != 4
            for enemy in self.enemy_sprites.values()
            for frames in enemy.values()
        ):
            raise RuntimeError("an enemy animation does not contain four frames")
        start_x = self.px
        self.keys = {"d"}
        self._update(1 / 60)
        if self.px <= start_x:
            raise RuntimeError("movement input was not applied within one update frame")
        self.keys.clear()
        self.ui_mode = "playing"
        self._draw()
        self._draw_ui(WIDTH, HEIGHT, 24, 24)
        self.root.destroy()


def main() -> None:
    if "--smoke-test" in sys.argv:
        class DummyWidget:
            def __init__(self, *args, **kwargs) -> None:
                self.tk = self

            def call(self, *args, **kwargs):
                return None

            def __getattr__(self, _name):
                return lambda *args, **kwargs: None

            def winfo_width(self) -> int:
                return WIDTH

            def winfo_height(self) -> int:
                return HEIGHT

            def zoom(self, *_args):
                return self

            def subsample(self, *_args):
                return self

        global FrameCanvas
        original_widgets = tk.Tk, tk.Canvas, tk.PhotoImage, FrameCanvas
        try:
            tk.Tk = tk.Canvas = tk.PhotoImage = FrameCanvas = DummyWidget
            game = DarkRuins2D(hidden=True)
            game.verify_startup()
        finally:
            tk.Tk, tk.Canvas, tk.PhotoImage, FrameCanvas = original_widgets
        print("Headless smoke test passed: startup, sprites, rendering, HUD, and input movement.")
        return
    DarkRuins2D().run()


if __name__ == "__main__":
    main()
