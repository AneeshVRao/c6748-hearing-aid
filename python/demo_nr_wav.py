"""Noise-suppression listening demo with faint noise (SIMULATED with the Python reference, not a board run).

    python python/demo_nr_wav.py

Speech at -40 dBFS RMS + white noise 20 dB below it, through Mode B, preset N3. Writes to results/demo_nr/:
nr_demo_off.wav, nr_demo_on.wav, and nr_demo_switching.wav (off 0-3 s, on 3-6 s, off 6-9 s, on from 9 s).
The switch at 6 s falls inside a speech pause, where the hiss is exposed.
"""
import numpy as np
from scipy.io import wavfile
from dsp_ref import FS, L_B, ROOT, chain

SNR_DB, SWITCH_S, FADE_S = 20, 3.0, 0.02


def rms_db(v):
    return 20 * np.log10(np.sqrt(np.mean(v ** 2)) + 1e-15)


_, sp = wavfile.read(ROOT / "data" / "speech_48k.wav")
s = sp.astype(float) / 32768
s = s[: len(s) // L_B * L_B]
s *= 10 ** (-40 / 20) / np.sqrt(np.mean(s ** 2))
w = np.random.default_rng(7).standard_normal(len(s))
w *= 10 ** ((-40 - SNR_DB) / 20) / np.sqrt(np.mean(w ** 2))
x = s + w
off, on = chain(x, "B", "N3"), chain(x, "B", "N3", nr=True)
n = min(len(off), len(on))
off, on = off[:n], on[:n]

# on/off gain, 0 = off and 1 = on, with short fades so that switching does not click
t = np.arange(n) / FS
g = (np.floor(t / SWITCH_S).astype(int) % 2).astype(float)
g[t >= 3 * SWITCH_S] = 1.0
k = int(FADE_S * FS)
g = np.convolve(np.pad(g, k, mode="edge"), np.ones(k) / k, "same")[k:k + n]
ab = (1 - g) * off + g * on

# speech pauses: 50 ms frames of the clean speech 20 dB below its RMS, after the noise tracker has settled
fr = int(0.05 * FS)
quiet = np.repeat([np.sqrt(np.mean(s[i:i + fr] ** 2)) < 10 ** (-60 / 20) for i in range(0, n, fr)], fr)[:n]
quiet[: int(2 * FS)] = False
drop, level = rms_db(off[quiet]) - rms_db(on[quiet]), rms_db(off) - rms_db(on)
lag = np.argmax(np.correlate(off[100000:104000], on[100000 - 300:104000 + 300], "valid")) - 300
print(f"hiss in pauses: {rms_db(off[quiet]):.1f} -> {rms_db(on[quiet]):.1f} dBFS ({drop:.1f} dB lower)")
print(f"whole file: {rms_db(off):.1f} -> {rms_db(on):.1f} dBFS; off and on aligned, lag {lag} samples")
assert drop > 10 and level < 1 and lag == 0

out = ROOT / "results" / "demo_nr"
out.mkdir(exist_ok=True)
for name, y in (("off", off), ("on", on), ("switching", ab)):
    wavfile.write(out / f"nr_demo_{name}.wav", int(FS), np.round(np.clip(y, -1, 32767 / 32768) * 32768).astype(np.int16))
print("wrote", out)
