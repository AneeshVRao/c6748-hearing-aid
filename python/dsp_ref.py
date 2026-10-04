"""Verified Python reference for every signal-processing block of the hearing aid.

Every other script (experiments, test-vector export, C comparison) imports this file,
so there is exactly one definition of each filter, gain table and processing chain.

Design values follow research/REVIEW.md section c (final spec). Run this file directly
for its self-check:  python python/dsp_ref.py
"""
from pathlib import Path
import sys
import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")           # Windows console defaults to cp1252
sys.path.insert(0, str(ROOT / "research" / "calc"))
from audiograms import AUDIOGRAMS, FREQS, band_gains_db, gain_curve_db  # noqa: E402  (pack module, reused)

FS = 48000.0
K = 4                                   # split levels -> 5 bands
NG, BETA_G = 21, 4.5                    # G: band-split / anti-alias lowpass, cut fs_k/8
NF, BETA_F = 31, 4.5                    # F: half-band anti-image filter after up-sampling
DG, DF = (NG - 1) // 2, (NF - 1) // 2   # group delays 10 and 15 samples
M_B, L_B, N_FFT = 129, 128, 256         # Mode B: FIR length, new samples per block, FFT size
LIMIT = 10 ** (-1 / 20)                 # output limiter ceiling, -1 dBFS (DESIGN CHOICE)

# ---------------------------------------------------------------- filters
G = signal.firwin(NG, 0.25, window=("kaiser", BETA_G))          # cutoff fs/8 (0.25 x Nyquist)
F = signal.firwin(NF, 0.5, window=("kaiser", BETA_F))           # half-band, cutoff fs/4
F[np.abs(F) < 1e-12] = 0.0                                       # exact half-band zeros
HPF_SOS = signal.butter(4, 100, "highpass", fs=FS, output="sos")  # bilinear, pre-warped

# path delay at each level, in samples at that level's rate: T_k = 10 + 15 + 2 T_{k+1}
T_LEVEL = [0] * (K + 1)
for _k in range(K - 1, -1, -1):
    T_LEVEL[_k] = DG + DF + 2 * T_LEVEL[_k + 1]
ALIGN = [T_LEVEL[k] - DG for k in range(K)]                      # 365, 165, 65, 15
assert T_LEVEL[0] == 375 and ALIGN == [365, 165, 65, 15]

# ---------------------------------------------------------------- gain presets
# Order matches the board's button S3: N3 half (default) -> N2 half -> Bisgaard S2 half -> bypass
PRESETS = {"N3": ("N3", 0.5), "N2": ("N2", 0.5), "S2": ("S2", 0.5), "bypass": (None, 0.0)}


def band_gains(preset):
    """Mode A band gains in dB, order B5 (top) ... B1 (residual)."""
    aud, fac = PRESETS[preset]
    return np.zeros(K + 1) if aud is None else np.array(band_gains_db(AUDIOGRAMS[aud], fac))


def target_db(preset, f):
    """Per-frequency target: factor x interpolated HL, capped at 30 dB (research/audiogram.md)."""
    aud, fac = PRESETS[preset]
    f = np.atleast_1d(np.asarray(f, float))
    return np.zeros_like(f) if aud is None else gain_curve_db(AUDIOGRAMS[aud], f, fac)


def freq_sampling_fir(gain_db_at_bins, M=M_B):
    """Type I linear-phase FIR by frequency sampling (M odd).
    gain_db_at_bins: (M+1)/2 magnitudes in dB at f_k = k fs / M."""
    Hk = 10 ** (np.asarray(gain_db_at_bins) / 20)
    a = (M - 1) / 2
    k = np.arange(1, len(Hk))
    n = np.arange(M)[:, None]
    return (Hk[0] + 2 * np.sum(Hk[1:] * np.cos(2 * np.pi * k * (n - a) / M), axis=1)) / M


def mode_b_fir(preset):
    fk = np.arange((M_B + 1) // 2) * FS / M_B
    return freq_sampling_fir(target_db(preset, fk))


def mode_b_H(preset):
    """H[k] = FFT-256 of the zero-padded 129-tap FIR (what the board stores)."""
    return np.fft.fft(mode_b_fir(preset), N_FFT)


# ---------------------------------------------------------------- blocks
def delay(x, d):
    return np.concatenate([np.zeros(d), x[: len(x) - d]])


def hpf(x):
    return signal.sosfilt(HPF_SOS, x)          # SciPy sosfilt = cascaded DF-II transposed


def mode_a(x, gains_db):
    """Mode A filter bank, vectorised. gains_db order B5..B1. Output length = input length."""
    g = 10 ** (np.asarray(gains_db) / 20)
    bands, xk = [], np.asarray(x, float)
    for k in range(K):
        gx = signal.lfilter(G, 1, xk)
        bands.append(delay(xk, DG) - gx)       # complementary high band at level k
        xk = gx[::2]                           # decimate by 2 (keep even samples)
    y = g[K] * xk                              # residual band B1 at fs/16
    for k in range(K - 1, -1, -1):
        up = np.zeros(len(bands[k]))
        up[::2] = y                            # up-sample by 2 (zeros at odd samples)
        yi = 2 * signal.lfilter(F, 1, up)      # anti-image, gain 2
        y = g[k] * delay(bands[k], ALIGN[k]) + yi
    return y


class ModeAStream:
    """Per-sample Mode A with power-of-2 circular buffers: the blueprint for c/modeA_bank.c.
    Same arithmetic as mode_a(); differences are float rounding only."""

    XB, YB = 32, 16                            # G input history, F (half-band) input history
    AB = [512, 256, 128, 16]                   # alignment delay lines (>= ALIGN[k] + 1)

    def __init__(self, gains_db):
        self.g = 10 ** (np.asarray(gains_db) / 20)
        self.xh = np.zeros((K, self.XB))       # x_k history (for G and the z^-10 tap)
        self.yh = np.zeros((K, self.YB))       # y_{k+1} history (half-band input, no zeros stored)
        self.ab = [np.zeros(n) for n in self.AB]
        self.ix = [0] * K                      # write index into xh
        self.iy = [0] * K                      # write index into yh
        self.ia = [0] * K                      # write index into ab
        self.t = 0                             # input sample counter
        self.Fe = F[0::2]                      # even taps (16) used when the level time is even
        self.Fc = F[DF]                        # centre tap (0.5); all other odd taps are zero

    def _analysis(self, k, xin):
        i = self.ix[k] = (self.ix[k] + 1) & (self.XB - 1)
        h = self.xh[k]
        h[i] = xin
        gx = sum(G[j] * h[(i - j) & (self.XB - 1)] for j in range(NG))
        b = h[(i - DG) & (self.XB - 1)] - gx
        a = self.ia[k] = (self.ia[k] + 1) & (self.AB[k] - 1)
        self.ab[k][a] = b
        return gx

    def _synthesis(self, k, even, ynext):
        """Level k output at its current time. even: level time is even, so y_{k+1} has a new sample."""
        if even:
            j = self.iy[k] = (self.iy[k] + 1) & (self.YB - 1)
            self.yh[k][j] = ynext
            yi = 2 * sum(self.Fe[m] * self.yh[k][(j - m) & (self.YB - 1)] for m in range(len(self.Fe)))
        else:   # odd time: only the centre tap F[15] meets a non-zero up-sampled input, y_{k+1} 7 samples back
            j = self.iy[k]
            yi = 2 * self.Fc * self.yh[k][(j - DF // 2) & (self.YB - 1)]
        a = self.ia[k]
        bd = self.ab[k][(a - ALIGN[k]) & (self.AB[k] - 1)]
        return self.g[k] * bd + yi

    def process(self, xin):
        n = self.t
        self.t += 1
        # analysis: level k is active when n is a multiple of 2^k
        xk, depth = xin, 0
        gxs = []
        for k in range(K):
            gxs.append(self._analysis(k, xk))
            depth = k
            if (n >> k) & 1:                   # level k time is odd: its lowpass is not passed down
                break
            xk = gxs[-1]
        else:
            depth = K                          # all levels even -> residual gets a new sample
        # synthesis, deepest first
        ynext = self.g[K] * xk if depth == K else 0.0
        for k in range(min(depth, K - 1), -1, -1):
            even = ((n >> k) & 1) == 0
            ynext = self._synthesis(k, even, ynext)
        return ynext

    def run(self, x):
        return np.array([self.process(v) for v in x])


def ola(x, h, L=L_B, N=N_FFT):
    """Overlap-add fast convolution, block by block as on the board. Output length = input length."""
    assert L + len(h) - 1 <= N, "N too small: circular convolution would alias in time"
    H = np.fft.fft(h, N)
    nb = -(-len(x) // L)
    xp = np.concatenate([x, np.zeros(nb * L - len(x))])
    y = np.zeros(nb * L + N)
    for b in range(nb):
        seg = np.fft.ifft(np.fft.fft(xp[b * L:(b + 1) * L], N) * H).real
        y[b * L:b * L + N] += seg
    return y[: len(x)]


def ols(x, h, N=N_FFT):
    """Overlap-save: keep the last N-M+1 outputs of each circular convolution."""
    M = len(h)
    L = N - M + 1
    H = np.fft.fft(h, N)
    xp = np.concatenate([np.zeros(M - 1), x, np.zeros(L)])
    y = []
    for s in range(0, len(x), L):
        y.append(np.fft.ifft(np.fft.fft(xp[s:s + N], N) * H).real[M - 1:])
    return np.concatenate(y)[: len(x)]


def mode_b(x, preset):
    return ola(np.asarray(x, float), mode_b_fir(preset))


def limiter(y, lim=LIMIT):
    """Hard limiter (maximum power output). Returns output and number of clipped samples."""
    return np.clip(y, -lim, lim), int(np.sum(np.abs(y) > lim))


def chain(x, mode, preset):
    """Full board chain: HPF -> Mode A or B -> limiter. x is float, full scale = 1.0."""
    v = hpf(x)
    v = mode_a(v, band_gains(preset)) if mode == "A" else mode_b(v, preset)
    return limiter(v)[0]


# ---------------------------------------------------------------- FFT from scratch and Goertzel
def bitrev(n):
    bits = n.bit_length() - 1
    return np.array([int(f"{i:0{bits}b}"[::-1], 2) for i in range(n)])


def fft_dit(x, count=None):
    """Iterative radix-2 decimation-in-time FFT: bit-reverse the input, then log2 N butterfly stages.
    count (dict, optional) collects the number of non-trivial twiddle multiplies."""
    x = np.asarray(x, complex)[bitrev(len(x))]
    N = len(x)
    size = 2
    while size <= N:
        half = size // 2
        for k in range(half):
            w = np.exp(-2j * np.pi * k / size)
            if count is not None and k not in (0, size // 4):     # W^0 = 1 and W^(N/4) = -j are free
                count["mul"] = count.get("mul", 0) + N // size
            for s in range(0, N, size):
                a, b = x[s + k], w * x[s + k + half]
                x[s + k], x[s + k + half] = a + b, a - b
        size *= 2
    return x


def fft_dif(x):
    """Iterative radix-2 decimation-in-frequency FFT: butterflies first, bit-reversed output reordered."""
    x = np.asarray(x, complex).copy()
    N = len(x)
    size = N
    while size >= 2:
        half = size // 2
        for k in range(half):
            w = np.exp(-2j * np.pi * k / size)
            for s in range(0, N, size):
                a, b = x[s + k], x[s + k + half]
                x[s + k], x[s + k + half] = a + b, (a - b) * w
        size //= 2
    return x[bitrev(N)]


def goertzel(x, f, fs=FS):
    """Amplitude of the tone at f (one DFT bin, second-order recursion)."""
    N = len(x)
    k = f * N / fs
    assert k == int(k), "tone not on a DFT bin: choose N so that f N / fs is an integer"
    c = 2 * np.cos(2 * np.pi * k / N)
    s1 = s2 = 0.0
    for v in x:
        s1, s2 = v + c * s1 - s2, s1
    power = s1 * s1 + s2 * s2 - c * s1 * s2
    return 2 * np.sqrt(power) / N


# ---------------------------------------------------------------- measurement helpers
def tone_gain(process, ft, amp=0.01, fs=FS):
    """Steady-state gain (dB) and residual spurs (dBc) of process() for a 1 s tone; same method as research/calc."""
    t = np.arange(int(fs)) / fs
    x = amp * np.sin(2 * np.pi * ft * t)
    y = process(x)
    seg, ref = y[8000:8000 + 38400], x[:38400]
    win = np.hanning(len(seg))
    Y, X = np.fft.rfft(seg * win), np.fft.rfft(ref * win)
    i0 = int(round(ft * len(seg) / fs))
    sp, xp = np.sum(np.abs(Y[i0 - 3:i0 + 4]) ** 2), np.sum(np.abs(X[i0 - 3:i0 + 4]) ** 2)
    return 10 * np.log10(sp / xp), 10 * np.log10((np.sum(np.abs(Y) ** 2) - sp) / sp)


TEST_F = list(FREQS) + [8000.0]     # 11 audiometric test frequencies


def savefig(fig, name, sub="phase1"):
    out = ROOT / "results" / sub
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / name, dpi=120, bbox_inches="tight")


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    x = rng.standard_normal(3000) * 0.1
    gd = band_gains("N3")
    # streaming per-sample bank == vectorised bank
    e = np.max(np.abs(ModeAStream(gd).run(x) - mode_a(x, gd)))
    assert e < 1e-12, e
    # impulse peak at 375 with unity gains
    imp = np.zeros(2048); imp[0] = 1
    assert int(np.argmax(np.abs(mode_a(imp, np.zeros(5))))) == 375
    # OLA and OLS == direct convolution
    h = mode_b_fir("N3")
    ref = signal.lfilter(h, 1, x)
    assert np.max(np.abs(ola(x, h) - ref)) < 1e-12 and np.max(np.abs(ols(x, h) - ref)) < 1e-12
    # own FFTs == numpy
    z = rng.standard_normal(256) + 1j * rng.standard_normal(256)
    assert np.max(np.abs(fft_dit(z) - np.fft.fft(z))) < 1e-9
    assert np.max(np.abs(fft_dif(z) - np.fft.fft(z))) < 1e-9
    print(f"dsp_ref self-check OK (stream vs vector max err {e:.2e})")
