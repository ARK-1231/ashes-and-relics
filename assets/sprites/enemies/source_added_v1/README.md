# Added enemy assets

Generated with the built-in image_gen tool. Original transparent sheets are kept here.
The existing frames_v6 assets are unchanged.

Prompt set / production specification:

- ash_charger: gritty dark-fantasy pixel-art medieval enemy, rust iron helmet and armor, burnt orange scarf and short spear; idle, alternating walking poses and spear-charge preparation.
- ash_healer: gritty dark-fantasy pixel-art hooded enemy, ash-grey robes, green sash and green-crystal staff; idle, alternating walking poses and raised-staff healing cast.
- shield_knight: gritty dark-fantasy pixel-art undead knight, dark iron armor, pale-blue tabard, large steel-blue shield and short sword; idle guard, alternating walking poses and sword attack.
- Shared prompt constraints: exact equal 4-column by 4-row sprite sheet; rows down/front, up/back, left, right; columns idle, left-foot walk, right-foot walk, attack/cast; genuine alpha background; full body and weapons within each cell; consistent scale and foot baseline; transparent gutters; no text, labels, grid, backdrop or ground shadow.

Runtime files: ../frames_added_v1/<enemy>/<direction>/<animation>/01.png through 04.png.
Each enemy has 48 RGBA PNG files, 96x96 pixels at native display size. Feet end at
y=84, matching the existing 12px rendering offset. Bounds fit within transparent
safety margins. No runtime scaling or sheet slicing is required.

Rebuild with tools/prepare_added_enemies.ps1. Idle repeats the standing pose;
walk uses left/idle/right/idle; attack uses idle/attack/attack/idle. These are
deliberate short animation cycles, not four independently drawn poses per state.

Run tools/validate_sprites.py to check dimensions, transparency, bounds and paths.
The loader validates each complete enemy set independently; missing or wrongly
sized files retain the colored actor fallback without disabling other enemies.
