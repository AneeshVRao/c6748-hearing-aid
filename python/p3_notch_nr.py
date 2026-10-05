"""Extras (brief items): IIR feedback notch by the bilinear transform with automatic howl detection,
and noise suppression in both modes. Pass criteria were fixed before running (docs/CHANGES.md C23):
  notch depth >= 100 dB at f0, -3 dB bandwidth = f0/Q within 3 %
  NR with all gains forced to 1 reproduces the verified Mode A / Mode B exactly
  howl detector: no notch on 11.8 s of speech; a howl tone notched within 0.5 s (0.3 s planned; see C23), >= 40 dB down after
  NR: SNR improvement > 0 dB in every case; noise-only segments attenuated >= 6 dB
SNR after nonlinear processing is measured by shadow filtering: the gains computed on the mixture are
applied to speech and noise separately (exact here, because each block/sample gain is applied linearly).
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dsp_ref import (FS, L_B, NOTCH_Q, NR_GMIN, ROOT, HowlDetector, band_gains, goertzel, hpf, mode_a, mode_a_nr,
                     mode_b, mode_b_nr, notch_auto, notch_coeffs, savefig)

rng = np.random.default_rng(21)

# ---------------------------------------------------------------- 1. notch design (bilinear, pre-warped)
f0 = 2700.0
c = notch_coeffs(f0)
w = np.linspace(1, FS / 2 - 1, 200001)
_, H = signal.freqz(c[:3], c[3:], w, fs=FS)
HdB = 20 * np.log10(np.abs(H) + 1e-300)
depth = -20 * np.log10(abs(signal.freqz(c[:3], c[3:], [f0], fs=FS)[1][0]) + 1e-300)
below = w[(HdB < -3.0103)]
bw = below.max() - below.min()
print(f"Notch f0 = {f0:.0f} Hz, Q = {NOTCH_Q}: depth {depth:.0f} dB, -3 dB bandwidth {bw:.1f} Hz (f0/Q = {f0 / NOTCH_Q:.0f}), "
      f"poles r = {np.abs(np.roots(c[3:]))[0]:.5f}")
assert depth >= 100 and abs(bw / (f0 / NOTCH_Q) - 1) < 0.03
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(w, HdB)
ax.set(xlim=(1500, 4000), ylim=(-60, 3), xlabel="Hz", ylabel="dB",
       title=f"Feedback notch by bilinear transform: f0 {f0:.0f} Hz, Q {NOTCH_Q:.0f} (bandwidth {bw:.0f} Hz)")
ax.grid(alpha=0.3)
savefig(fig, "p3_notch_response.png", "phase3")

# ---------------------------------------------------------------- 2. NR with unit gains == verified core
x = 0.01 * rng.standard_normal(16 * L_B)
gd = band_gains("N3")
ones_a = [np.ones(len(x) >> min(k, 4)) for k in range(5)]
ones_a = [np.ones(-(-len(x) // 2 ** k)) for k in range(5)]
ea = np.max(np.abs(mode_a_nr(x, gd, fixed=ones_a)[0] - mode_a(x, gd)))
eb = np.max(np.abs(mode_b_nr(x, "N3", fixed=[np.ones(65)] * 16)[0] - mode_b(x, "N3")))
print(f"NR with unit gains vs core: Mode A {ea:.1e}, Mode B {eb:.1e} (FIR redesigned per block by frequency sampling)")
assert ea < 1e-12 and eb < 1e-12

# ---------------------------------------------------------------- 3. howl detector and auto notch
_, sp = wavfile.read(ROOT / "data" / "speech_48k.wav")
s = sp.astype(float) / 32768
s *= 10 ** (-40 / 20) / np.sqrt(np.mean(s ** 2))
s = s[: len(s) // L_B * L_B]
# second voice, never used while choosing the detector settings (validation set)
fz, sz = wavfile.read(ROOT / "data" / "speech2_zira_44k1.wav")
s2 = signal.resample_poly(sz.astype(float) / 32768, 160, 147)
s2 *= 10 ** (-40 / 20) / np.sqrt(np.mean(s2 ** 2))
s2 = s2[: len(s2) // L_B * L_B]
for name, v in (("voice 1 (design)", s), ("voice 2 (validation)", s2)):
    det = HowlDetector()
    n_false = sum(det.block(hpf(v)[j * L_B:(j + 1) * L_B]) is not None for j in range(len(v) // L_B))
    print(f"Howl detector on {len(v) / FS:.1f} s of {name} alone: {n_false} notch(es) placed")
    assert n_false == 0
for name, v in (("voice 2", s2),):                             # detection on the validation voice too
    tv = np.arange(len(v)) / FS
    hv = np.where(tv >= 3.0, np.sqrt(2) * 10 ** (-30 / 20) * np.sin(2 * np.pi * 1900.0 * tv), 0.0)
    ev = []
    notch_auto(hpf(v + hv), ev)
    print(f"{name} + 1900 Hz howl from 3.0 s: " + ", ".join(f"{fq:.1f} Hz from {i / FS:.3f} s" for i, fq in ev))
    assert len(ev) == 1 and abs(ev[0][1] - 1900) < 10 and ev[0][0] / FS - 3.0 < 0.5

t = np.arange(len(s)) / FS
howl = np.where(t >= 3.0, np.sqrt(2) * 10 ** (-30 / 20) * np.sin(2 * np.pi * f0 * t), 0.0)   # 10 dB above speech
xm = hpf(s + howl)
events = []
y = notch_auto(xm, events)
print(f"Speech + {f0:.0f} Hz howl from 3.0 s: notches at " + ", ".join(f"{fq:.1f} Hz active from {i / FS:.3f} s" for i, fq in events))
assert len(events) == 1 and abs(events[0][1] - f0) < 10 and events[0][0] / FS - 3.0 < 0.5
on = events[0][0] + int(0.05 * FS)
n = 4608 * 2
before = goertzel(xm[on:on + n], round(f0 * n / FS) * FS / n)
after = goertzel(y[on:on + n], round(f0 * n / FS) * FS / n)
att = 20 * np.log10(before / after)
print(f"Howl tone level after the notch is active: {att:.1f} dB lower")
assert att >= 40

fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
for ax, v, lab in ((axs[0], xm, "input: speech + howl at 2.7 kHz from 3 s"), (axs[1], y, "after automatic notch")):
    f, tt, S = signal.spectrogram(v, FS, nperseg=1024, noverlap=768)
    SdB = 10 * np.log10(S + 1e-20)
    ax.pcolormesh(tt, f / 1000, SdB, vmin=SdB.max() - 90, vmax=SdB.max(), shading="auto")
    ax.set(ylim=(0, 8), ylabel="kHz", title=lab)
axs[1].axvline(events[0][0] / FS, color="w", ls=":")
axs[1].set_xlabel("s")
savefig(fig, "p3_auto_notch.png", "phase3")

# ---------------------------------------------------------------- 4. noise suppression (shadow filtering)
from dsp_ref import NR_BIAS_A, NR_BIAS_B, nr_bias
ba, bb = nr_bias(seed=7)                         # a different noise realisation than the one used to set them
print(f"Noise-floor bias factors re-measured on white noise: A {[round(v, 3) for v in ba]}, B {bb:.3f}")
assert all(abs(m / c - 1) < 0.05 for m, c in zip(ba + [bb], NR_BIAS_A + [NR_BIAS_B]))
def pink(nsamp):
    X = np.fft.rfft(rng.standard_normal(nsamp))
    return np.fft.irfft(X / np.sqrt(np.maximum(np.fft.rfftfreq(nsamp, 1 / FS), 20)), nsamp)


def run(mode, sv, nv):
    """Returns SNR improvement, speech change and noise change (dB) of NR vs the same mode without NR."""
    hs, hn = hpf(sv), hpf(nv)
    if mode == "A":
        _, Gt = mode_a_nr(hs + hn, gd)
        ys, yn = mode_a_nr(hs, gd, fixed=Gt)[0], mode_a_nr(hn, gd, fixed=Gt)[0]
        rs, rn = mode_a(hs, gd), mode_a(hn, gd)
    else:
        _, Gt = mode_b_nr(hs + hn, "N3")
        ys, yn = mode_b_nr(hs, "N3", fixed=Gt)[0], mode_b_nr(hn, "N3", fixed=Gt)[0]
        rs, rn = mode_b(hs, "N3")[: len(ys)], mode_b(hn, "N3")[: len(ys)]
    p = lambda v: np.sum(v ** 2)
    return (10 * np.log10(p(ys) / p(yn)) - 10 * np.log10(p(rs) / p(rn)),
            10 * np.log10(p(ys) / p(rs)), 10 * np.log10(p(yn) / p(rn)), ys + yn)


rows = []
print("\nNoise suppression vs the same mode without it (speech -40 dBFS RMS, 11.8 s):")
print("  mode  noise  input SNR   SNR gain   speech   noise")
for mode in "AB":
    for kind in ("white", "pink"):
        for snr_in in (0, 5, 10):
            nv = rng.standard_normal(len(s)) if kind == "white" else pink(len(s))
            nv *= np.sqrt(np.mean(s ** 2) / np.mean(nv ** 2)) * 10 ** (-snr_in / 20)
            gain, ds, dn, _ = run(mode, s, nv)
            rows.append((mode, kind, snr_in, gain, ds, dn))
            print(f"   {mode}    {kind:5s}  {snr_in:3d} dB    {gain:+6.2f} dB  {ds:+6.2f}  {dn:+6.2f}")
assert all(r[3] > 0 for r in rows)

# noise-only segment: first 0.5 s of the white-noise case must drop >= 6 dB once the tracker has the floor
nv = rng.standard_normal(2 * int(FS)) * 0.003
for mode in "AB":
    y_nr = (mode_a_nr(hpf(nv), gd)[0] if mode == "A" else mode_b_nr(hpf(nv), "N3")[0])
    y_ref = mode_a(hpf(nv), gd) if mode == "A" else mode_b(hpf(nv), "N3")[: len(y_nr)]
    seg = slice(int(1.0 * FS), int(2.0 * FS) - 512)
    a = 10 * np.log10(np.sum(y_nr[seg] ** 2) / np.sum(y_ref[seg] ** 2))
    print(f"Noise only, Mode {mode}: output {a:+.1f} dB vs no NR (floor {20 * np.log10(NR_GMIN):.0f} dB)")
    assert a <= -6

fig, ax = plt.subplots(figsize=(9, 4))
lab = [f"{m} {k}\n{s_} dB" for m, k, s_, *_ in rows]
ax.bar(range(len(rows)), [r[3] for r in rows], color=["C0" if r[0] == "A" else "C1" for r in rows])
ax.set_xticks(range(len(rows)), lab, fontsize=7)
ax.set(ylabel="SNR improvement, dB", title="Noise suppression: SNR gain (shadow filtering), Mode A blue, Mode B orange")
ax.grid(alpha=0.3, axis="y")
savefig(fig, "p3_nr_snr_gain.png", "phase3")

nv = rng.standard_normal(len(s)); nv *= np.sqrt(np.mean(s ** 2) / np.mean(nv ** 2)) * 10 ** (-5 / 20)
fig, axs = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
for ax, v, ttl in ((axs[0], hpf(s + nv), "input: speech + white noise, 5 dB SNR"),
                   (axs[1], mode_b(hpf(s + nv), "N3"), "Mode B, no noise suppression"),
                   (axs[2], mode_b_nr(hpf(s + nv), "N3")[0], "Mode B with noise suppression")):
    f, tt, S = signal.spectrogram(v, FS, nperseg=1024, noverlap=768)
    SdB = 10 * np.log10(S + 1e-20)
    ax.pcolormesh(tt, f / 1000, SdB, vmin=SdB.max() - 70, vmax=SdB.max(), shading="auto")
    ax.set(ylim=(0, 12), ylabel="kHz", title=ttl)
axs[2].set_xlabel("s")
savefig(fig, "p3_nr_spectrograms.png", "phase3")
print("p3_notch_nr OK")
