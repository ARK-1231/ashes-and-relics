# Sprite assets

## Player basic sheet

- File: `player/player_basic_sheet.png`
- Canvas: 1536 x 1024 px
- Generated layout: 11 columns x 4 rows
- Runtime crop: 140 x 216 px, scaled to 47 x 72 px
- Rows: down, left, right, up
- Columns 1-4: idle
- Columns 5-8: walk
- Columns 9-11: sword attack; the middle attack pose is repeated at runtime

The generated source is a visual draft. Before replacing it, keep the same canvas
and cell layout. `player_basic_sheet_aligned.png` is the runtime copy with its
checker background converted to alpha transparency. Direction-specific drawing
offsets keep the feet aligned with the player's collision position.
The generated poses are hand-spaced rather than evenly gridded, so the loader uses
measured pose centers and row starts instead of dividing the sheet uniformly.

## Runtime frames v2

- Directory: `player/frames_v2/`
- Format: alpha-transparent PNG
- Frame size: exactly 96 x 96 px
- Direction order: `up`, `down`, `left`, `right`
- Animations: `idle`, `walk`, `attack`; four frames each
- Foot contact point: `(48, 88)`
- Transparent safety margin: 8 px
- Runtime display size: 48 x 48 px

The game loads these individual normalized frames. The older sheet files are kept
only as source artwork and are no longer sliced at runtime.

## Newly produced player basic set (v3)

- Source sheets: `player/source_v3/idle_sheet.png`, `walk_sheet.png`,
  `attack_sheet.png`
- Runtime frames: `player/frames_v3/`
- Format: genuine alpha-transparent PNG
- Frame size: exactly 96 x 96 px
- Direction order: `up`, `down`, `left`, `right`
- Animations: `idle`, `walk`, `attack`; four frames each (48 total)
- Foot contact point: `(48, 88)`
- Character and sword bounds: inside `(8, 8)` through `(87, 87)`
- Runtime display size: 96 x 96 px (native resolution; no resampling)

All v3 frames were created from the new animation sheets and validated for canvas
size, alpha transparency, and the required transparent safety margin. The game now
loads v3 directly; v2 remains only as a rollback asset.
All directions are loaded from their native 96 x 96 frames without runtime
resampling or mirroring, preventing clipping and preserving the source quality.

## Size-corrected player set (v4)

- Runtime frames: `player/frames_v4/`
- Frame and display size: 96 x 96 px
- The `up`, `down`, and `right` frames are unchanged v3 artwork.
- The `left` frames are pre-rendered horizontal mirrors of the matching `right`
  frames, keeping both horizontal directions exactly the same apparent size.

V4 provides the size-matched source frames used to build v5. Mirroring is performed
in the asset itself instead of at runtime, so the left-facing character remains
sharp and cannot be clipped by a negative Tk image scale.

## Reduced player set (v5)

- Runtime frames: `player/frames_v5/`
- Frame and display size: 84 x 84 px
- High-quality bicubic reduction from v4
- Left and right silhouettes remain the same size

The game loads v5 directly. Pre-rendering the smaller frames avoids Tkinter's
coarse integer resampling while making the player slightly less dominant on screen.

## Regular enemy basic sets

- Source sheets: `enemies/source_v1/`
- Runtime frames: `enemies/frames_v1/`
- Enemies: `ash_soldier`, `ruined_knight`, `wandering_shadow`
- Format: alpha-transparent PNG, exactly 96 x 96 px
- Direction order: `up`, `down`, `left`, `right`
- Animations: `idle`, `walk`, `attack`; four frames each
- Total: 144 frames
- Foot/hover contact point: `(48, 88)`
- Character, weapon, and spell bounds: inside `(8, 8)` through `(87, 87)`

The game selects direction from the enemy-to-player vector and selects idle, walk,
or attack from the current enemy AI state. Boss rendering is unchanged.

### Alignment correction (v2)

The game now loads `enemies/frames_v2/`. Unlike v1, v2 never recenters or rescales
individual opaque bounds. Every source grid cell uses the same crop origin and the
same scale, preserving the authored body and foot position between animation frames.
The v1 files remain available only as rollback assets. Regular enemies are displayed
at their native 96 x 96 px size so their armor, silhouette, and attack poses remain
readable during play.

### Per-frame foot alignment (v3)

The game now loads `enemies/frames_v3/`. For every frame, the alignment process
detects the lowest opaque point inside the central body region, excluding most
sideways weapon and spell pixels, and maps that foot/hover point to `(48, 84)`.
All enemies keep a common scale. At runtime the frame uses its south edge plus the
12 px transparent bottom margin so the authored foot/hover point `(48, 84)` stays
on the enemy's collision position. This prevents the image from appearing shifted
down and keeps animation frames on the same world-space reference point.

### Adjacent-frame cleanup (v4)

The game now loads `enemies/frames_v4/`. Connected-component cleanup keeps the
central enemy body and its connected weapon while removing detached pixels and
partial characters that leaked in from neighboring source-sheet cells. This avoids
the appearance of a second enemy during walk and attack animation.

### Missing-body repair (v5)

The game loads `enemies/frames_v5/`. V5 keeps the cleaned v4 artwork and replaces
six frames whose central body was missing with their intact v2 counterparts. The
runtime set contains 144 non-empty 96 x 96 PNG files. Run
`python tools/validate_sprites.py` to check dimensions, alpha content, central enemy
body coverage, player left/right parity, and UTF-8 Python sources.

### Ruined-knight attack restoration (v6)

The game loads `enemies/frames_v6/`. Its upward ruined-knight attack now contains
four distinct anticipation, wind-up, swing, and recovery poses derived from the
generated sheet in `enemies/source_v2/`. All other enemy frames are unchanged from
v5. The new frames retain the 96 x 96 canvas and common foot baseline.

### Character outlines

The incomplete outlined `player/frames_v6/` experiment was removed because the
game uses the complete `player/frames_v5/` set. The matching `enemies/frames_v7/`
experiment is empty and is not used at runtime.

## Generation prompt summary

Dark-fantasy ash-blue armored swordsman, orthographic top-down three-quarter view,
four directional rows, and idle/walk/sword-attack animation groups.
