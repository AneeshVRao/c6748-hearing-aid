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


def mode_a(x, gains_db, g_coef=None, f_coef=None, gain_lin=None, q=None):
    """Mode A filter bank, vectorised. gains_db order B5..B1. Output length = input length.
    Optional hooks for the fixed-point study (python/p2_fixed_point.py): quantised coefficients
    g_coef/f_coef/gain_lin, and q() applied to every stored intermediate result."""
    Gc = G if g_coef is None else g_coef
    Fc = F if f_coef is None else f_coef
    g = 10 ** (np.asarray(gains_db) / 20) if gain_lin is None else gain_lin
    q = q or (lambda v: v)
    bands, xk = [], np.asarray(x, float)
    for k in range(K):
        gx = q(signal.lfilter(Gc, 1, xk))
        bands.append(q(delay(xk, DG) - gx))    # complementary high band at level k
        xk = gx[::2]                           # decimate by 2 (keep even samples)
    y = q(g[K] * xk)                           # residual band B1 at fs/16
    for k in range(K - 1, -1, -1):
        up = np.zeros(len(bands[k]))
        up[::2] = y                            # up-sample by 2 (zeros at odd samples)
        yi = q(2 * signal.lfilter(Fc, 1, up))  # anti-image, gain 2
        y = q(q(g[k] * delay(bands[k], ALIGN[k])) + yi)
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


# ---------------------------------------------------------------- extras: feedback notch, noise suppression
# Both are OFF by default; chain(x, mode, preset) is unchanged. All values below are DESIGN CHOICES.
NOTCH_Q = 10.0                   # -3 dB bandwidth = f0 / Q
HOWL_LO, HOWL_HI = 500.0, 8000.0 # search range of the howl detector (Hz)
HOWL_PAPR_DB = 25.0              # peak must stand this far above the mean of the range (main lobe +-5 bins excluded)
HOWL_HOLD = 75                   # leaky count of such blocks (same bin +-1): +1 per hit, -1 per miss; trigger at 75
HOWL_FLOOR = 1e-8                # blocks quieter than -80 dBFS mean power are ignored
HOWL_MAX = 2                     # at most two notches
NR_TAU_P, NR_TAU_G = 0.010, 0.020   # power smoothing, gain smoothing time constants (s)
NR_SUB, NR_NSUB = 0.375, 4       # noise floor = minimum of the smoothed power over 4 x 0.375 s = 1.5 s
NR_BETA = 2.0                    # over-subtraction factor
NR_GMIN = 10 ** (-12 / 20)       # gain floor (-12 dB): limits speech distortion and musical noise
# Bias of the minimum (E[P] / E[min P]) on stationary white noise, per Mode A band B5..B1 and for the
# Mode B frequency samples. Measured by nr_bias() (python/p3_notch_nr.py checks they are current).
NR_BIAS_A = [1.194, 1.427, 1.717, 2.069, 2.305]
NR_BIAS_B = 2.233


def notch_coeffs(f0, Q=NOTCH_Q, fs=FS):
    """2nd-order notch by the bilinear transform of H(s) = (s^2 + w0^2)/(s^2 + (w0/Q)s + w0^2), pre-warped at f0.
    Returns [b0 b1 b2 a0 a1 a2]; zeros exactly on the unit circle at f0."""
    K = np.tan(np.pi * f0 / fs)
    n = 1.0 / (1.0 + K / Q + K * K)
    b0, b1 = (1.0 + K * K) * n, 2.0 * (K * K - 1.0) * n
    return np.array([b0, b1, b0, 1.0, b1, (1.0 - K / Q + K * K) * n])


class HowlDetector:
    """Notch-filter-based howling suppression: detect a persistent, dominant spectral peak and notch it.
    One decision per 128-sample block from a Hann-windowed FFT-256 of the block (zero-padded)."""

    def __init__(self):
        self.k_prev, self.count, self.notches = -10, 0, []
        self.win = np.hanning(L_B)
        self.lo, self.hi = int(np.ceil(HOWL_LO * N_FFT / FS)), int(HOWL_HI * N_FFT / FS)

    def block(self, xb):
        """xb: 128 samples. Returns a new notch frequency (Hz) or None."""
        if np.mean(xb * xb) < HOWL_FLOOR:                       # silence: no decision, keep the count
            return None
        P = np.abs(np.fft.fft(xb * self.win, N_FFT)[: N_FFT // 2 + 1]) ** 2
        seg = P[self.lo:self.hi + 1]
        k = int(np.argmax(seg)) + self.lo
        # the Hann main lobe of a 128-sample block spans +-4 bins of the 256-point FFT: exclude +-5
        rest = np.concatenate([P[self.lo:max(k - 5, self.lo)], P[k + 6:self.hi + 1]])
        papr = P[k] / (np.mean(rest) + 1e-30)
        # a sinusoid makes a local peak; a maximum at the range edge is just a sloping (e.g. voiced) spectrum
        local = self.lo < k < self.hi and P[k] > P[k - 1] and P[k] > P[k + 1]
        if abs(k - self.k_prev) > 1:                           # a different candidate: start counting again
            self.count = 0
        hit = local and papr > 10 ** (HOWL_PAPR_DB / 10)
        self.count = self.count + 1 if hit else max(self.count - 1, 0)   # leaky: survives masking by speech
        self.k_prev = k
        if self.count >= HOWL_HOLD and len(self.notches) < HOWL_MAX:
            a, b, c = np.log(P[k - 1:k + 2] + 1e-30)            # parabolic peak refinement
            f0 = (k + 0.5 * (a - c) / (a - 2 * b + c)) * FS / N_FFT
            if all(abs(f0 - f) > f / NOTCH_Q for f in self.notches):
                self.notches.append(f0)
                self.count = 0
                return f0
        return None


def notch_auto(x, events=None):
    """Auto howl notch, block-timed exactly as the board. The detector watches the notch OUTPUT (a notched
    howl disappears from it); block j's decision is made in the background during block j+1 and the new
    notch becomes active at the start of block j+2."""
    det, coef, st, pending = HowlDetector(), [], [], {}
    y = np.array(x, float)
    for j in range(len(y) // L_B):
        if j in pending:
            coef.append(pending.pop(j)); st.append([0.0, 0.0])
        for i in range(j * L_B, (j + 1) * L_B):
            v = y[i]
            for c, s in zip(coef, st):                       # cascade of active notches, DF-II-T
                out = c[0] * v + s[0]
                s[0] = c[1] * v - c[4] * out + s[1]
                s[1] = c[2] * v - c[5] * out
                v = out
            y[i] = v
        f0 = det.block(y[j * L_B:(j + 1) * L_B])
        if f0 is not None:
            pending[j + 2] = notch_coeffs(f0)
            if events is not None:
                events.append(((j + 2) * L_B, f0))
    return y


class MinTrack:
    """Minimum statistics (simplified): minimum of the smoothed power over NR_NSUB sub-windows of n_sub
    updates each, times the bias factor. Before the first sub-window completes, the running minimum is used."""

    def __init__(self, n_sub, bias, shape=()):
        self.n_sub, self.bias, self.i = n_sub, bias, 0
        self.cur = np.full(shape, np.inf)
        self.mins = [np.full(shape, np.inf) for _ in range(NR_NSUB)]

    def update(self, P):
        self.cur = np.minimum(self.cur, np.where(P > 1e-20, P, np.inf))   # exact digital silence is ignored
        self.i += 1
        if self.i == self.n_sub:
            self.mins = self.mins[1:] + [self.cur]
            self.cur, self.i = np.full(np.shape(P), np.inf), 0
        m = self.cur
        for v in self.mins:
            m = np.minimum(m, v)
        return self.bias * m


def nr_gain(P, N):
    return np.sqrt(np.maximum(1.0 - NR_BETA * N / (P + 1e-30), NR_GMIN ** 2))


def nr_track(v, fs_k, bias=1.0, keep_noise=None):
    """Noise suppression gain for one band signal v at rate fs_k (update, then apply). Returns G per sample."""
    a_p, a_g = np.exp(-1 / (NR_TAU_P * fs_k)), np.exp(-1 / (NR_TAU_G * fs_k))
    mt = MinTrack(int(round(NR_SUB * fs_k)), bias)
    n_warm = int(round(3 * NR_TAU_P * fs_k))          # skip the smoothed-power ramp-up (3 tau)
    P, Gs, seen = 0.0, 1.0, 0
    G = np.empty(len(v))
    for i, s in enumerate(v):
        if seen == 0 and s == 0.0:                     # leading zeros (alignment delay): pass through
            G[i] = Gs
            continue
        seen += 1
        P = a_p * P + (1 - a_p) * s * s
        N = float(mt.update(P)) if seen > n_warm else 0.0
        if keep_noise is not None and seen > n_warm:
            keep_noise.append((P, N / bias))
        Gs = a_g * Gs + (1 - a_g) * float(nr_gain(P, N))
        G[i] = Gs
    return G


def mode_a_nr(x, gains_db, fixed=None):
    """Mode A with per-band noise suppression. Returns (y, gain trajectories). fixed: reuse given
    trajectories (shadow filtering: apply the gains computed on the mixture to speech and noise alone)."""
    g = 10 ** (np.asarray(gains_db) / 20)
    bands, xk = [], np.asarray(x, float)
    for k in range(K):
        gx = signal.lfilter(G, 1, xk)
        bands.append(delay(xk, DG) - gx)
        xk = gx[::2]
    Gs = [None] * (K + 1)
    Gs[K] = fixed[K] if fixed else nr_track(xk, FS / 2 ** K, NR_BIAS_A[K])
    y = g[K] * Gs[K] * xk
    for k in range(K - 1, -1, -1):
        up = np.zeros(len(bands[k]))
        up[::2] = y
        bd = delay(bands[k], ALIGN[k])
        Gs[k] = fixed[k] if fixed else nr_track(bd, FS / 2 ** k, NR_BIAS_A[k])
        y = g[k] * Gs[k] * bd + 2 * signal.lfilter(F, 1, up)
    return y, Gs


NR_J = np.arange((M_B + 1) // 2)                              # the 65 frequency samples of the Mode B FIR
NR_BIN = np.round(NR_J * N_FFT / M_B).astype(int)             # nearest FFT-256 bin of each
NR_COS = np.cos(2 * np.pi * np.outer(NR_J, np.arange(M_B) - (M_B - 1) / 2) / M_B)


def mode_b_nr(x, preset, fixed=None):
    """Mode B with noise suppression: per block, estimate power at the 65 frequency samples, update the
    gains, redesign the 129-tap FIR by frequency sampling and filter the block with it. Each block is
    still an exact linear convolution (L + M - 1 = 256), so overlap-add stays artefact-free."""
    tgt = 10 ** (target_db(preset, NR_J * FS / M_B) / 20)
    dt = L_B / FS
    a_p, a_g = np.exp(-dt / NR_TAU_P), np.exp(-dt / NR_TAU_G)
    mt = MinTrack(int(round(NR_SUB / dt)), NR_BIAS_B, (len(NR_J),))
    n_warm = int(round(3 * NR_TAU_P / dt))             # same 3-tau warm-up as Mode A (11 blocks)
    P, seen = None, 0
    Gs = np.ones(len(NR_J))
    nb = len(x) // L_B
    y = np.zeros(nb * L_B + N_FFT)
    used = []
    for b in range(nb):
        X = np.fft.fft(x[b * L_B:(b + 1) * L_B], N_FFT)
        if fixed is None:
            P2 = np.abs(X[: N_FFT // 2 + 1]) ** 2
            Pj = np.array([P2[max(i - 1, 0):i + 2].mean() for i in NR_BIN])   # power around each sample
            if seen == 0 and not Pj.any():                     # leading digital silence: pass through
                Gb = Gs.copy()
            else:
                seen += 1
                P = Pj if P is None else a_p * P + (1 - a_p) * Pj  # first real block initialises P
                N = mt.update(P) if seen > n_warm else np.zeros(len(NR_J))
                Gs = a_g * Gs + (1 - a_g) * nr_gain(P, N)
                Gb = Gs.copy()
        else:
            Gb = fixed[b]
        used.append(Gb)
        Hj = tgt * Gb
        h = (Hj[0] * NR_COS[0] + 2 * (Hj[1:, None] * NR_COS[1:]).sum(0)) / M_B
        y[b * L_B:b * L_B + N_FFT] += np.fft.ifft(X * np.fft.fft(h, N_FFT)).real
    return y[: nb * L_B], used


def nr_bias(seconds=20.0, seed=123):
    """Measure the bias factors E[P] / E[min] of the noise tracker on stationary white noise (the
    estimator's own statistics; independent of the speech tests). Returns (list for Mode A, Mode B)."""
    rng = np.random.default_rng(seed)
    x = 0.01 * rng.standard_normal(int(seconds * FS))
    bands, xk = [], x
    for k in range(K):
        gx = signal.lfilter(G, 1, xk)
        bands.append(delay(xk, DG) - gx)
        xk = gx[::2]
    bands.append(xk)
    res_a = []
    for k, v in enumerate(bands):
        pn = []
        nr_track(v, FS / 2 ** k, 1.0, pn)
        pn = np.array(pn[int(len(pn) * 0.2):])                  # skip the first 20 % (start-up)
        res_a.append(float(np.mean(pn[:, 0]) / np.mean(pn[:, 1])))
    dt = L_B / FS
    a_p = np.exp(-dt / NR_TAU_P)
    mt = MinTrack(int(round(NR_SUB / dt)), 1.0, (len(NR_J),))
    P, ps, ns = None, [], []
    for b in range(len(x) // L_B):
        P2 = np.abs(np.fft.fft(x[b * L_B:(b + 1) * L_B], N_FFT)[: N_FFT // 2 + 1]) ** 2
        Pj = np.array([P2[max(i - 1, 0):i + 2].mean() for i in NR_BIN])
        P = Pj if P is None else a_p * P + (1 - a_p) * Pj
        n = mt.update(P)
        if b > (len(x) // L_B) // 5:
            ps.append(P); ns.append(n)
    return res_a, float(np.mean(np.array(ps)[:, 1:]) / np.mean(np.array(ns)[:, 1:]))


def chain(x, mode, preset, nr=False, notch=False):
    """Full board chain: HPF -> [auto feedback notch] -> Mode A or B [with noise suppression] -> limiter.
    x is float, full scale = 1.0. nr / notch default off (the verified core)."""
    v = hpf(x)
    if notch:
        v = notch_auto(v)
    if mode == "A":
        v = mode_a_nr(v, band_gains(preset))[0] if nr else mode_a(v, band_gains(preset))
    else:
        v = mode_b_nr(v, preset)[0] if nr else mode_b(v, preset)
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
