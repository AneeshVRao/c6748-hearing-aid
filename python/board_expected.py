"""Expected values for the board's IO_INTERNAL run (docs/board_checklist.md step 2):
replays the board's default stored signal (board_io.c stored_init) through the Python reference and
measures each tone with the same Goertzel windows as main.c run_internal(). Writes
results/phase3/board_expected.txt.   Run: python python/board_expected.py
"""
import numpy as np
from dsp_ref import ROOT, TEST_F, chain, goertzel

i = np.arange(8000)
tones = [np.round(32768 * np.float32(0.01414214) * np.sin(np.float32(6.2831853) * np.float32(f) * i.astype(np.float32)
                                                          / np.float32(48000))).astype(np.int32) for f in TEST_F]
x = np.concatenate(tones + [np.zeros(8000, np.int32)]).astype(float) / 32768   # noise part not used here

lines = ["Expected g_int[m].gain_db (dB), IO_INTERNAL, preset N3, board default stored tones (-40 dBFS RMS)",
         "   Hz    Mode A g_int[0]   Mode B g_int[1]"]
res = {}
for m, mode in enumerate("AB"):
    y = chain(x, mode, "N3")
    if mode == "B":                       # the board's Mode B output lags by the 2-block buffering (256 samples)
        y = np.concatenate([np.zeros(256), y[:-256]])
    res[mode] = []
    for t, f in enumerate(TEST_F):
        s0 = t * 8000 + 2000
        res[mode].append(20 * np.log10(goertzel(y[s0:s0 + 4608], f) / goertzel(x[s0:s0 + 4608], f)))
for t, f in enumerate(TEST_F):
    lines.append(f"{f:6.0f}   {res['A'][t]:10.2f}        {res['B'][t]:10.2f}")
lines.append("Pass: board within 0.05 dB of these (float32 board vs float64 Python; the PC C build matches Python to 2e-5 of full scale).")
out = ROOT / "results" / "phase3"
out.mkdir(parents=True, exist_ok=True)
(out / "board_expected.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
