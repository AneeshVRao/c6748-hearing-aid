"""Phase 4 analysis: board results vs simulation.

  python python/board_compare.py internal out_modeA.dat out_modeB.dat
      IO_INTERNAL memory dumps (CCS Save Memory, TI data format, 32-bit hex) vs the Python reference
  python python/board_compare.py rec T2 rec_modeA.wav [--cal rec_bypass.wav] [--mode A]
  python python/board_compare.py rec T4|T5|T9|T10 rec.wav [--loop loopback.wav]
      live recordings: channel 0 = board LINE OUT, channel 1 = source (Y-cable) if available
  python python/board_compare.py selftest
      fabricates recordings with a known delay and gain and checks that the analysis recovers them

The test files played from the PC are data/board/T*.wav (python/export.py): 0.5 s silence, a marker
click at 0.5 s, 0.5 s silence, then the test signal starting at 1.0 s.
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.io import wavfile
from dsp_ref import FS, ROOT, TEST_F, chain, goertzel, target_db

BOARD = ROOT / "data" / "board"
SIG0 = int(1.0 * FS)                       # test signal starts 1 s into each file
MARK = int(0.5 * FS)                       # marker click


# ---------------------------------------------------------------- inputs
def read_dat(path, as_float=True):
    """CCS 'TI data' memory file: header '1651 1 addr page len', then one 0xXXXXXXXX word per line."""
    lines = Path(path).read_text().split()
    words = np.array([int(w, 16) for w in lines[5:]], dtype=np.uint32)
    return words.view(np.float32).astype(float) if as_float else words.view(np.int32)


def stored_default():
    """The board's default stored signal (board_io.c stored_init), reproduced with C integer semantics."""
    i = np.arange(8000, dtype=np.float32)
    parts = [np.round(32768 * np.float32(0.01414214) * np.sin(np.float32(6.2831853) * np.float32(f) * i / np.float32(48000)))
             for f in TEST_F]
    seed, noise = 12345, []
    for _ in range(96000 - 88000):
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
        v = ((seed >> 16) - 32768) * 328
        noise.append(int(v / 18918))                             # C division truncates toward zero
    return np.concatenate(parts + [np.array(noise, float)]) / 32768


def read_rec(path):
    fs, d = wavfile.read(path)
    assert fs == 48000, f"{path}: record at 48 kHz (got {fs})"
    d = d.astype(float) / (32768.0 if d.dtype == np.int16 else 1.0)
    return (d[:, 0], d[:, 1]) if d.ndim == 2 else (d, None)


def src(test):
    _, d = wavfile.read(BOARD / f"{test}.wav")
    return d[:, 0].astype(float) / 32767


def lag_of(y, x, maxlag=int(0.5 * FS)):
    """Delay of y relative to x (samples) from the cross-correlation peak, with parabolic refinement."""
    n = 1 << int(np.ceil(np.log2(len(x) + len(y))))
    c = np.fft.irfft(np.fft.rfft(y, n) * np.conj(np.fft.rfft(x, n)), n)
    c = np.concatenate([c[-maxlag:], c[:maxlag + 1]])
    k = int(np.argmax(np.abs(c)))
    if 0 < k < len(c) - 1:
        a, b, d = np.abs(c[k - 1:k + 2])
        k = k + 0.5 * (a - d) / (a - 2 * b + d)
    return k - maxlag


def aligned(y, test, ref=None):
    """Return y shifted so that sample 0 is the start of the test file (uses the source channel if present)."""
    x = ref if ref is not None else src(test)
    L = lag_of(y[: 4 * SIG0], x[: 4 * SIG0])
    return np.roll(y, -int(round(L))), L


# ---------------------------------------------------------------- analyses
def internal(fa, fb, fin=None):
    """fin: optional dump of g_stored (the board's actual input). Without it the input is rebuilt in
    Python; TI's sinf may round a few samples to a different 16-bit value, so prefer the dump."""
    x = read_dat(fin, as_float=False).astype(float) / 32768 if fin else stored_default()
    print(f"IO_INTERNAL dumps vs Python reference (preset N3), input {'from g_stored dump' if fin else 'rebuilt'}:")
    for name, f, mode, lag in (("Mode A", fa, "A", 0), ("Mode B", fb, "B", 256)):
        y = read_dat(f)[: len(x)]
        ref = chain(x, mode, "N3")
        ref = np.concatenate([np.zeros(lag), ref[: len(ref) - lag]])
        e = np.max(np.abs(y - ref))
        gains = [20 * np.log10(goertzel(y[t * 8000 + 2000:t * 8000 + 6608], f0) /
                               goertzel(x[t * 8000 + 2000:t * 8000 + 6608], f0)) for t, f0 in enumerate(TEST_F)]
        print(f"  {name}: max |board - Python| = {e:.2e} ({'PASS' if e < 1e-4 else 'FAIL'}, gate 1e-4)")
        print("    gains: " + "  ".join(f"{f0:.0f}:{g:.2f}" for f0, g in zip(TEST_F, gains)))


def tone_levels(y, freqs, seg=int(FS), skip=int(0.25 * FS), n=4608):
    """Level (amplitude) of each 1 s tone segment, Goertzel over 4608 samples after a 0.25 s settle."""
    return np.array([goertzel(y[SIG0 + i * seg + skip: SIG0 + i * seg + skip + n], f) for i, f in enumerate(freqs)])


def t2(rec, cal=None, mode="A", preset="N3"):
    y, ref = read_rec(rec)
    y, _ = aligned(y, "T2_tones", ref)
    out = tone_levels(y, TEST_F)
    if cal:
        yc, refc = read_rec(cal)
        yc, _ = aligned(yc, "T2_tones", refc)
        base = tone_levels(yc, TEST_F)                     # bypass: codec + sound card path without gain
    else:
        x = ref if ref is not None else src("T2_tones")
        x = np.roll(x, -int(round(lag_of(x[:4 * SIG0], src("T2_tones")[:4 * SIG0])))) if ref is not None else x
        base = tone_levels(x, TEST_F)
    g = 20 * np.log10(out / base)
    sim = [20 * np.log10(goertzel(chain(src("T2_tones"), mode, preset)[SIG0 + i * int(FS) + int(0.25 * FS):][:4608], f) /
                         goertzel(src("T2_tones")[SIG0 + i * int(FS) + int(0.25 * FS):][:4608], f)) for i, f in enumerate(TEST_F)]
    tgt = target_db(preset, TEST_F)
    print(f"T2 band gains, Mode {mode}, {preset} ({'bypass-calibrated' if cal else 'vs source'}):")
    print("    Hz   measured  simulated  target   meas-sim")
    for f, a, s, t in zip(TEST_F, g, sim, tgt):
        print(f"  {f:6.0f}  {a:7.2f}  {s:8.2f}  {t:7.2f}   {a - s:+6.2f}")
    worst = np.max(np.abs(g - np.array(sim)))
    print(f"  max |measured - simulated| = {worst:.2f} dB ({'PASS' if worst <= 1.0 else 'FAIL'}, research/07 T2 gate 1 dB)")
    return g


def t4(rec):
    y, ref = read_rec(rec)
    assert ref is not None, "T4 needs the source on channel 1"
    L = int(round(lag_of(y, ref)))                         # remove the bulk delay: it biases Welch coherence
    y, ref = y[L:], ref[:len(ref) - L]
    y, ref = y[SIG0:len(y) - int(0.5 * FS)], ref[SIG0:len(ref) - int(0.5 * FS)]   # noise part only, no lead/tail
    f, Pxy = signal.csd(ref, y, FS, nperseg=8192)
    _, Pxx = signal.welch(ref, FS, nperseg=8192)
    _, C = signal.coherence(ref, y, FS, nperseg=8192)
    band = (f >= 100) & (f <= 10000)
    print(f"T4: min coherence 100 Hz-10 kHz = {C[band].min():.3f} ({'PASS' if C[band].min() > 0.9 else 'FAIL'}, gate 0.9)")
    return f, 20 * np.log10(np.abs(Pxy / Pxx) + 1e-12), C


def t5(rec, loop=None):
    y, ref = read_rec(rec)
    if ref is not None:                                    # source on channel 1: direct measurement
        L = lag_of(y, ref)
        how = "board output vs source channel"
    else:
        L = lag_of(y, src("T5_clicks"))
        how = "board output vs file"
        if loop:
            yl, _ = read_rec(loop)
            L -= lag_of(yl, src("T5_clicks"))
            how += " minus loopback cable recording"
    print(f"T5 latency ({how}): {L:.1f} samples = {L / FS * 1e3:.2f} ms")
    return L / FS * 1e3


def t9(rec):
    y, ref = read_rec(rec)
    y, _ = aligned(y, "T9_spur_tones", ref)
    # Gate on the largest discrete spur (aliases, images, harmonics). The total residual at -40 dBFS is
    # dominated by the 16-bit noise floor, so it is printed for information only.
    print("T9 crossover spurs: largest single component / total residual (0.1-20 kHz), dBc")
    worst = -999
    for i, f in enumerate((700, 760, 1450, 1550, 2950, 3050, 5900, 6100)):
        # 0.5 s window: a whole number of cycles of every T9 tone. Blackman-Harris and +-8 bins tolerate
        # a sound card whose clock differs slightly from the codec's.
        seg = y[SIG0 + i * int(FS) + int(0.25 * FS):][:24000]
        Y = np.abs(np.fft.rfft(seg * signal.windows.blackmanharris(len(seg)))) ** 2
        fr = np.fft.rfftfreq(len(seg), 1 / FS)
        k = int(round(f * len(seg) / FS))
        sig_p = Y[k - 8:k + 9].sum()
        band = (fr > 100) & (fr < 20000)
        total = 10 * np.log10((Y[band].sum() - sig_p) / sig_p)
        far = band & (np.abs(fr - f) > 20)
        j = int(np.argmax(np.where(far, Y, 0)))
        s = 10 * np.log10(Y[j] / Y[k])
        worst = max(worst, s)
        print(f"  {f:5d} Hz: largest {s:6.1f} dBc at {fr[j]:7.1f} Hz   (total residual {total:6.1f} dBc)")
    print(f"  worst single spur {worst:.1f} dBc ({'PASS' if worst <= -60 else 'FAIL'}, research/07 T9 gate -60 dBc)")
    return worst


def t10(rec):
    y, ref = read_rec(rec)
    y, _ = aligned(y, "T10_level_steps", ref)
    print("T10 limiter: output peak per 1 kHz input step")
    for i, lvl in enumerate(range(-40, 1, 5)):
        seg = y[SIG0 + i * int(FS) + int(0.25 * FS):][:24000]
        print(f"  input {lvl:4d} dBFS RMS -> output peak {20 * np.log10(np.max(np.abs(seg)) + 1e-12):6.1f} dBFS")


# ---------------------------------------------------------------- self-test on fabricated recordings
def selftest():
    rng = np.random.default_rng(0)
    out = ROOT / "results" / "phase4_selftest"
    out.mkdir(parents=True, exist_ok=True)
    true_ms, card = 8.81, 10 ** (-3 / 20)                   # board latency, sound-card gain -3 dB
    lag = int(round(true_ms * FS / 1000)) - 375            # chain() already contains the 375-sample bank delay
    def fake(test, mode, preset, ref=True):
        x = src(test)
        y = card * chain(x, mode, preset)
        y = np.concatenate([np.zeros(lag), y[:-lag]]) + 1e-5 * rng.standard_normal(len(y))
        d = np.stack([y, card * x], 1) if ref else y
        p = out / f"{test}_{mode}_{preset}{'' if ref else '_mono'}.wav"
        wavfile.write(p, 48000, d.astype(np.float32))
        return p
    # IO_INTERNAL path: write .dat dumps as CCS would (float32 words) and read them back
    x = stored_default()
    xi = np.round(x * 32768).astype(np.int32)
    def dat(name, words):
        (out / name).write_text(f"1651 1 c0000000 0 {len(words):x}\n" +
                                "".join(f"0x{w:08X}\n" for w in words.view(np.uint32).tolist()))
        return out / name
    ya = chain(x, "A", "N3").astype(np.float32)
    yb = np.concatenate([np.zeros(256), chain(x, "B", "N3")[:-256]]).astype(np.float32)
    internal(dat("out_modeA.dat", ya), dat("out_modeB.dat", yb), dat("g_stored.dat", xi))
    assert np.array_equal(read_dat(out / "g_stored.dat", as_float=False), xi)
    g = t2(fake("T2_tones", "A", "N3"), cal=fake("T2_tones", "A", "bypass"))
    sim = np.array([17.40, 17.41, 17.65, 19.03, 20.66, 23.33, 25.60, 28.02, 29.66, 30.00, 30.00])
    assert np.max(np.abs(g - sim)) < 0.1, g
    ms = t5(fake("T5_clicks", "A", "N3"))
    assert abs(ms - true_ms) < 0.05, ms
    _, _, C = t4(fake("T4_noise", "B", "N3"))
    assert C[(np.arange(len(C)) * FS / 8192 >= 100) & (np.arange(len(C)) * FS / 8192 <= 10000)].min() > 0.9
    assert t9(fake("T9_spur_tones", "A", "N3")) < -60
    print("board_compare self-test OK: gains within 0.1 dB, latency within 0.05 ms, coherence > 0.9, spurs < -60 dBc")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "selftest":
        selftest()
    elif a[0] == "internal":
        internal(a[1], a[2], a[3] if len(a) > 3 else None)
    elif a[0] == "rec":
        opt = {a[i]: a[i + 1] for i in range(3, len(a) - 1, 2)}
        {"T2": lambda: t2(a[2], opt.get("--cal"), opt.get("--mode", "A"), opt.get("--preset", "N3")),
         "T4": lambda: t4(a[2]), "T5": lambda: t5(a[2], opt.get("--loop")),
         "T9": lambda: t9(a[2]), "T10": lambda: t10(a[2])}[a[1]]()
