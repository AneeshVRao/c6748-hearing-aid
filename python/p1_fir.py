"""Phase 1, block 1: FIR design by windowing (Kaiser) vs frequency sampling.

(a) G lowpass (21 taps, cutoff fs/8) both ways, plus rectangular/Hamming/Kaiser windows.
(b) Mode B audiogram FIR (129 taps) both ways.
(c) Zero plots of G and F (linear phase -> reciprocal zero pairs; half-band zero pattern).
"""
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dsp_ref import G, F, NG, FS, M_B, freq_sampling_fir, mode_b_fir, target_db, savefig


def att(h, f_stop, fs=1.0):
    """Stopband attenuation (dB) beyond f_stop, normalised to DC gain."""
    w, H = signal.freqz(h, 1, 1 << 15, fs=fs)
    H = np.abs(H) / abs(H[0])
    return -20 * np.log10(H[w >= f_stop].max())


# ---- (a) lowpass G: windows and frequency sampling ----
win = {name: signal.firwin(NG, 0.25, window=w) for name, w in
       (("rectangular", "boxcar"), ("Hamming", "hamming"), ("Kaiser b=4.5", ("kaiser", 4.5)))}
assert np.allclose(win["Kaiser b=4.5"], G)
# frequency sampling of the same ideal lowpass: 11 samples H(k) at k/21 fs, cutoff fs/8 -> bins 0..2 pass
k = np.arange((NG + 1) // 2)
fk = k / NG
hd = np.where(fk < 0.125, 0.0, -300.0)                 # 0 dB pass, "zero" stop (dB)
fs_plain = freq_sampling_fir(hd, NG)
hd_t = hd.copy(); hd_t[np.argmax(fk > 0.125)] = 20 * np.log10(0.4)   # one transition sample (DESIGN CHOICE 0.4)
fs_trans = freq_sampling_fir(hd_t, NG)

rows = {**win, "freq. sampling": fs_plain, "freq. sampling + transition": fs_trans}
print("G lowpass, 21 taps: stopband attenuation for f >= 0.20 fs")
res = {}
for name, h in rows.items():
    res[name] = att(h, 0.20)
    print(f"  {name:28s} {res[name]:6.1f} dB")
assert res["Kaiser b=4.5"] > 52.0                       # pack: 52.5 dB
assert res["Kaiser b=4.5"] > res["Hamming"] > res["rectangular"]
assert res["freq. sampling + transition"] > res["freq. sampling"]   # a transition sample helps

fig, ax = plt.subplots(figsize=(9, 4.5))
for name, h in rows.items():
    w, H = signal.freqz(h, 1, 4096, fs=FS)
    ax.plot(w, 20 * np.log10(np.abs(H) + 1e-9), label=f"{name} ({res[name]:.0f} dB)")
ax.set(xlim=(0, 24000), ylim=(-90, 5), xlabel="Hz (level 0, fs = 48 kHz)", ylabel="dB",
       title="21-tap lowpass G: window method vs frequency sampling")
ax.axvline(0.20 * FS, color="k", ls=":", lw=0.8)
ax.grid(alpha=0.3); ax.legend(fontsize=8)
savefig(fig, "p1_fir_G_methods.png")

# ---- (b) Mode B audiogram FIR: frequency sampling vs Kaiser-windowed design ----
h_fs = mode_b_fir("N3")
fgrid = np.linspace(0, FS / 2, 513)
h_win = signal.firwin2(M_B, fgrid, 10 ** (target_db("N3", np.maximum(fgrid, 1)) / 20), fs=FS,
                       window=("kaiser", 4.5))
w, Hfs = signal.freqz(h_fs, 1, 8192, fs=FS)
_, Hw = signal.freqz(h_win, 1, 8192, fs=FS)
sel = (w >= 250) & (w <= 8000)
tgt = target_db("N3", w[sel])
e_fs = np.max(np.abs(20 * np.log10(np.abs(Hfs[sel])) - tgt))
e_w = np.max(np.abs(20 * np.log10(np.abs(Hw[sel])) - tgt))
print(f"Mode B 129-tap N3 FIR, max |error| 250-8000 Hz: frequency sampling {e_fs:.2f} dB, "
      f"Kaiser window (firwin2) {e_w:.2f} dB")
assert abs(e_fs - 0.38) < 0.01                          # pack value 0.38 dB
assert e_fs < e_w < 1.5           # windowing rounds the corners of the gain curve

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.semilogx(w[1:], 20 * np.log10(np.abs(Hfs[1:])), label=f"frequency sampling (max err {e_fs:.2f} dB)")
ax.semilogx(w[1:], 20 * np.log10(np.abs(Hw[1:])), "--", label=f"Kaiser window, firwin2 (max err {e_w:.2f} dB)")
ax.semilogx(w[1:], target_db("N3", w[1:]), "k:", label="N3 half-gain target")
fk = np.arange((M_B + 1) // 2) * FS / M_B
ax.plot(fk[1:], target_db("N3", fk[1:]), "o", ms=3, label="frequency samples H(k)")
ax.set(xlim=(100, 24000), ylim=(10, 35), xlabel="Hz", ylabel="dB",
       title="Mode B 129-tap FIR: frequency sampling vs window method")
ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
savefig(fig, "p1_fir_modeB_methods.png")

# ---- (c) zeros of G and F ----
fig, axs = plt.subplots(1, 2, figsize=(9, 4.5))
for ax, h, name in ((axs[0], G, "G (21 taps)"), (axs[1], np.trim_zeros(F), "F (31 taps, half-band)")):
    z = np.roots(h)
    ax.plot(np.cos(np.linspace(0, 2 * np.pi, 400)), np.sin(np.linspace(0, 2 * np.pi, 400)), "k", lw=0.5)
    ax.plot(z.real, z.imag, "o", mfc="none")
    ax.set(aspect="equal", title=f"zeros of {name}", xlim=(-2.2, 2.2), ylim=(-1.6, 1.6))
    ax.grid(alpha=0.3)
    # linear phase: every zero z has a partner 1/conj(z)
    for zi in z:
        if abs(abs(zi) - 1) > 1e-6:
            assert np.min(np.abs(z - 1 / np.conj(zi))) < 1e-6
savefig(fig, "p1_fir_zeros.png")
print("p1_fir OK")
