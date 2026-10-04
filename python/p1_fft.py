"""Phase 1, block 5: radix-2 DIT and DIF FFTs written from scratch vs the library FFT,
operation counts for radix-2 / radix-4 / split-radix, direct DFT, and a Goertzel check on the
calibration tones used by the on-board tone meter (test T2).
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dsp_ref import FS, TEST_F, fft_dit, fft_dif, goertzel, savefig

rng = np.random.default_rng(5)

# ---- correctness: own DIT / DIF and direct DFT vs numpy ----
for N in (8, 16, 64, 256, 1024):
    x = rng.standard_normal(N) + 1j * rng.standard_normal(N)
    ref = np.fft.fft(x)
    e_dit = np.max(np.abs(fft_dit(x) - ref))
    e_dif = np.max(np.abs(fft_dif(x) - ref))
    n = np.arange(N)
    e_dft = np.max(np.abs(np.exp(-2j * np.pi * np.outer(n, n) / N) @ x - ref))
    print(f"N={N:5d}: max error DIT {e_dit:.1e}, DIF {e_dif:.1e}, direct DFT {e_dft:.1e}")
    assert max(e_dit, e_dif, e_dft) < 1e-9
# inverse via the forward FFT: x = conj(FFT(conj(X)))/N
X = np.fft.fft(x)
assert np.max(np.abs(np.conj(fft_dit(np.conj(X))) / len(X) - x)) < 1e-9

# ---- operation counts: non-trivial complex twiddle multiplies ----
# trivial twiddles W^0 = 1 and W^(N/4) = -j cost nothing; W^(N/8)-type ones are counted as general here.
def m_r2(N):   # radix-2: two half-size FFTs + N/2 twiddles, 2 of them trivial
    return 0 if N <= 2 else 2 * m_r2(N // 2) + N // 2 - 2


def m_r4(N):   # radix-4 (N a power of 4): four quarter-size FFTs + 3(N/4-1) twiddles, one of them -j
    return 0 if N <= 4 else 4 * m_r4(N // 4) + 3 * (N // 4 - 1) - 1


def m_sr(N):   # split radix: one half-size + two quarter-size FFTs + 2(N/4-1) twiddles
    return 0 if N <= 2 else m_sr(N // 2) + 2 * m_sr(N // 4) + 2 * (N // 4 - 1)


print("\n     N   direct DFT   radix-2   radix-4   split-radix   (non-trivial complex multiplies)")
table = []
for N in (16, 64, 256, 1024):
    c = {}
    fft_dit(np.ones(N), count=c)                 # instrumented own DIT
    assert c["mul"] == m_r2(N) == N // 2 * int(np.log2(N)) - 3 * N // 2 + 2
    row = (N, N * N, m_r2(N), m_r4(N), m_sr(N))
    table.append(row)
    print(f"{N:6d} {N*N:11d} {row[2]:9d} {row[3]:9d} {row[4]:12d}")
    assert row[4] <= row[3] < row[2]             # split radix <= radix-4 < radix-2
r256 = [r for r in table if r[0] == 256][0]
print(f"N=256: radix-4 saves {100*(1-r256[3]/r256[2]):.0f} %, split radix saves {100*(1-r256[4]/r256[2]):.0f} % of radix-2 multiplies")

fig, ax = plt.subplots(figsize=(7, 4))
names = ["radix-2", "radix-4", "split-radix"]
ax.bar(names, r256[2:], color=["C0", "C1", "C2"])
for i, v in enumerate(r256[2:]):
    ax.text(i, v, str(v), ha="center", va="bottom")
ax.set(ylabel="non-trivial complex multiplies", title="FFT-256 multiply count (direct DFT: 65 536)")
savefig(fig, "p1_fft_opcounts.png")

# ---- Goertzel on the 11 calibration tones ----
# Every tone must sit on a bin: k = f N / fs integer. 375 Hz needs N to be a multiple of 128 and
# 250 Hz a multiple of 192, so N must be a multiple of 384. N = 4800 (research/07 T2) puts 375 Hz on bin 37.5.
N = 4608                                          # 96 ms, 10.42 Hz bins (correction C10)
assert all(f * N % FS == 0 for f in TEST_F) and not all(f * 4800 % FS == 0 for f in TEST_F)
t = np.arange(N) / FS
print(f"\nGoertzel, N = {N}, tone amplitude 0.1 (-20 dBFS) plus a 0.05 tone 1 bin away:")
worst = 0
for f in TEST_F:
    x = 0.1 * np.sin(2 * np.pi * f * t + 0.3) + 0.05 * np.sin(2 * np.pi * (f + FS / N) * t)
    a = goertzel(x, f)
    err = 20 * np.log10(a / 0.1)
    worst = max(worst, abs(err))
    print(f"  {f:6.0f} Hz: measured {a:.6f} ({err:+.4f} dB)")
assert worst < 0.001
print(f"Goertzel cost: 1 multiply per sample per bin -> 11 bins x {N} = {11*N} multiplies per 96 ms; "
      f"a {N}-point FFT is not a power of 2, and an 8192-point radix-2 FFT needs {m_r2(8192)} complex multiplies")

# ---- Chirp-Z transform: 512-point zoom on the 750 Hz crossover of Mode A (research/03, Unit 2) ----
from scipy import signal
from dsp_ref import band_gains, mode_a
imp = np.zeros(8192); imp[0] = 1
h = mode_a(imp, band_gains("N3"))                 # Mode A impulse response (linear, shift-variance negligible)
f1, f2, m = 600.0, 900.0, 512
w = np.exp(-2j * np.pi * (f2 - f1) / ((m - 1) * FS))
a = np.exp(2j * np.pi * f1 / FS)
Z = signal.czt(h, m, w, a)
fz = f1 + np.arange(m) * (f2 - f1) / (m - 1)
_, Hf = signal.freqz(h, 1, fz, fs=FS)
assert np.max(np.abs(Z - Hf)) < 1e-9              # CZT = DTFT samples on the chosen arc
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(fz, 20 * np.log10(np.abs(Z)), label="CZT, 512 points in 600-900 Hz (0.59 Hz spacing)")
ff = np.fft.rfftfreq(len(h), 1 / FS)
sel = (ff >= f1) & (ff <= f2)
ax.plot(ff[sel], 20 * np.log10(np.abs(np.fft.rfft(h))[sel]), "o", label=f"FFT-{len(h)} bins (5.9 Hz spacing)")
ax.axhline(17.5, color="k", ls=":", label="target 17.5 dB")
ax.set(xlabel="Hz", ylabel="dB", title="Chirp-Z zoom: Mode A gain around the 750 Hz crossover (N3)")
ax.grid(alpha=0.3); ax.legend(fontsize=8)
savefig(fig, "p1_fft_czt_zoom.png")
print(f"CZT zoom 600-900 Hz: Mode A gain {20*np.log10(np.abs(Z)).min():.2f} to {20*np.log10(np.abs(Z)).max():.2f} dB; matches freqz")
print("p1_fft OK")
