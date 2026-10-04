"""Phase 2, part 2: data-path arithmetic, float32 vs Q15 (16-bit fixed point).

1. HPF biquads in DF-I, DF-II and DF-II-T with true float32 arithmetic, and DF-I in Q15
   (Q1.14 coefficients, Q15 data, wide accumulator, one rounding per output, saturation).
2. Mode A and Mode B, float32 vs Q15, SNR against the float64 reference, speech at -40 dBFS RMS.
3. Overflow: how much headroom 30 dB of gain needs in a 16-bit path (test T10 / research/06 Stage 2).
SNR = 10 log10(sum ref^2 / sum (y - ref)^2), ref = the float64 result of the same structure.
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dsp_ref import F, FS, G, HPF_SOS, L_B, N_FFT, ROOT, band_gains, mode_a, mode_b_fir, ola, savefig

f32 = np.float32


def q15(v):
    return np.clip(np.round(np.asarray(v) * 32768), -32768, 32767) / 32768


def qc(z):
    return q15(z.real) + 1j * q15(z.imag)


def snr(y, ref):
    return 10 * np.log10(np.sum(ref ** 2) / np.sum((np.asarray(y, float) - ref) ** 2))


_, sp = wavfile.read(ROOT / "data" / "speech_48k.wav")
speech = sp[: 4 * 48000].astype(float) / 32768
speech /= np.sqrt(np.mean(speech ** 2))                    # unit RMS; scale per test below


def at_dbfs(x, dbfs):
    return q15(x * 10 ** (dbfs / 20))                       # every test input is a 16-bit codec sample


# ================================================================= 1. HPF forms
def biquad_f32(x, sec, form):
    b0, b1, b2, _, a1, a2 = (f32(c) for c in sec)
    y = np.empty(len(x), f32)
    if form == "DF-I":
        x1 = x2 = y1 = y2 = f32(0)
        for n, v in enumerate(x.astype(f32)):
            out = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            x2, x1, y2, y1 = x1, v, y1, out
            y[n] = out
    elif form == "DF-II":
        w1 = w2 = f32(0)
        for n, v in enumerate(x.astype(f32)):
            w0 = v - a1 * w1 - a2 * w2
            y[n] = b0 * w0 + b1 * w1 + b2 * w2
            w2, w1 = w1, w0
    else:                                                   # DF-II transposed
        s1 = s2 = f32(0)
        for n, v in enumerate(x.astype(f32)):
            out = b0 * v + s1
            s1 = b1 * v - a1 * out + s2
            s2 = b2 * v - a2 * out
            y[n] = out
    return y


def biquad_q15_df1(x, sec):
    """Q15 data, Q1.14 coefficients, products summed exactly (Q29), rounded once, saturated."""
    c = [int(round(v * 2 ** 14)) for v in sec]
    b0, b1, b2, _, a1, a2 = c
    xi = [int(v) for v in np.round(x * 32768)]
    x1 = x2 = y1 = y2 = 0
    y = np.empty(len(xi))
    for n, v in enumerate(xi):
        acc = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out = max(-32768, min(32767, (acc + (1 << 13)) >> 14))
        x2, x1, y2, y1 = x1, v, y1, out
        y[n] = out
    return y / 32768


xh = at_dbfs(speech[: 2 * 48000], -20)
ref = signal.sosfilt(HPF_SOS, xh)
print("1. HPF (2 biquads), speech at -20 dBFS RMS, 2 s: SNR vs float64")
hpf_snr = {}
for form in ("DF-I", "DF-II", "DF-II-T"):
    y = xh
    for sec in HPF_SOS:
        y = biquad_f32(y, sec, form)
    hpf_snr[f"float32 {form}"] = snr(y, ref)
y = xh
for sec in HPF_SOS:
    y = biquad_q15_df1(y, sec)
hpf_snr["Q15 DF-I"] = snr(y, ref)
floor16 = -20 * np.log10(32768 * np.sqrt(12))                # 16-bit rounding noise of the codec, -101.2 dBFS
for k, v in hpf_snr.items():
    print(f"   {k:18s} SNR {v:6.1f} dB -> arithmetic noise {-20 - v:7.1f} dBFS (codec 16-bit floor {floor16:.1f} dBFS)")
assert hpf_snr["float32 DF-II-T"] >= max(hpf_snr["float32 DF-I"], hpf_snr["float32 DF-II"])   # research/03 assumption
assert min(v for k, v in hpf_snr.items() if k.startswith("float32")) > hpf_snr["Q15 DF-I"] + 20

# ================================================================= 2. Mode A and Mode B
gd = band_gains("N3")
g_lin = 10 ** (gd / 20)
xa = at_dbfs(speech, -40)
refA = mode_a(xa, gd)
yA32 = mode_a(xa, gd, q=lambda v: np.asarray(v, f32).astype(float))
yA16 = mode_a(xa, gd, g_coef=q15(G), f_coef=q15(F),
              gain_lin=np.round(g_lin * 2 ** 10) / 2 ** 10,     # gains as Q5.10 words (max 31.999)
              q=q15)


def fft_q15(X, inverse=False, scale=True):
    """Radix-2 DIT on rows of X, Q15 twiddles, every butterfly output rounded to Q15 and saturated;
    scale=True halves every stage (overall 1/N), the usual way to avoid overflow."""
    N = X.shape[1]
    bits = N.bit_length() - 1
    rev = np.array([int(f"{i:0{bits}b}"[::-1], 2) for i in range(N)])
    X = X[:, rev]
    size = 2
    while size <= N:
        half = size // 2
        Wt = qc(np.exp((2j if inverse else -2j) * np.pi * np.arange(half) / size))
        Y = X.reshape(X.shape[0], N // size, size)
        a, b = Y[..., :half], qc(Y[..., half:] * Wt)
        top, bot = a + b, a - b
        if scale:
            top, bot = top / 2, bot / 2
        X = qc(np.concatenate([top, bot], axis=2)).reshape(X.shape[0], N)
        size *= 2
    return X


def mode_b_q15(x, h):
    """Q15 OLA: forward FFT scaled 1/256, H stored as H/32 in Q15, inverse unscaled, x32 at the end."""
    H = qc(np.fft.fft(h, N_FFT) / 32)
    nb = len(x) // L_B
    blocks = np.zeros((nb, N_FFT), complex)
    blocks[:, :L_B] = x[: nb * L_B].reshape(nb, L_B)
    Xf = fft_q15(blocks, scale=True)                         # = X / 256
    Yb = fft_q15(qc(Xf * H), inverse=True, scale=False).real  # = (x * h) / 32 per block
    y = np.zeros(nb * L_B + N_FFT)
    for b in range(nb):
        y[b * L_B:b * L_B + N_FFT] = q15(y[b * L_B:b * L_B + N_FFT] + Yb[b])
    return q15(32 * y[: nb * L_B])


h = mode_b_fir("N3")
n = len(xa) // L_B * L_B
refB = ola(xa[:n], h)
X32 = np.fft.fft(np.pad(xa[:n].astype(f32).reshape(-1, L_B), ((0, 0), (0, N_FFT - L_B))), axis=1)
assert X32.dtype == np.complex64                             # NumPy 2 keeps single precision
Yb32 = np.fft.ifft(X32 * np.fft.fft(h, N_FFT).astype(np.complex64), axis=1).real
yB32 = np.zeros(n + N_FFT, f32)
for b in range(n // L_B):
    yB32[b * L_B:b * L_B + N_FFT] += Yb32[b]
yB32 = yB32[:n]
yB16 = mode_b_q15(xa[:n], h)

# Note: Mode A float32 rounds every stored result to float32 but lfilter accumulates in float64,
# so it is an upper bound; the exact float32 figure comes from the C build in Phase 3.
res = {"HPF": (hpf_snr["float32 DF-II-T"], hpf_snr["Q15 DF-I"]),
       "Mode A": (snr(yA32, refA), snr(yA16, refA)),
       "Mode B": (snr(yB32, refB), snr(yB16, refB))}
print("\n2. SNR vs float64 (speech; HPF at -20 dBFS, Modes A/B at -40 dBFS RMS, N3 gains):")
print("   block     float32     Q15")
for k, (a, b) in res.items():
    print(f"   {k:8s} {a:7.1f} dB {b:7.1f} dB")
assert all(a > 60 for a, _ in res.values())                  # float32 is far below the 16-bit codec noise
assert res["Mode B"][1] < res["Mode A"][1]                   # per-stage FFT scaling costs Q15 Mode B the most

fig, ax = plt.subplots(figsize=(8, 4))
xi = np.arange(3)
ax.bar(xi - 0.2, [v[0] for v in res.values()], 0.4, label="float32 (board build)")
ax.bar(xi + 0.2, [v[1] for v in res.values()], 0.4, label="Q15")
ax.axhline(6.02 * 16 + 1.76, color="k", ls=":", lw=1, label="ideal 16-bit full-scale sine (98 dB)")
ax.set_xticks(xi, list(res.keys()))
ax.set(ylabel="SNR vs float64, dB", title="Arithmetic noise: float32 vs Q15 (speech input)")
ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")
savefig(fig, "p2_snr_float_vs_q15.png", "phase2")

# ================================================================= 3. overflow / headroom
print("\n3. Overflow with 30 dB gain in a 16-bit path (Mode A, N3; 1 s of speech, and a 4 kHz tone):")
print("   input      speech clips   4 kHz tone clips   Q15 SNR (speech)")
t = np.arange(48000) / FS
for lvl in (-20, -30, -40, -50):
    xs = at_dbfs(speech[:48000], lvl)
    xt = q15(np.sqrt(2) * 10 ** (lvl / 20) * np.sin(2 * np.pi * 4000 * t))   # same RMS as the speech
    ys = mode_a(xs, gd, q=q15)
    yt = mode_a(xt, gd, q=q15)
    cs, ct = int(np.sum(np.abs(ys) >= 32767 / 32768)), int(np.sum(np.abs(yt) >= 32767 / 32768))
    s_ = snr(mode_a(xs, gd, g_coef=q15(G), f_coef=q15(F), gain_lin=np.round(g_lin * 2 ** 10) / 2 ** 10, q=q15),
             mode_a(xs, gd))
    print(f"   {lvl:4d} dBFS  {cs:8d}        {ct:8d}          {s_:6.1f} dB")
    if lvl == -20:
        assert ct > 0                                       # -20 dBFS + 30 dB = +10 dBFS: must clip
    if lvl <= -40:
        assert ct == 0
print("p2_fixed_point OK")
