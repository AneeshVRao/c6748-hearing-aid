"""Figures for the IEEE paper, at column width (3.5 in), 8-pt fonts, vector PDF.

    python paper/make_figs.py

Uses the project reference (python/dsp_ref.py) and the committed board readouts in
results/phase4/board/. Writes paper/figures/*.pdf and prints the numbers the paper quotes,
with asserts against the values in docs/_facts.md.
"""
import re
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "python"))
from dsp_ref import (FS, K, L_B, M_B, ROOT, T_LEVEL, TEST_F, band_gains, mode_a,  # noqa: E402
                     mode_b_fir, target_db)

OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7, "xtick.labelsize": 7,
                     "ytick.labelsize": 7, "pdf.fonttype": 42, "lines.linewidth": 1.0})
W = 3.5
FT = [250, 500, 1000, 2000, 4000, 8000]
FTL = ["0.25", "0.5", "1", "2", "4", "8"]


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def mode_a_response(gain_lin, n=1 << 14):
    imp = np.zeros(n)
    imp[0] = 1.0
    h = mode_a(imp, None, gain_lin=np.asarray(gain_lin, float))
    w, H = signal.freqz(h, 1, 1 << 14, fs=FS)
    return w, H


def db(H):
    return 20 * np.log10(np.abs(H) + 1e-12)


# ---------------------------------------------------------------- Fig. 2: Mode A bands and composite
fig, ax = plt.subplots(figsize=(W, 2.2))
names = ["B5 (>6 kHz)", "B4", "B3", "B2", "B1 (<750 Hz)"]
for b in range(K + 1):
    g = np.zeros(K + 1)
    g[b] = 1.0
    w, H = mode_a_response(g)
    ax.semilogx(w[1:], db(H[1:]), lw=0.8, label=names[b])
w, H = mode_a_response(np.ones(K + 1))
ripple = db(H[(w >= 50) & (w <= 20000)])
w, H = mode_a_response(10 ** (band_gains("N3") / 20))
ax.semilogx(w[1:], db(H[1:]), "k", lw=1.5, label="sum, N3 gains")
ax.set_xlim(100, 20000)
ax.set_ylim(-60, 35)
ax.set_xticks([100, 1000, 10000], ["0.1", "1", "10"])
ax.set_xlabel("Frequency (kHz)")
ax.set_ylabel("Magnitude (dB)")
ax.grid(True, which="both", alpha=0.3)
ax.legend(ncol=3, loc="lower center", fontsize=6.5, handlelength=1.5, columnspacing=0.8)
save(fig, "fig_bands.pdf")
print(f"unity-gain ripple 50 Hz-20 kHz: +{ripple.max():.3f} / {ripple.min():.3f} dB")
assert abs(ripple.max() - 0.020) < 0.002 and abs(ripple.min() + 0.010) < 0.002

# ---------------------------------------------------------------- Fig. 3: accuracy vs target, N2/N3/S2
f = np.geomspace(250, 8000, 400)
fig, ax = plt.subplots(2, 1, figsize=(W, 2.9), sharex=True)
for p, c in (("N2", "C2"), ("N3", "C0"), ("S2", "C3")):
    t = target_db(p, f)
    wa, Ha = mode_a_response(10 ** (band_gains(p) / 20))
    ea = np.interp(f, wa, db(Ha)) - t
    wb, Hb = signal.freqz(mode_b_fir(p), 1, 1 << 14, fs=FS)
    eb = np.interp(f, wb, db(Hb)) - t
    ax[0].semilogx(f, ea, c, label=p)
    ax[1].semilogx(f, eb, c, label=p)
    ta = np.interp(TEST_F, wa, db(Ha)) - target_db(p, TEST_F)
    tb = np.interp(TEST_F, wb, db(Hb)) - target_db(p, TEST_F)
    ax[0].plot(TEST_F, ta, c + "o", ms=2.5)
    ax[1].plot(TEST_F, tb, c + "o", ms=2.5)
    print(f"{p}: max |error| at test tones  A {np.max(np.abs(ta)):.2f} dB  B {np.max(np.abs(tb)):.2f} dB;"
          f"  dense 250 Hz-8 kHz  A {np.max(np.abs(ea)):.2f}  B {np.max(np.abs(eb)):.2f}")
for a, n in zip(ax, ("Mode A", "Mode B")):
    a.axhspan(-3, 3, color="0.9", zorder=0)
    a.set_ylabel(f"{n} error (dB)")
    a.grid(True, which="both", alpha=0.3)
    a.set_ylim(-8, 8)
ax[0].legend(ncol=3, loc="lower left")
ax[1].set_xticks(FT, FTL)
ax[1].minorticks_off()
ax[1].set_xlabel("Frequency (kHz)")
save(fig, "fig_accuracy.pdf")

# ---------------------------------------------------------------- Fig. 4: board-measured band gains (N3)
BRD = ROOT / "results" / "phase4" / "board"
r = dict(re.findall(r"^(\S+) = (\S+)$", (BRD / "internal_readout.txt").read_text(), re.M))
board = np.array([[float(r[f"g_int[{m}].gain_db[{i}]"]) for i in range(11)] for m in (0, 1)])
rows = [ln.split() for ln in (ROOT / "results/phase3/board_expected.txt").read_text().splitlines()[2:13]]
design = np.array([[float(x[1]) for x in rows], [float(x[2]) for x in rows]])
assert np.max(np.abs(board - design)) < 0.011, board - design
target = target_db("N3", TEST_F)
fig, ax = plt.subplots(figsize=(W, 2.1))
ax.semilogx(TEST_F, target, "k--", label="target (N3)")
for m, (c, n, mk) in enumerate((("C0", "Mode A", "o"), ("C1", "Mode B", "s"))):
    ax.semilogx(TEST_F, design[m], c + "-", alpha=0.5, label=f"{n} design")
    ax.semilogx(TEST_F, board[m], c + mk, ms=3, mfc="none", label=f"{n} board")
ax.set_xticks(FT, FTL)
ax.minorticks_off()
ax.set_xlabel("Frequency (kHz)")
ax.set_ylabel("Gain (dB)")
ax.grid(True, which="both", alpha=0.3)
ax.legend(ncol=2, loc="lower right")
save(fig, "fig_board_gains.pdf")
print("max |board - design| =", np.max(np.abs(board - design)), "dB;  Mode A max |design - target| =",
      round(np.max(np.abs(design[0] - target)), 2), " Mode B:", round(np.max(np.abs(design[1] - target)), 2))

# ---------------------------------------------------------------- Fig. 5: latency breakdown (calculated)
IO, CODEC = 10, 38                                        # samples: FIFO/block model, ADC 17 + DAC 21 (AIC3106)
proc = {"Mode A": T_LEVEL[0], "Mode B": 2 * L_B + (M_B - 1) // 2}
assert proc == {"Mode A": 375, "Mode B": 320}
fig, ax = plt.subplots(figsize=(W, 1.25))
for i, (n, s) in enumerate(proc.items()):
    parts = [(s, "filter bank / block + FIR", "C0"), (IO, "I/O buffering (model)", "C1"), (CODEC, "codec", "C7")]
    left = 0.0
    for v, lab, c in parts:
        ax.barh(i, v / FS * 1e3, left=left, color=c, height=0.55, label=lab if i == 0 else None)
        left += v / FS * 1e3
    ax.text(left + 0.1, i, f"{left:.2f} ms", va="center", fontsize=7)
    print(f"{n}: {left:.2f} ms")
ax.axvline(10, color="k", ls="--", lw=0.8)
ax.text(10.05, 1.42, "10 ms", fontsize=7, va="center")
ax.set_yticks([0, 1], list(proc))
ax.set_ylim(-0.5, 1.7)
ax.set_xlim(0, 11.5)
ax.invert_yaxis()
ax.set_xlabel("Calculated input-to-output delay (ms)")
ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.55), fontsize=6.5, frameon=False)
save(fig, "fig_latency.pdf")

# ---------------------------------------------------------------- CPU load check from the live readout (Table)
t6 = re.findall(r"^(\S+) = (\S+)$", (BRD / "T6_live.txt").read_text(), re.M)
blocks = [dict(t6[:11]), dict(t6[11:])]
a, b = blocks
la = float(a["g_prof.isr_sum"]) / float(a["g_prof.isr_count"]) / 25000
lb = (float(b["g_prof.isr_sum"]) / float(b["g_prof.isr_count"])
      + float(b["g_prof.bg_sum"]) / float(b["g_prof.bg_count"]) / 32) / 25000
print(f"live CPU load: Mode A {100 * la:.1f} %, Mode B {100 * lb:.1f} %")
assert round(100 * la, 1) == 10.5 and round(100 * lb, 1) == 4.2
