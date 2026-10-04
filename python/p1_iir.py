"""Phase 1, block 2: IIR design from an analog prototype.

The board HPF (4th-order Butterworth, 100 Hz) by the bilinear transform, compared with
matched-z, and impulse invariance (which only works for a low-pass: an analog high-pass is
not band-limited and its impulse response contains a delta).
"""
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dsp_ref import FS, HPF_SOS, savefig

T = 1 / FS
FC = 100.0


def impulse_invariance(b, a, T):
    """H(s) = sum r_i/(s - p_i)  ->  H(z) = sum T r_i / (1 - e^(p_i T) z^-1). Needs a strictly proper H(s)."""
    r, p, k = signal.residue(b, a)
    assert len(k) == 0, "H(s) is not strictly proper: impulse invariance is undefined"
    bz, az = signal.invresz(T * r, np.exp(p * T), [])
    return np.real(bz), np.real(az)


def matched_z(z_s, p_s, k_s, T, f_norm):
    """Map every s-plane pole/zero with z = e^(sT); set the gain to match the analog filter at f_norm."""
    zz, pz = np.exp(np.asarray(z_s) * T), np.exp(np.asarray(p_s) * T)
    b, a = np.poly(zz).real, np.poly(pz).real
    _, Ha = signal.freqs_zpk(z_s, p_s, k_s, [2 * np.pi * f_norm])
    _, Hd = signal.freqz(b, a, [f_norm], fs=1 / T)
    return b * abs(Ha[0]) / abs(Hd[0]), a


# ---- bilinear (board filter) ----
w = np.logspace(1, np.log10(23999), 2000)
_, Hb = signal.sosfreqz(HPF_SOS, w, fs=FS)
g100 = 20 * np.log10(abs(signal.sosfreqz(HPF_SOS, [FC], fs=FS)[1][0]))
poles = np.concatenate([np.roots(s[3:]) for s in HPF_SOS])
print(f"Bilinear HPF: gain at 100 Hz = {g100:.3f} dB, pole radii = {np.round(np.abs(poles), 6)}")
print("Board biquads (b0 b1 b2 a0 a1 a2):\n", HPF_SOS)
assert abs(g100 + 3.01) < 0.02 and np.all(np.abs(poles) < 1)

# ---- matched-z of the same analog high-pass ----
zs, ps, ks = signal.butter(4, 2 * np.pi * FC, "highpass", analog=True, output="zpk")
bm, am = matched_z(zs, ps, ks, T, 20000.0)
_, Hm = signal.freqz(bm, am, w, fs=FS)
_, Ha = signal.freqs_zpk(zs, ps, ks, 2 * np.pi * w)
gm100 = 20 * np.log10(abs(signal.freqz(bm, am, [FC], fs=FS)[1][0]))
dev = np.max(np.abs(20 * np.log10(np.abs(Hm[w > 50])) - 20 * np.log10(np.abs(Hb[w > 50]))))
print(f"Matched-z HPF: gain at 100 Hz = {gm100:.3f} dB; max difference from bilinear above 50 Hz = {dev:.3f} dB")
assert dev < 0.1              # at fc << fs the two mappings almost coincide

# ---- 1st-order example quoted in research/03 (matched-z vs bilinear pole) ----
Kt = np.tan(np.pi * FC / FS)
p_bil, p_mz = (1 - Kt) / (1 + Kt), np.exp(-2 * np.pi * FC / FS)
print(f"1st-order 100 Hz: bilinear pole {p_bil:.6f}, matched-z pole {p_mz:.6f}")
assert f"{p_bil:.6f}" == f"{p_mz:.6f}" == "0.986995"

# ---- impulse invariance: not possible for the high-pass ----
bh, ah = signal.butter(4, 2 * np.pi * FC, "highpass", analog=True)
try:
    impulse_invariance(bh, ah, T)
    raise SystemExit("expected failure")
except AssertionError as e:
    print(f"Impulse invariance on the analog HPF: {e}")

# ---- impulse invariance vs bilinear on a low-pass, where aliasing shows ----
fig, axs = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, fl in zip(axs, (100.0, 8000.0)):
    bl, al = signal.butter(4, 2 * np.pi * fl, analog=True)
    bi, ai = impulse_invariance(bl, al, T)
    bb, ab = signal.butter(4, fl, fs=FS)
    _, Hi = signal.freqz(bi, ai, w, fs=FS)
    _, Hbl = signal.freqz(bb, ab, w, fs=FS)
    _, Hal = signal.freqs(bl, al, 2 * np.pi * w)
    Hi = Hi / abs(Hi[0])                               # II scales DC by about 1; normalise
    floor = 20 * np.log10(abs(Hi[-1]))
    print(f"LP {fl:.0f} Hz: response at 24 kHz: analog {20*np.log10(abs(Hal[-1])):.1f} dB, "
          f"impulse invariance {floor:.1f} dB (aliasing floor), bilinear {20*np.log10(abs(Hbl[-1])+1e-12):.1f} dB")
    if fl == 8000.0:
        assert floor > 20 * np.log10(abs(Hal[-1])) + 2   # aliasing lifts the stopband (2.3 dB measured)
    for H, lab in ((Hal, "analog"), (Hi, "impulse invariance"), (Hbl, "bilinear")):
        ax.semilogx(w, 20 * np.log10(np.abs(H) + 1e-12), label=lab)
    ax.set(ylim=(-120, 5), title=f"4th-order Butterworth LP {fl:.0f} Hz", xlabel="Hz", ylabel="dB")
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
savefig(fig, "p1_iir_impinv_lowpass.png")

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.semilogx(w, 20 * np.log10(np.abs(Ha)), "k:", label="analog prototype")
ax.semilogx(w, 20 * np.log10(np.abs(Hb)), label="bilinear (board)")
ax.semilogx(w, 20 * np.log10(np.abs(Hm)), "--", label="matched-z")
ax.axvline(FC, color="grey", lw=0.6)
ax.set(ylim=(-80, 3), xlabel="Hz", ylabel="dB", title="4th-order Butterworth HPF 100 Hz: bilinear vs matched-z")
ax.grid(alpha=0.3, which="both"); ax.legend()
savefig(fig, "p1_iir_hpf_methods.png")
print("p1_iir OK")
