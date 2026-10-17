# Combat sounds

Original synthesized mono 16-bit PCM WAV effects at 22050 Hz, generated with `python tools/generate_combat_sounds.py`. No external dependencies or downloaded audio.

Player attacks use `swing` on misses and `hit` on contact. Boss releases use `boss_melee`, `boss_fan`, `boss_ring`, `boss_lance`, `boss_spiral`, or `boss_wave`. `warning`, `hurt`, and `phase` replace the former system notification sounds.

Windows playback uses asynchronous winsound file playback. Only one effect plays at a time; a new effect replaces the previous one. Missing audio files or unavailable Windows audio leave gameplay silent. Playback routing and WAV format are checked programmatically; speaker output is not automatically verified.

Boss effects layer a descending 38–115 Hz bass impact, a second harmonic for small speakers, metallic tones, filtered noise and damped 43/79/127 ms echoes. Peaks stay below 78% full scale. Wave and ring attacks have longer tails; spiral stays at 0.20 seconds to fit its 0.22-second repeated shots. Regeneration preserves the existing synthesis for player and notification sounds.
