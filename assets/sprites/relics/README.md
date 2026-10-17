# Relic sprites

The game loads nine 96 x 96 transparent PNG files from this directory. Each
sprite is displayed at half size in the field and equipped-relic HUD. Generated
originals are retained in `../relics_source/`; run
`tools/prepare_relic_sprites.ps1` to crop and normalize them again.

## Generation prompt

Each relic was generated separately with the built-in image generation tool.
The shared prompt requested one centered, isolated collectible for a top-down
dark-fantasy RPG, in crisp hand-painted pixel-art-like style, readable at 44
pixels, with genuine transparency, generous padding, and no ground, shadow,
frame, text, watermark, or additional objects.

Subjects and palettes:

- `blade`: jagged blackened sword shard with ember-red cracks.
- `lantern`: antique vial-lantern containing a golden sacred flame.
- `heart`: heart-shaped obsidian gemstone with violet inner veins.
- `chalice`: silver-green ceremonial goblet with mint life energy.
- `gauntlet`: massive engraved bronze-orange armored fist.
- `wing`: silver feathered-wing badge around an ice-blue shield.
- `ember`: faceted crystal containing a red-orange dawn flame.
- `ward`: ancient crowned royal talisman with violet runes.
- `dew`: moonlit blue orb cradled by a silver crescent.
