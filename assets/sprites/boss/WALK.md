# Boss walk cycle

`walk/01.png` through `walk/04.png`: four transparent 180 x 180 downward-facing walk poses. The game preloads the images, advances at six frames per second only when movement succeeds, uses idle when stopped, and gives attack poses priority. This is one facing direction, not a four-direction set.

Generated with the built-in image generation tool using the existing spellblade as reference. Source: `walk_source.png`. Background removal: `tools/remove_boss_background.ps1`. Frame extraction: `tools/split_boss_walk.ps1`.

## Prompt

Create a coherent FOUR-FRAME looping WALK CYCLE sprite sheet for the same dark royal spellblade boss in reference. Strict 2x2 grid on square 1024x1024 canvas, four equal 512x512 cells, read left-to-right then next row. Same crown helmet, charcoal armor, burgundy cloak, chipped greatsword held lowered in right hand, left armored hand relaxed with a tiny purple glow. NO large magical projectiles. Slightly top-down, facing down toward viewer, consistent head height, body proportions, camera, scale, center and foot baseline in every cell, at least 40px clear padding around each full character. Four genuinely distinct walking phases: 1 left foot forward/right foot back; 2 left foot planted/right knee passing forward, torso slightly higher; 3 right foot forward/left foot back; 4 right foot planted/left knee passing forward, torso slightly higher. Alternate legs visibly and swing cloak gently. Sword remains carried downward, not attacking. Game-ready detailed pixel-art-like painting matching reference. Exactly four full-body poses, no cropped weapons or feet, no text, no labels, no grid lines, no floor or shadows. Transparent alpha background preferred, otherwise uniform pure white, never checkerboard.
