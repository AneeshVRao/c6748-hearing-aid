"""Phase 1, block 3: decimation and interpolation at each level, and one rational I/D example.

Decimation: G (21-tap) before ↓2 suppresses the component that would alias into the band the
next level uses. Interpolation: F (31-tap half-band) after ↑2 removes the image.
Rational I/D: test speech 44.1 kHz -> 48 kHz with I/D = 160/147 (polyphase, scipy resample_poly).
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dsp_ref import G, F, FS, K, ROOT, savefig


def level_db(x, f, fs):
    """Level (dB) of the component at f, Hann-windowed FFT, +-2 bins."""
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) / len(x)      # normalise: lengths differ after ↓2/↑2
    i = int(round(f * len(x) / fs))
    return 20 * np.log10(np.sqrt(np.sum(X[i - 2:i + 3] ** 2)) + 1e-15)


n = 1 << 14
print("level  fs_k    tone -> alias after ↓2     no filter    with G    suppression")
for k in range(K):
    fk = FS / 2 ** k
    f_in = round(0.35 * n) / n * fk            # 0.35 fs_k, folds onto 0.15 fs_k (the next level's band)
    f_al = fk / 2 - f_in
    x = np.sin(2 * np.pi * f_in * np.arange(n) / fk)
    ref = level_db(x, f_in, fk)
    raw = level_db(x[::2], f_al, fk / 2) - ref
    filt = level_db(signal.lfilter(G, 1, x)[::2], f_al, fk / 2) - ref
    print(f"  {k}   {fk:6.0f}  {f_in:7.0f} -> {f_al:7.0f} Hz   {raw:7.1f} dB  {filt:7.1f} dB  {raw - filt:6.1f} dB")
    assert raw > -1 and filt < -50              # unfiltered alias at full level; G gives > 50 dB

print("level  fs_k   tone at fs_k/2 rate -> image after ↑2     no filter    with F")
for k in range(K):
    fk = FS / 2 ** k
    f_lo = round(0.15 * n / 2) / (n / 2) * (fk / 2)      # 0.15 fs_k, inside the band of level k+1
    f_im = fk / 2 - f_lo
    x = np.sin(2 * np.pi * f_lo * np.arange(n // 2) / (fk / 2))
    up = np.zeros(n); up[::2] = x
    y = 2 * signal.lfilter(F, 1, up)
    sig = level_db(y, f_lo, fk)
    raw = level_db(2 * up, f_im, fk) - level_db(2 * up, f_lo, fk)
    img = level_db(y, f_im, fk) - sig
    print(f"  {k}   {fk:6.0f}  {f_lo:7.0f} -> image {f_im:7.0f} Hz   {raw:7.1f} dB  {img:7.1f} dB")
    assert abs(raw) < 1 and img < -50

# ---- spectra figure at level 0 ----
fk = FS
f_in = round(0.35 * n) / n * fk
x = np.sin(2 * np.pi * f_in * np.arange(n) / fk) + np.sin(2 * np.pi * 3000 * np.arange(n) / fk)
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
for x2, lab in ((x[::2], "↓2 without G"), (signal.lfilter(G, 1, x)[::2], "G then ↓2")):
    X = 20 * np.log10(np.abs(np.fft.rfft(x2 * np.hanning(len(x2)))) / (len(x2) / 4) + 1e-12)
    axs[0].plot(np.fft.rfftfreq(len(x2), 2 / fk), X, label=lab)
axs[0].set(title=f"Decimation, level 0: tones 3 kHz + {f_in:.0f} Hz", xlabel="Hz (24 kHz rate)", ylabel="dB", ylim=(-110, 5))
axs[0].legend(); axs[0].grid(alpha=0.3)
xs = np.sin(2 * np.pi * 3000 * np.arange(n // 2) / (fk / 2))
up = np.zeros(n); up[::2] = xs
for y, lab in ((2 * up, "↑2 without F"), (2 * signal.lfilter(F, 1, up), "↑2 then F")):
    Y = 20 * np.log10(np.abs(np.fft.rfft(y * np.hanning(n))) / (n / 4) + 1e-12)
    axs[1].plot(np.fft.rfftfreq(n, 1 / fk), Y, label=lab)
axs[1].set(title="Interpolation, level 0: 3 kHz tone from 24 kHz", xlabel="Hz (48 kHz rate)", ylim=(-110, 5))
axs[1].legend(); axs[1].grid(alpha=0.3)
savefig(fig, "p1_multirate_levels.png")

# ---- rational I/D = 160/147: 44.1 kHz -> 48 kHz ----
I, D = 160, 147
assert 44100 * I // D == 48000 and 44100 * I % D == 0
t = np.arange(44100) / 44100
tone = 0.5 * np.sin(2 * np.pi * 1000 * t)
y = signal.resample_poly(tone, I, D)
seg = y[2400:2400 + 43200]                     # whole number of 1 kHz cycles at 48 kHz
amp = np.sqrt(2) * np.std(seg)
peak = np.fft.rfftfreq(len(seg), 1 / FS)[np.argmax(np.abs(np.fft.rfft(seg)))]
print(f"I/D {I}/{D}: 1 kHz tone -> peak {peak:.1f} Hz, amplitude {amp:.4f} (input 0.5), length {len(tone)} -> {len(y)}")
assert peak == 1000.0 and abs(20 * np.log10(amp / 0.5)) < 0.05 and len(y) == 48000

fs_in, sp = wavfile.read(ROOT / "data" / "speech_44k1.wav")
assert fs_in == 44100
sp48 = signal.resample_poly(sp.astype(float) / 32768, I, D)
wavfile.write(ROOT / "data" / "speech_48k.wav", 48000, np.round(np.clip(sp48, -1, 32767 / 32768) * 32768).astype(np.int16))
print(f"speech: {len(sp)} samples @44.1k -> {len(sp48)} @48k, written data/speech_48k.wav")

fig, ax = plt.subplots(figsize=(9, 4))
for v, fs, lab in ((sp / 32768, 44100, "original 44.1 kHz"), (sp48, 48000, "resampled 48 kHz (160/147)")):
    f, P = signal.welch(v, fs, nperseg=4096)
    ax.semilogx(f[1:], 10 * np.log10(P[1:] + 1e-20), label=lab)
ax.set(xlabel="Hz", ylabel="dB/Hz", title="Test speech before and after rational resampling")
ax.grid(alpha=0.3, which="both"); ax.legend()
savefig(fig, "p1_multirate_resample.png")
print("p1_multirate OK")
