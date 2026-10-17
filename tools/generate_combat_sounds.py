"""Generate short original combat effects using only the Python standard library."""
from pathlib import Path
import math
import random
import struct
import wave

ROOT = Path(__file__).resolve().parent.parent / 'assets' / 'sounds'
RATE = 22050

def build(name, duration, start, end, noise, pulse=0):
    rng = random.Random(name)
    samples = []
    phase = 0.0
    filtered = 0.0
    for i in range(round(duration * RATE)):
        t = i / RATE
        u = t / duration
        phase += math.tau * (start + (end - start) * u) / RATE
        filtered = .65 * filtered + .35 * rng.uniform(-1, 1)
        envelope = min(1, t / .008) * (1 - u) ** 1.8
        modulation = .65 + .35 * math.cos(math.tau * pulse * t) if pulse else 1
        tone = math.sin(phase) + .22 * math.sin(phase * 2.71)
        value = .5 * envelope * modulation * ((1 - noise) * tone + noise * filtered * 2)
        samples.append(struct.pack('<h', round(max(-1, min(1, value)) * 32767)))
    with wave.open(str(ROOT / f'{name}.wav'), 'wb') as wav:
        wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        wav.writeframes(b''.join(samples))

def build_boss(name, duration, start, end, noise, pulse=0):
    """Layer a bass impact, metallic body and damped echoes with headroom."""
    rng = random.Random(name)
    length = round(duration * RATE)
    dry = []
    bass_phase = body_phase = 0.0
    low_noise = previous_noise = 0.0
    bass_start = 115 if name in ('boss_lance', 'enemy_ranged') else 85
    bass_end = 38 if name == 'boss_wave' else 48
    for i in range(length):
        t = i / RATE
        u = t / duration
        attack = min(1.0, t / .004)
        fade = min(1.0, (duration - t) / .05)
        bass_hz = bass_end + (bass_start - bass_end) * math.exp(-t * 18)
        bass_phase += math.tau * bass_hz / RATE
        # A second harmonic keeps the impact audible on smaller speakers.
        bass = (math.sin(bass_phase) + .38 * math.sin(2 * bass_phase)) * math.exp(-t * 7)
        body_phase += math.tau * (end + (start - end) * math.exp(-t * 9)) / RATE
        body = (math.sin(body_phase) + .3 * math.sin(1.43 * body_phase)) * math.exp(-t * 10)
        raw = rng.uniform(-1, 1)
        low_noise = .92 * low_noise + .08 * raw
        crack = (raw - previous_noise) * math.exp(-t * 65)
        previous_noise = raw
        rumble = low_noise * 3 * math.exp(-t * 5)
        # Give each move a recognizable texture beyond the common impact.
        sweep = (raw - low_noise) * math.exp(-((t - .045) / .055) ** 2)
        metal = sum(math.sin(body_phase * ratio) * math.exp(-t * decay)
                    for ratio, decay in ((2.13, 14), (3.71, 20), (5.19, 28))) / 3
        shimmer = (math.sin(body_phase * 2) + .35 * math.sin(body_phase * 3)) * math.exp(-t * 5)
        if name in ('boss_melee', 'enemy_melee'):
            texture = .65 * sweep + .32 * metal
        elif name == 'boss_lance':
            texture = .40 * sweep + .48 * metal
        elif name == 'boss_wave':
            texture = .65 * rumble + .20 * sweep
        else:
            texture = .34 * shimmer * (.6 + .4 * math.sin(math.tau * (pulse or 16) * t)) + .20 * sweep
        modulation = .75 + .25 * math.cos(math.tau * pulse * t) if pulse else 1
        bass_weight = .38 if name.startswith('enemy_') else .70
        value = bass_weight * bass + .24 * body * modulation + texture + noise * (.40 * rumble + .12 * crack)
        dry.append(math.tanh(value * 1.3) * attack * fade)
    wet = dry[:]
    for delay, gain in ((.043, .20), (.079, .14), (.127, .08)):
        offset = round(delay * RATE)
        damped = 0.0
        for i in range(offset, length):
            damped = .78 * damped + .22 * dry[i - offset]
            wet[i] += damped * gain
    peak = max(abs(v) for v in wet) or 1.0
    samples = [round(v / peak * .78 * min(1, (length - 1 - i) / (RATE * .025)) * 32767)
               for i, v in enumerate(wet)]
    with wave.open(str(ROOT / f'{name}.wav'), 'wb') as wav:
        wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        wav.writeframes(struct.pack(f'<{len(samples)}h', *samples))

if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    effects = {
        'swing': (.18, 1100, 180, .94, 0),
        'hit': (.20, 420, 85, .65, 0),
        'hurt': (.22, 180, 55, .65, 0),
        'warning': (.20, 400, 800, .05, 12),
        'phase': (.48, 120, 620, .3, 8),
        'enemy_melee': (.26, 950, 140, .75, 0),
        'enemy_ranged': (.34, 380, 1100, .28, 18),
        'boss_melee': (.52, 480, 100, .85, 0),
        'boss_fan': (.42, 700, 170, .50, 22),
        'boss_ring': (.62, 260, 650, .25, 10),
        'boss_lance': (.40, 1250, 160, .45, 0),
        'boss_spiral': (.20, 330, 700, .35, 30),
        'boss_wave': (.72, 170, 42, .85, 0),
    }
    for name, args in effects.items():
        (build_boss if name.startswith(("boss_", "enemy_")) else build)(name, *args)
    print(f'Generated {len(effects)} WAV effects in {ROOT}')
