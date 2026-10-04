"""Phase 1, block 6: gain presets and the full Mode A / Mode B chains.

1. Reproduces the pack's accuracy table (research/audiogram.md section 4) for all six cases.
2. Full chain (HPF -> mode -> limiter) at the 11 audiometric tones vs target (test T2 in simulation).
3. Delay (impulse), noise-excited response and coherence (T3/T4), crossover spurs (T9).
4. Speech and speech + pink noise: spectrograms and per-band SNR (T7/T8 in simulation).
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dsp_ref import (AUDIOGRAMS, FS, ROOT, TEST_F, band_gains, band_gains_db, chain, freq_sampling_fir,
                     gain_curve_db, hpf, mode_a, mode_b, savefig, target_db, tone_gain, M_B)

# ---- 1. accuracy table, all six cases (pack: research/audiogram.md section 4) ----
PACK = {("N2", 0.5): (1.01, 0.22), ("N2", 0.4): (0.82, 0.18), ("N3", 0.5): (1.53, 0.38),
        ("N3", 0.4): (1.20, 0.33), ("S2", 0.5): (6.82, 0.49), ("S2", 0.4): (5.20, 0.45)}
print("case       Mode A max err (pack)   worst spur   Mode B max err (pack)")
for (aud, fac), (pa, pb) in PACK.items():
    gd = band_gains_db(AUDIOGRAMS[aud], fac)
    errs, spurs = [], []
    for f in TEST_F:
        g, s = tone_gain(lambda x: mode_a(x, gd), f)
        errs.append(abs(g - gain_curve_db(AUDIOGRAMS[aud], f, fac)[0]))
        spurs.append(s)
    fk = np.arange((M_B + 1) // 2) * FS / M_B
    h = freq_sampling_fir(gain_curve_db(AUDIOGRAMS[aud], fk, fac))
    w, H = signal.freqz(h, 1, 8192, fs=FS)
    sel = (w >= 250) & (w <= 8000)
    eb = np.max(np.abs(20 * np.log10(np.abs(H[sel])) - gain_curve_db(AUDIOGRAMS[aud], w[sel], fac)))
    ea = max(errs)
    print(f"{aud} x{fac}    {ea:5.2f} dB ({pa:.2f})          {max(spurs):6.1f} dBc     {eb:5.2f} dB ({pb:.2f})")
    assert abs(ea - pa) < 0.006 and abs(eb - pb) < 0.006

# ---- 2. full chain at the 11 tones, default preset N3 ----
res = {}
for mode in "AB":
    res[mode] = np.array([tone_gain(lambda x: chain(x, mode, "N3"), f)[0] for f in TEST_F])
tgt = target_db("N3", TEST_F)
print("\nFull chain (HPF + mode + limiter), N3 half-gain, -40 dBFS tones:")
print("   Hz  target  Mode A  Mode B")
for f, t, a, b in zip(TEST_F, tgt, res["A"], res["B"]):
    print(f"{f:6.0f}  {t:6.2f}  {a:6.2f}  {b:6.2f}")
print(f"max |error|: Mode A {np.max(np.abs(res['A'] - tgt)):.2f} dB, Mode B {np.max(np.abs(res['B'] - tgt)):.2f} dB")
assert np.max(np.abs(res["A"] - tgt)) < 1.6 and np.max(np.abs(res["B"] - tgt)) < 0.4

fig, ax = plt.subplots(figsize=(10, 4.2))
xi = np.arange(len(TEST_F))
ax.bar(xi - 0.27, tgt, 0.27, label="target (N3 half-gain, 30 dB cap)", color="0.6")
ax.bar(xi, res["A"], 0.27, label="Mode A (filter bank)")
ax.bar(xi + 0.27, res["B"], 0.27, label="Mode B (FFT OLA)")
ax.set_xticks(xi, [f"{f/1000:g}k" if f >= 1000 else f"{f:.0f}" for f in TEST_F])
ax.set(ylabel="gain, dB", xlabel="Hz", ylim=(0, 35), title="Simulated full-chain gain at the audiometric frequencies")
ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3, axis="y")
savefig(fig, "p1_chain_tone_gains.png")

# ---- 3. delay, response from noise, coherence, crossover spurs ----
imp = np.zeros(4096); imp[0] = 1
dA = int(np.argmax(np.abs(mode_a(imp, np.zeros(5)))))
dB = int(np.argmax(np.abs(mode_b(imp, "bypass"))))
print(f"\nImpulse peak: Mode A {dA} samples ({dA/FS*1e3:.2f} ms), Mode B FIR group delay {dB} samples "
      f"(+ 2L = 256 buffering on the board, estimated)")
assert dA == 375 and dB == 64

rng = np.random.default_rng(7)
x = 0.01 * rng.standard_normal(int(10 * FS))
fig, axs = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
for mode in "AB":
    y = chain(x, mode, "N3")
    f, Pxy = signal.csd(x, y, FS, nperseg=8192)
    _, Pxx = signal.welch(x, FS, nperseg=8192)
    _, C = signal.coherence(x, y, FS, nperseg=8192)
    band = (f >= 100) & (f <= 10000)
    print(f"Mode {mode}: min coherence 100 Hz-10 kHz = {C[band].min():.4f}")
    assert C[band].min() > 0.9                       # T4 pass threshold (DESIGN CHOICE in research/07)
    axs[0].semilogx(f[1:], 20 * np.log10(np.abs(Pxy[1:] / Pxx[1:])), label=f"Mode {mode}")
    axs[1].semilogx(f[1:], C[1:], label=f"Mode {mode}")
axs[0].semilogx(f[1:], target_db("N3", f[1:]), "k:", label="target")
axs[0].set(ylabel="gain, dB", ylim=(-40, 35), title="Response from 10 s white noise (Welch, as test T4)")
axs[1].set(ylabel="coherence", xlabel="Hz", ylim=(0.8, 1.01))
for a in axs:
    a.grid(alpha=0.3, which="both"); a.legend(fontsize=8)
savefig(fig, "p1_chain_noise_response.png")

print("\nCrossover spurs, Mode A N3 (test T9 tones):")
worst = -999
for ft in (700, 760, 1450, 1550, 2950, 3050, 5900, 6100):
    _, s = tone_gain(lambda v: chain(v, "A", "N3"), ft)
    worst = max(worst, s)
    print(f"  {ft} Hz: {s:6.1f} dBc")
assert worst < -60

# ---- 4. speech, speech + pink noise ----
_, sp = wavfile.read(ROOT / "data" / "speech_48k.wav")
s = sp.astype(float) / 32768
s *= 10 ** (-40 / 20) / np.sqrt(np.mean(s ** 2))         # -40 dBFS RMS, the test level in research/07
white = rng.standard_normal(len(s))
pink = np.real(np.fft.irfft(np.fft.rfft(white) / np.sqrt(np.maximum(np.fft.rfftfreq(len(s), 1 / FS), 20)), len(s)))
pink *= np.sqrt(np.mean(s ** 2) / np.mean(pink ** 2)) * 10 ** (-5 / 20)   # 5 dB SNR

outs = {}
for mode in "AB":
    v = chain(s, mode, "N3")
    outs[mode] = v
    clips = int(np.sum(np.abs(v) >= 10 ** (-1 / 20) - 1e-12))
    print(f"Speech -40 dBFS RMS (input peak {20*np.log10(np.max(np.abs(s))):.1f} dBFS) through Mode {mode}: "
          f"output RMS {20*np.log10(np.sqrt(np.mean(v**2))):.1f} dBFS, limiter clips {clips} "
          f"({100*clips/len(v):.3f} % of samples)")
    assert np.max(np.abs(v)) <= 10 ** (-1 / 20) and clips / len(v) < 1e-3   # limiter holds; clipping rare
    out = ROOT / "results" / "phase1" / "audio"
    out.mkdir(parents=True, exist_ok=True)
    wavfile.write(out / f"speech_mode{mode}_N3.wav", 48000, (v * 32767).astype(np.int16))

# per-octave-band SNR: HPF + bank is linear, so process speech and noise separately (limiter left out)
edges = [(250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000)]
print("\nSpeech + pink noise at 5 dB SNR: per-band SNR in -> out (Mode A)")
ys, yn = (mode_a(hpf(v), band_gains("N3")) for v in (s, pink))
for lo, hi in edges:
    sos = signal.butter(6, [lo, hi], "bandpass", fs=FS, output="sos")
    snr = lambda a, b: 10 * np.log10(np.mean(signal.sosfilt(sos, a) ** 2) / np.mean(signal.sosfilt(sos, b) ** 2))
    si, so = snr(s, pink), snr(ys, yn)
    print(f"  {lo:5d}-{hi:5d} Hz: {si:6.1f} dB -> {so:6.1f} dB")
    assert abs(si - so) < 1.0                       # linear gain cannot improve SNR inside a band

fig, axs = plt.subplots(3, 2, figsize=(12, 9), sharex=True, sharey=True)
mix = s + pink
for col, (inp, lab) in enumerate(((s, "speech"), (mix, "speech + pink noise, 5 dB SNR"))):
    for row, (v, name) in enumerate(((inp, "input"), (chain(inp, "A", "N3"), "Mode A"), (chain(inp, "B", "N3"), "Mode B"))):
        f, t, S = signal.spectrogram(v, FS, nperseg=1024, noverlap=768)
        SdB = 10 * np.log10(S + 1e-20)
        axs[row, col].pcolormesh(t, f / 1000, SdB, vmin=SdB.max() - 80, vmax=SdB.max(), shading="auto")  # 80 dB range
        axs[row, col].set(title=f"{name}: {lab}", ylim=(0, 12))
for a in axs[:, 0]:
    a.set_ylabel("kHz")
for a in axs[-1]:
    a.set_xlabel("s")
savefig(fig, "p1_chain_spectrograms.png")
print("p1_chain OK")
