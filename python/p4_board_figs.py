"""Phase 4 figures from the board readouts in results/phase4/board/ (no board needed).

    python python/p4_board_figs.py

Writes results/phase4/p4_*.png: on-board band gains vs design and target, board output vs Python,
CPU load per mode, and -O0 vs -O3 cycle counts. Checks the readouts against the report's gates.
"""
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dsp_ref import ROOT, TEST_F, chain, savefig, target_db
from board_compare import read_dat

BRD = ROOT / "results" / "phase4" / "board"
CYC = 25000                                   # cycles per 4-sample interrupt at 300 MHz / 48 kHz


def readout(name):
    """'name = value' lines of a dss_run.js readout, in order (a name can repeat)."""
    return [(k, float(v)) for k, v in re.findall(r"^(\S+) = (\S+)$", (BRD / name).read_text(), re.M)]


# ---------------------------------------------------------------- band gains: board vs design vs target
r = dict(readout("internal_readout.txt"))
board = np.array([[r[f"g_int[{m}].gain_db[{i}]"] for i in range(11)] for m in (0, 1)])
rows = [l.split() for l in (ROOT / "results/phase3/board_expected.txt").read_text().splitlines()[2:13]]
design = np.array([[float(x[1]) for x in rows], [float(x[2]) for x in rows]])
target = target_db("N3", TEST_F)
assert np.max(np.abs(board - design)) < 0.05, board - design
fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True, height_ratios=[2, 1])
ax[0].semilogx(TEST_F, target, "k--", label="half-gain target (N3, 30 dB cap)")
for m, (c, n) in enumerate((("C0", "Mode A"), ("C1", "Mode B"))):
    ax[0].semilogx(TEST_F, design[m], c + "-", alpha=0.5, label=f"{n} design (Python)")
    ax[0].semilogx(TEST_F, board[m], c + "o", label=f"{n} on the board (Goertzel)")
    ax[1].semilogx(TEST_F, board[m] - design[m], c + "o-", label=f"{n}: board - design")
    ax[1].semilogx(TEST_F, design[m] - target, c + ":", label=f"{n}: design - target")
ax[0].set_ylabel("gain (dB)"); ax[0].legend(fontsize=8); ax[0].grid(True, which="both", alpha=0.3)
ax[1].set_ylabel("error (dB)"); ax[1].set_xlabel("frequency (Hz)"); ax[1].legend(fontsize=7, ncol=2)
ax[1].grid(True, which="both", alpha=0.3)
ax[1].set_xticks(TEST_F, [f"{f / 1000:g}k" for f in TEST_F], fontsize=8); ax[1].minorticks_off()
ax[0].set_title("Band gains measured on the LCDK (internal.out) vs design and target")
savefig(fig, "p4_board_gains.png", "phase4")

# ---------------------------------------------------------------- board output vs Python, sample by sample
x = read_dat(BRD / "g_stored.dat", as_float=False) / 32768
fig, ax = plt.subplots(figsize=(8, 3.5))
for f, mode, lag in (("out_modeA.dat", "A", 0), ("out_modeB.dat", "B", 256)):
    y = read_dat(BRD / f)[:len(x)]
    ref = chain(x, mode, "N3")
    ref = np.concatenate([np.zeros(lag), ref[:len(ref) - lag]])
    e = np.abs(y - ref)
    assert e.max() < 1e-4, (mode, e.max())
    ax.semilogy(np.arange(len(e)) / 48000, e + 1e-12, lw=0.5, label=f"Mode {mode} (max {e.max():.1e})")
ax.axhline(1e-4, color="k", ls="--", label="gate 1e-4")
ax.set_ylim(1e-10, 1e-3); ax.set_xlabel("time (s): 11 tones, then noise"); ax.set_ylabel("|board - Python|")
ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
ax.set_title("DSP output vs Python reference (same input, preset N3)")
savefig(fig, "p4_board_vs_python.png", "phase4")

# ---------------------------------------------------------------- CPU load at 300 MHz
t6 = readout("T6_live.txt")
live = [v for k, v in t6 if k in ("g_prof.isr_sum", "g_prof.isr_count", "g_prof.bg_sum", "g_prof.bg_count")]
(sa, na, _, _), (sb, nb, bs, bn) = live[:4], live[4:8]
o0 = dict(readout("internal_o0_readout.txt"))
load = lambda d, m: (d[f"g_int[{m}].avg"] + d[f"g_int[{m}].bg_avg"] / 32) / CYC * 100
bars = {"A live": sa / na / CYC * 100, "B live": (sb / nb + bs / bn / 32) / CYC * 100,
        "A": load(r, 0), "B": load(r, 1), "A + NR": load(r, 2), "B + NR": load(r, 3),
        "A -O0": load(o0, 0), "B -O0": load(o0, 1)}
assert abs(bars["A live"] - 10.5) < 0.05 and abs(bars["B live"] - 4.2) < 0.05, bars
fig, ax = plt.subplots(figsize=(8, 3.5))
b = ax.bar(list(bars), list(bars.values()), color=["C0", "C1"] * 2 + ["C2", "C2", "C7", "C7"])
ax.bar_label(b, fmt="%.1f %%", fontsize=8)
ax.set_ylabel("CPU load at 300 MHz (%)"); ax.grid(True, axis="y", alpha=0.3)
ax.set_title("Measured CPU load: live = codec running (T6); others = internal.out, no codec")
savefig(fig, "p4_cpu_load.png", "phase4")

# ---------------------------------------------------------------- -O3 vs -O0 (software pipelining)
names = ["DSPLIB fir_gen", "plain-C FIR", "DSPLIB biquad", "plain-C biquad", "own FFT-256", "fftSPxSP",
         "HPF x48", "Mode A x48", "Mode B block"]
idx = [0, 1, 2, 3, 4, 9, 11, 12, 13]
o3b, o0b = (dict(readout(f)) for f in ("lab_bench.txt", "lab_bench_o0.txt"))
c3 = np.array([o3b[f"g_lab.bench[{i}]"] for i in idx])
c0 = np.array([o0b[f"g_lab.bench[{i}]"] for i in idx])
fig, ax = plt.subplots(figsize=(8, 3.5))
w = np.arange(len(idx))
ax.bar(w - 0.2, c3, 0.4, label="-O3"); ax.bar(w + 0.2, c0, 0.4, label="-O0")
for i in range(len(idx)):
    ax.text(i, max(c0[i], c3[i]) * 1.15, f"{c0[i] / c3[i]:.1f}x", ha="center", fontsize=8)
ax.set_yscale("log"); ax.set_xticks(w, names, rotation=30, ha="right", fontsize=8)
ax.set_ylabel("cycles"); ax.legend(); ax.grid(True, axis="y", alpha=0.3)
ax.set_title("lab_bench on the board: -O0 / -O3 cycle ratio (DSPLIB is precompiled, so ~1x)")
savefig(fig, "p4_o0_vs_o3.png", "phase4")

print("Loads (%): " + ", ".join(f"{k} {v:.1f}" for k, v in bars.items()))
print(f"Max |board gain - design|: {np.max(np.abs(board - design)):.3f} dB; "
      f"max |design - target|: A {np.max(np.abs(design[0] - target)):.2f} dB, B {np.max(np.abs(design[1] - target)):.2f} dB")
print("Figures written to results/phase4/")
