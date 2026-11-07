"""Combat geometry, safe path shortcuts, and PCM volume regressions."""
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dark_ruins_rpg import DarkRuins2D
from game_options import GameOptions, volume_sound


class GameOptionsTests(unittest.TestCase):
    def test_spear_reaches_farther_but_has_narrower_arc(self):
        game = DarkRuins2D.__new__(DarkRuins2D)
        game.px = game.py = 0
        game.attack_direction = (1, 0)
        far = SimpleNamespace(x=160, y=0, radius=1)
        side = SimpleNamespace(x=50, y=50, radius=1)
        game.weapon = "sword"
        self.assertFalse(game._in_attack_sector(far))
        self.assertTrue(game._in_attack_sector(side))
        game.weapon = "spear"
        self.assertTrue(game._in_attack_sector(far))
        self.assertFalse(game._in_attack_sector(side))

    def test_shortcut_stops_before_obstructed_waypoint(self):
        game = DarkRuins2D.__new__(DarkRuins2D)
        companion = SimpleNamespace(x=0, y=0, path_timer=1,
                                    path=[(0, 48), (48, 48), (96, 48)])
        game._line_blocked = lambda x, y, tx, ty, radius: tx >= 96
        game._move_ally_toward = Mock()
        game._update_companion_movement(companion, 150, 48, 0.016)
        self.assertEqual(companion.path[0], (48, 48))
        game._move_ally_toward.assert_called_once_with(companion, 48, 48, 0.016)

    def test_volume_scales_pcm_and_preserves_wave_format(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "cue.wav"
            with wave.open(str(source), "wb") as output:
                output.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
                output.writeframes((10000).to_bytes(2, "little", signed=True))
            target = volume_sound(source, 50)
            with wave.open(str(target), "rb") as result:
                self.assertEqual(result.getframerate(), 22050)
                self.assertEqual(int.from_bytes(result.readframes(1), "little", signed=True), 5000)


if __name__ == "__main__":
    unittest.main()
