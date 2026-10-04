"""Phase 1, block 4: overlap-add FFT filtering vs direct convolution (must match),
overlap-save, and the time aliasing that appears when the FFT is too short (N < L + M - 1).
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dsp_ref import FS, L_B, M_B, N_FFT, ROOT, mode_b_fir, ola, ols, savefig

fs, sp = wavfile.read(ROOT / "data" / "speech_48k.wav")
x = sp[: 3 * 48000].astype(float) / 32768
h = mode_b_fir("N3")
ref = signal.lfilter(h, 1, x)                     # direct convolution (FIR, causal)

e_ola = np.max(np.abs(ola(x, h) - ref))
e_ols = np.max(np.abs(ols(x, h) - ref))
print(f"OLA  L={L_B}, M={M_B}, N={N_FFT}: max |y_OLA - y_direct| = {e_ola:.2e}")
print(f"OLS  N={N_FFT}, {N_FFT - M_B + 1} new samples/block: max |y_OLS - y_direct| = {e_ols:.2e}")
print(f"max |y_OLA - y_OLS| = {np.max(np.abs(ola(x, h) - ols(x, h))):.2e}")
assert e_ola < 1e-6 and e_ols < 1e-6


def ola_unchecked(x, h, L, N):
    """OLA without the N >= L+M-1 guard: the circular wrap-around lands on the wrong output samples."""
    H = np.fft.fft(h, N)
    y = np.zeros(len(x) + N)
    for s in range(0, len(x) - L + 1, L):
        y[s:s + N] += np.fft.ifft(np.fft.fft(x[s:s + L], N) * H).real
    return y[: len(x)]


rows = []
for N in (256, 224, 192, 160):
    e = np.max(np.abs(ola_unchecked(x, h, L_B, N) - ref))
    rows.append((N, e))
    print(f"N = {N}: L+M-1 = {L_B + M_B - 1} {'<=' if L_B + M_B - 1 <= N else '> '} N -> max error {e:.2e}")
assert rows[0][1] < 1e-6 and all(e > 1e-3 for _, e in rows[1:])

# cost per output sample (real multiplies; complex multiply = 4 real, radix-2 FFT N/2 log2 N butterflies)
direct = M_B
fft_cost = 2 * (N_FFT // 2) * int(np.log2(N_FFT)) * 4 + N_FFT * 4
print(f"Cost: direct {direct} mult/sample; FFT-OLA ~{fft_cost / L_B:.0f} real mult/sample "
      f"(2 radix-2 FFTs + spectrum multiply per {L_B} samples, before real-input savings)")

fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
t = np.arange(len(x)) / FS
i = slice(48000, 48000 + 4 * L_B)
axs[0].plot(t[i] * 1e3, ref[i], label="direct convolution")
axs[0].plot(t[i] * 1e3, ola(x, h)[i], "--", label=f"OLA N={N_FFT}")
axs[0].plot(t[i] * 1e3, ola_unchecked(x, h, L_B, 192)[i], ":", label="OLA N=192 (too short)")
for b in range(5):
    axs[0].axvline(t[48000 + b * L_B] * 1e3, color="grey", lw=0.5)
axs[0].set(ylabel="output", title="Overlap-add: block boundaries every L = 128 samples (2.67 ms)")
axs[0].legend(fontsize=8); axs[0].grid(alpha=0.3)
axs[1].semilogy(t[i] * 1e3, np.abs(ola(x, h)[i] - ref[i]) + 1e-18, label=f"|OLA N={N_FFT} - direct|")
axs[1].semilogy(t[i] * 1e3, np.abs(ola_unchecked(x, h, L_B, 192)[i] - ref[i]) + 1e-18, label="|OLA N=192 - direct|")
axs[1].set(xlabel="ms", ylabel="abs error"); axs[1].legend(fontsize=8); axs[1].grid(alpha=0.3)
savefig(fig, "p1_ola_vs_direct.png")
print("p1_ola OK")
