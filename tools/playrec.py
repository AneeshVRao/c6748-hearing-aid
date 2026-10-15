"""Play a WAV on the PC output and record the PC input at the same time (48 kHz, 16-bit).

    python tools/playrec.py <play.wav> <rec.wav> [--out DEV] [--in DEV] [--tail 1.0]
    python tools/playrec.py --list

The recording is 2 channels as delivered by the input device. Board LINE OUT -> PC input.
"""
import argparse
import numpy as np
import sounddevice as sd
from scipy.io import wavfile

ap = argparse.ArgumentParser()
ap.add_argument("play", nargs="?")
ap.add_argument("rec", nargs="?")
ap.add_argument("--out", default=None)
ap.add_argument("--in", dest="inp", default=None)
ap.add_argument("--tail", type=float, default=1.0, help="extra seconds recorded after the file ends")
ap.add_argument("--gain", type=float, default=-20.0,
                help="playback gain in dB. ponytail: -20 while testing in the library; use 0 for the calibrated T2-T10 runs")
ap.add_argument("--list", action="store_true")
a = ap.parse_args()
if a.list:
    print(sd.query_devices())
    raise SystemExit
dev = lambda d: int(d) if d is not None and d.isdigit() else d
fs, x = wavfile.read(a.play)
assert fs == 48000, fs
x = x.astype(np.float32) / 32768.0 if x.dtype == np.int16 else x.astype(np.float32)
x *= 10 ** (a.gain / 20)
if x.ndim == 1:
    x = np.stack([x, x], 1)
x = np.concatenate([x, np.zeros((int(a.tail * fs), x.shape[1]), np.float32)])
y = sd.playrec(x, fs, channels=2, device=(dev(a.inp), dev(a.out)), dtype="float32", blocking=True)
wavfile.write(a.rec, fs, np.clip(y * 32767, -32768, 32767).astype(np.int16))
print(f"{a.rec}: {len(y) / fs:.1f} s, peak {20 * np.log10(np.abs(y).max() + 1e-12):.1f} dBFS, "
      f"rms {20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-12):.1f} dBFS")
