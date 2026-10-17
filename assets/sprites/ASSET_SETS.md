# Sprite set inventory

## Active runtime sets

- `player/frames_v5/`: 48 player frames, 84 x 84 pixels.
- `enemies/frames_v6/`: 144 regular-enemy frames, 96 x 96 pixels.

These complete sets were restored byte-for-byte from
`archive/superseded_assets_2026-08-29.zip`. The incomplete experimental
`player/frames_v6/` set was removed because it was not used at runtime;
`enemies/frames_v7/` remains empty. The restored artwork is the earlier version
without the added outlines.

## Source and rollback sets

- `player/source_v3/`: authored player animation sheets.
- `player/player_basic_sheet*.png`: legacy sheet artwork retained for reference.
- `enemies/source_v1/`: authored enemy source sheets.
- `archive/legacy_sprite_sets_2026-08-29.zip`: compressed archive of the oldest
  player and enemy frame sets. The unpacked legacy frame directories were removed
  after the archive checksum was verified.
- `archive/superseded_assets_2026-08-29.zip`: archived non-outlined player and
  enemy frames plus the full-size environment and ruined-knight generated sources.
  Their unpacked copies were removed after checksum verification.

Do not add another numbered runtime directory without updating
`src/dark_ruins_rpg.py`, `README.md`, and `tools/validate_sprites.py` together.
Run `python tools/validate_sprites.py` after every sprite change.
