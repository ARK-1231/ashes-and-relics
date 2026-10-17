# Spellblade boss sprite

Runtime file: `kingdom_guardian_spellblade.png`

Original generated preview: `kingdom_guardian_spellblade_preview.png`

Created with the built-in image generation tool. The preview had an opaque background. `tools/remove_boss_background.ps1` removes connected near-white regions, preserving small highlights and colored magic. The transparent result is now loaded by the game and subsampled once at startup.

Final prompt: On the ORIGINAL transparent knight image supplied, change ONLY the shield: replace shield with an open armored hand conjuring purple magic and three small violet magical lances, suggesting radial and fan magic attacks. Keep original sword, body, face, cloak, canvas size, framing and ALL EXISTING TRANSPARENT PIXELS unchanged. Preserve the original genuine alpha channel. Output transparent PNG. Never paint a checkerboard pattern or background. This is a small localized shield-to-spell-hand edit of the original transparent sprite.

Validation: the runtime PNG has transparent background pixels. The original preview and previous guardian are retained.
