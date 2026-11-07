"""Runtime preferences, weapon tuning and optional volume-adjusted WAV files."""
import math
import tempfile
import wave
from pathlib import Path
from array import array
from dataclasses import dataclass, field

WEAPONS = {
    "sword": ("剣", 110, math.pi / 3, 0.65, 1.0),
    "spear": ("槍", 175, math.pi / 9, 0.85, 1.15),
    "axe": ("大斧", 130, math.pi / 2, 1.15, 1.65),
}


@dataclass
class GameOptions:
    difficulty: str = "標準"
    volume: int = 100
    shake: bool = True
    bindings: dict = field(default_factory=dict)

    @property
    def damage_multiplier(self):
        return {"やさしい": 0.65, "標準": 1.0, "難しい": 1.4}[self.difficulty]


_audio_cache = {}
_audio_directory = None


def volume_sound(path, volume):
    global _audio_directory
    if volume == 100:
        return path
    key = (str(path), volume)
    if key in _audio_cache:
        return _audio_cache[key]
    if _audio_directory is None:
        _audio_directory = tempfile.TemporaryDirectory(prefix="ruins-audio-")
    with wave.open(str(path), "rb") as source:
        params = source.getparams()
        data = source.readframes(source.getnframes())
    width = params.sampwidth
    if width == 1:
        data = bytes(round((v - 128) * volume / 100) + 128 for v in data)
    elif width in (2, 4):
        samples = array("h" if width == 2 else "i", data)
        data = array(samples.typecode, (round(v * volume / 100) for v in samples)).tobytes()
    else:
        scaled = bytearray()
        for i in range(0, len(data), width):
            value = int.from_bytes(data[i:i+width], "little", signed=True)
            scaled.extend(round(value * volume / 100).to_bytes(width, "little", signed=True))
        data = bytes(scaled)
    target = Path(_audio_directory.name) / f"{len(_audio_cache)}.wav"
    with wave.open(str(target), "wb") as output:
        output.setparams(params)
        output.writeframes(data)
    _audio_cache[key] = target
    return target
