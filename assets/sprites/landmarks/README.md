# Landmark sprites

Generated using the built-in image_gen tool. Runtime: 128 x 128 RGBA PNG. The loader finds each PNG's lowest visible row once at startup and aligns that base with the world position; transparent padding does not shift the interaction point. Current visible sizes: shrine 76 x 84, stairs 97 x 109, exit 87 x 107 pixels. Keep source/ originals for future resizing. Rebuild with tools/prepare_landmark_sprites.ps1. Shrine appears at the healing point; stairs on floors 1–2; exit on floor 3. Shrine and exit overlap nearby character sprites in ground-position order; stairs remain below characters. Existing interaction rules are preserved.

## Final prompts

### shrine

Use case: stylized-concept. Production sprite for a dark fantasy top-down 2D action RPG. Single isolated object, genuine transparent RGBA background, no checkerboard or ground backdrop. Hand-painted compact game art, ash-grey weathered stone, crisp readable silhouette, restrained detail readable at 128px. Orthographic three-quarter overhead view looking north, symmetrical front visible, no isometric diagonal rotation. Object fully within square canvas with 12% transparent padding, centered horizontally, base at 85% canvas height. No text, letters, UI, characters, watermark. Subject: small ruined healing shrine, squat stone altar with two broken short pillars and a blue glowing sacred crystal above a bowl. Subtle cyan light contained near the object. Clearly a healing shrine.

### stairs

Use case: stylized-concept. Production sprite for a dark fantasy top-down 2D action RPG. Single isolated object, genuine transparent RGBA background, no checkerboard or ground backdrop. Hand-painted compact game art, ash-grey weathered stone, crisp readable silhouette, restrained detail readable at 128px. Orthographic three-quarter overhead view looking north, symmetrical front visible, no isometric diagonal rotation. Object fully within square canvas with 12% transparent padding, centered horizontally, base at 85% canvas height. No text, letters, UI, characters, watermark. Subject: flight of six broad ancient stone steps ascending away from viewer northwards, short broken stone side rails. Clearly upward stairs to next dungeon floor; open top landing, no door, no portal. Muted pale stone edges.

### exit

Use case: stylized-concept. Production sprite for a dark fantasy top-down 2D action RPG. Single isolated object, genuine transparent RGBA background, no checkerboard or ground backdrop. Hand-painted compact game art, ash-grey weathered stone, crisp readable silhouette, restrained detail readable at 128px. Orthographic three-quarter overhead view looking north, symmetrical front visible, no isometric diagonal rotation. Object fully within square canvas with 12% transparent padding, centered horizontally, base at 85% canvas height. No text, letters, UI, characters, watermark. Subject: ancient stone exit gateway, open arch with two stone pillars, soft emerald and warm ivory light filling the opening, short threshold. Clearly an exit rather than stairs or altar. Glow contained inside arch, no broad fog.

