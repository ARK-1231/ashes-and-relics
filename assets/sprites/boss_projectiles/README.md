# Boss projectile sprites

The game loads five projectile styles with sixteen pre-rotated 48 x 48 frames
per style. Direction `00` points right; subsequent frames rotate clockwise in
22.5-degree steps. The renderer selects the nearest frame from projectile
velocity and falls back to the original Canvas shape if a style is unavailable.

Run `tools/prepare_boss_projectiles.ps1` to rebuild these 80 runtime frames from
the generated transparent originals in `../boss_projectiles_source/`.

## Generation prompt set

Each style was generated separately with the built-in image generation tool as
one isolated, transparent, centered boss projectile for a top-down dark-fantasy
RPG. Shared constraints requested crisp pixel-art-like effects readable at 20 to
36 pixels, generous padding, and no character, scenery, text, frame, watermark,
or additional projectile.

- `fan`: right-facing violet crystalline arcane shard.
- `ring`: radial magenta orb with a thin broken halo.
- `lance`: right-facing narrow cyan magical spearhead.
- `spiral`: radial orange spiral-fire pinwheel.
- `wave`: right-facing compact golden shockwave wedge.
