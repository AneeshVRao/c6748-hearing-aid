"""Phase 2, part 1: filter structures and coefficient quantisation.

FIR (G, and the Mode B FIR): direct form, cascade of second-order sections, lattice (on the
minimum-phase version of the Mode B FIR), frequency-sampling structure (comb + resonators).
A lattice needs every zero strictly inside the unit circle: a linear-phase FIR fails (|K_M| = 1),
and so does G even after minimum-phase conversion, because its 16 stopband zeros lie ON the circle
(correction C12).
IIR (the 100 Hz HPF): direct form I, direct form II, DF-II transposed, cascade, parallel,
lattice-ladder.

1. Every structure is implemented sample by sample and must equal scipy lfilter (float64).
2. Coefficients are then stored as 16-bit words ("Q15" family: the smallest integer part that
   fits the largest coefficient, rest fraction) and as float32; we compare responses, pole
   movement and stopband loss. Data-path rounding is in p2_fixed_point.py.
"""
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dsp_ref import FS, G, HPF_SOS, M_B, mode_b_fir, savefig

rng = np.random.default_rng(3)
x = rng.standard_normal(4000)


# ----------------------------------------------------------------- 16-bit coefficient words
def q16(c):
    """Round to a 16-bit signed word with the fewest integer bits that hold max|c| (Q15 if |c| < 1).
    Returns the quantised values and the format name."""
    c = np.asarray(c, float)
    ib = max(0, int(np.ceil(np.log2(np.max(np.abs(c)) + 1e-12 + 2 ** -15))))  # integer bits (excl. sign)
    fb = 15 - ib
    return np.clip(np.round(c * 2 ** fb), -2 ** 15, 2 ** 15 - 1) / 2 ** fb, f"Q{ib}.{fb}"


def q32f(c):
    return np.asarray(c, np.float32).astype(float)


# ----------------------------------------------------------------- FIR structures
def fir_direct(h, x):
    """y[n] = sum h[k] x[n-k], the tapped delay line."""
    buf = np.zeros(len(h))
    y = np.empty(len(x))
    for n, v in enumerate(x):
        buf = np.roll(buf, 1); buf[0] = v
        y[n] = h @ buf
    return y


def sos_filter(sos, x):
    """Cascade of DF-II-T second-order sections (FIR sections have a1 = a2 = 0)."""
    for b0, b1, b2, _, a1, a2 in sos:
        s1 = s2 = 0.0
        y = np.empty(len(x))
        for n, v in enumerate(x):
            out = b0 * v + s1
            s1 = b1 * v - a1 * out + s2
            s2 = b2 * v - a2 * out
            y[n] = out
        x = y
    return x


def fir_to_lattice(h):
    """Reflection coefficients K_1..K_M of A(z) = h(z)/h[0] (step-down recursion). Fails if |K| = 1."""
    a = np.asarray(h, float) / h[0]
    ks = []
    for m in range(len(a) - 1, 0, -1):
        k = a[m]
        if abs(1 - k * k) < 1e-9:
            raise ValueError(f"|K_{m}| = 1: a zero on or mirrored about the unit circle")
        ks.append(k)
        a = (a[:m] - k * a[m:0:-1]) / (1 - k * k)
    return h[0], np.array(ks[::-1])


def fir_lattice(h0, ks, x):
    """All-zero lattice: f_m = f_{m-1} + K_m g_{m-1}(n-1), g_m = K_m f_{m-1} + g_{m-1}(n-1)."""
    gd = np.zeros(len(ks))            # g_{m-1}(n-1) for m = 1..M
    y = np.empty(len(x))
    for n, v in enumerate(x):
        f = g = v
        for m, k in enumerate(ks):
            f, g, gd[m] = f + k * gd[m], k * f + gd[m], g
        y[n] = h0 * f
    return y


def min_phase(h):
    """Reflect zeros outside the unit circle to 1/conj(z): same magnitude response, minimum phase."""
    z = np.roots(h)
    z = np.where(np.abs(z) > 1, 1 / np.conj(z), z)
    hm = np.real(np.poly(z))
    w = np.linspace(0, np.pi, 512)
    return hm * np.max(np.abs(np.fft.rfft(h, 1022))) / np.max(np.abs(np.fft.rfft(hm, 1022)))


def min_phase_cepstrum(h, nfft=1 << 14):
    """Minimum-phase FIR with the same magnitude, by the real cepstrum (needs no zeros on the circle).
    Root finding is not accurate enough for a degree-128 polynomial."""
    c = np.fft.ifft(np.log(np.abs(np.fft.fft(h, nfft)))).real
    fold = np.zeros(nfft)
    fold[0], fold[nfft // 2] = c[0], c[nfft // 2]
    fold[1:nfft // 2] = 2 * c[1:nfft // 2]
    return np.fft.ifft(np.exp(np.fft.fft(fold))).real[: len(h)]


def fir_freq_sampling_structure(h, x):
    """H(z) = (1 - z^-M)/M * sum_k H[k] / (1 - e^(j2pi k/M) z^-1): comb followed by M resonators."""
    M = len(h)
    Hk = np.fft.fft(h)
    c = x - np.concatenate([np.zeros(M), x[:-M]])           # comb 1 - z^-M
    y = np.zeros(len(x), complex)
    for k in range(M):
        y += Hk[k] * signal.lfilter([1], [1, -np.exp(2j * np.pi * k / M)], c)
    return np.real(y) / M


# ----------------------------------------------------------------- IIR structures (HPF)
b_hp, a_hp = signal.sos2tf(HPF_SOS)          # one 4th-order transfer function


def df1(b, a, x):
    xs, ys = np.zeros(len(b)), np.zeros(len(a) - 1)
    y = np.empty(len(x))
    for n, v in enumerate(x):
        xs = np.roll(xs, 1); xs[0] = v
        out = b @ xs - a[1:] @ ys
        ys = np.roll(ys, 1); ys[0] = out
        y[n] = out
    return y


def df2(b, a, x):
    w = np.zeros(len(a))                      # one shared delay line (canonic)
    y = np.empty(len(x))
    for n, v in enumerate(x):
        w = np.roll(w, 1)
        w[0] = v - a[1:] @ w[1:]
        y[n] = b @ w
    return y


def df2t(b, a, x):
    s = np.zeros(len(a) - 1)
    y = np.empty(len(x))
    for n, v in enumerate(x):
        out = b[0] * v + s[0]
        s[:-1] = b[1:-1] * v - a[1:-1] * out + s[1:]
        s[-1] = b[-1] * v - a[-1] * out
        y[n] = out
    return y


def to_parallel(b, a):
    """Partial fractions (residuez), conjugate pole pairs combined into real second-order sections."""
    r, p, k = signal.residuez(b, a)
    secs, used = [], np.zeros(len(p), bool)
    for i in range(len(p)):
        if used[i]:
            continue
        j = next(j for j in range(i + 1, len(p)) if not used[j] and abs(p[j] - np.conj(p[i])) < 1e-6)
        used[[i, j]] = True
        # r/(1-pz^-1) + r*/(1-p*z^-1) = (2Re r - 2Re(r p*) z^-1) / (1 - 2Re p z^-1 + |p|^2 z^-2)
        secs.append(([2 * r[i].real, -2 * (r[i] * np.conj(p[i])).real],
                     [1, -2 * p[i].real, abs(p[i]) ** 2]))
    return np.real(k), secs


def parallel_filter(k, secs, x):
    y = np.zeros(len(x))
    for i, kk in enumerate(np.atleast_1d(k)):
        y[i:] += kk * x[: len(x) - i]
    for bs, as_ in secs:
        y += signal.lfilter(bs, as_, x)
    return y


def to_lattice_ladder(b, a):
    """Gray-Markel: reflection coefficients K_m (step-down of A) and ladder taps v_m."""
    N = len(a) - 1
    A = [None] * (N + 1)
    A[N] = np.asarray(a, float) / a[0]
    ks = np.zeros(N + 1)
    for m in range(N, 0, -1):
        ks[m] = A[m][m]
        A[m - 1] = (A[m][:m] - ks[m] * A[m][m:0:-1]) / (1 - ks[m] ** 2)
    c = np.asarray(b, float) / a[0]
    v = np.zeros(N + 1)
    for m in range(N, -1, -1):
        v[m] = c[m]
        c = c[:m] - v[m] * A[m][m:0:-1] if m else c   # C_{m-1} = C_m - v_m z^-m A_m(1/z)
    return ks[1:], v


def lattice_ladder(ks, v, x):
    N = len(ks)
    gd = np.zeros(N + 1)                      # g_m(n-1), m = 0..N
    y = np.empty(len(x))
    for n, xin in enumerate(x):
        f = xin
        g = np.zeros(N + 1)
        for m in range(N, 0, -1):             # f_{m-1} = f_m - K_m g_{m-1}(n-1)
            f = f - ks[m - 1] * gd[m - 1]
            g[m] = ks[m - 1] * f + gd[m - 1]
        g[0] = f
        gd = g
        y[n] = v @ g
    return y


# ================================================================= 1. structures == lfilter
print("1. Every structure vs scipy lfilter (float64, 4000 random samples):")
hB = mode_b_fir("N3")
hm = min_phase_cepstrum(hB)                 # Mode B FIR has no unit-circle zeros (min distance 0.058)
h0, kG = fir_to_lattice(hm)
k_hp, secs_hp = to_parallel(b_hp, a_hp)
kl, vl = to_lattice_ladder(b_hp, a_hp)
sos_G = signal.tf2sos(G, [1.0])
checks = {
    "FIR direct (G)": (fir_direct(G, x), signal.lfilter(G, 1, x)),
    "FIR cascade, 10 SOS (G)": (sos_filter(sos_G, x), signal.lfilter(G, 1, x)),
    "FIR lattice (min-phase Mode B FIR)": (fir_lattice(h0, kG, x), signal.lfilter(hm, 1, x)),
    "FIR freq.-sampling structure (Mode B)": (fir_freq_sampling_structure(hB, x), signal.lfilter(hB, 1, x)),
    "IIR direct form I (4th order)": (df1(b_hp, a_hp, x), signal.lfilter(b_hp, a_hp, x)),
    "IIR direct form II": (df2(b_hp, a_hp, x), signal.lfilter(b_hp, a_hp, x)),
    "IIR DF-II transposed": (df2t(b_hp, a_hp, x), signal.lfilter(b_hp, a_hp, x)),
    "IIR cascade, 2 biquads (board)": (sos_filter(HPF_SOS, x), signal.lfilter(b_hp, a_hp, x)),
    "IIR parallel (residuez)": (parallel_filter(k_hp, secs_hp, x), signal.lfilter(b_hp, a_hp, x)),
    "IIR lattice-ladder": (lattice_ladder(kl, vl, x), signal.lfilter(b_hp, a_hp, x)),
}
floor = np.max(np.abs(signal.lfilter(b_hp, a_hp, x) - signal.sosfilt(HPF_SOS, x)))
print(f"   (floor: lfilter on the 4th-order polynomial vs sosfilt differ by {floor:.1e}; poles at r = 0.995 make"
      f" the single polynomial ill-conditioned)")
for name, (y, ref) in checks.items():
    e = np.max(np.abs(y - ref))
    print(f"   {name:40s} max error {e:.1e}")
    assert e < (1e-10 if name.startswith("FIR") else 10 * floor), name
for name, h in (("linear-phase G", G), ("minimum-phase G", min_phase(G)), ("linear-phase Mode B FIR", hB)):
    try:
        fir_to_lattice(h)
        raise SystemExit(f"{name} should have no lattice")
    except ValueError as err:
        print(f"   {name}: {err.args[0].split(':')[0]}: no lattice")
print(f"   HPF lattice reflection coefficients K = {np.round(kl, 6)} (all |K| < 1 -> stable)")
assert np.all(np.abs(kl) < 1)
assert np.allclose(np.abs(np.fft.rfft(hm, 4096)), np.abs(np.fft.rfft(hB, 4096)), atol=1e-6)
print(f"   min-phase Mode B FIR lattice: {len(kG)} reflection coefficients, max |K| = {np.max(np.abs(kG)):.4f}")

# ================================================================= 2. coefficient quantisation
w = np.logspace(np.log10(20), np.log10(23999), 3000)
_, Href = signal.freqz(b_hp, a_hp, w, fs=FS)


def stats(H, poles):
    """max pole radius, passband error >= 200 Hz (dB), gain at 20 Hz (dB), -3 dB frequency (Hz)."""
    m = 20 * np.log10(np.abs(H) + 1e-300)
    ref = 20 * np.log10(np.abs(Href))
    pb = w >= 200
    f3 = w[np.argmax(m > -3.0103)]
    return np.max(np.abs(poles)), np.max(np.abs(m[pb] - ref[pb])), m[0], f3


print("\n2a. HPF coefficients as 16-bit words (each structure gets the smallest integer part that fits):")
rows = [("exact (float64)", "-", stats(Href, np.roots(a_hp)))]
bq, fb = q16(b_hp); aq, fa = q16(a_hp)                       # direct form: one 4th-order polynomial
pd = np.roots(aq)
rows.append(("direct form, 4th order", f"{fb}/{fa}", stats(signal.freqz(bq, aq, w, fs=FS)[1], pd)))
sq = HPF_SOS.copy()                                           # cascade (board structure)
sq[:, :3] = q16(HPF_SOS[:, :3])[0]
sq[:, 3:], fsec = q16(HPF_SOS[:, 3:])
pc = np.concatenate([np.roots(sec[3:]) for sec in sq])
rows.append(("cascade, 2 biquads (board)", fsec, stats(signal.sosfreqz(sq, w, fs=FS)[1], pc)))
H = np.zeros(len(w), complex) + np.sum(k_hp)                  # parallel
pp = []
for bs, as_ in secs_hp:
    bsq, _ = q16(bs); asq, fpar = q16(as_)
    H += signal.freqz(bsq, asq, w, fs=FS)[1]
    pp += list(np.roots(asq))
rows.append(("parallel, 2 sections", fpar, stats(H, np.array(pp))))
klq, fk = q16(kl); vlq, fv = q16(vl)                          # lattice-ladder: |K| < 1 -> Q0.15
A = np.array([1.0])
for k in klq:                                                 # step-up: poles of the quantised lattice
    A = np.concatenate([A, [0]]) + k * np.concatenate([[0], A[::-1]])
imp = np.zeros(1 << 15); imp[0] = 1
hll = lattice_ladder(klq, vlq, imp)
pl = np.roots(A)
rows.append(("lattice-ladder", f"K {fk}, v {fv}", stats(signal.freqz(hll, 1, w, fs=FS)[1], pl)))
print("   structure                    format             max pole radius  passband err (>=200 Hz)  gain @20 Hz  -3 dB freq")
for name, fmt, (r, e, g20, f3) in rows:
    print(f"   {name:28s} {fmt:18s} {r:10.6f}      {e:10.4f} dB         {g20:7.1f} dB   {f3:6.1f} Hz")
assert rows[1][2][0] >= 1 - 1e-6                                # direct form: a pole reaches the unit circle
r_c = rows[2][2]
assert r_c[0] < 1 and r_c[1] < 0.25 and abs(r_c[3] - 100) < 1 and r_c[2] < -50   # cascade keeps the response
assert rows[4][2][0] < 1                                        # lattice stays stable
sq32 = q32f(HPF_SOS)
print(f"   float32 cascade: passband error {stats(signal.sosfreqz(sq32, w, fs=FS)[1], np.roots(a_hp))[1]:.1e} dB")

fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
axs[0].semilogx(w, 20 * np.log10(np.abs(Href)), "k", lw=2, label="exact")
axs[0].semilogx(w, 20 * np.log10(np.abs(signal.freqz(bq, aq, w, fs=FS)[1]) + 1e-12), label=f"direct form, 16-bit ({fb}/{fa})")
axs[0].semilogx(w, 20 * np.log10(np.abs(signal.sosfreqz(sq, w, fs=FS)[1])), "--", label=f"cascade, 16-bit ({fsec})")
axs[0].semilogx(w, 20 * np.log10(np.abs(signal.freqz(hll, 1, w, fs=FS)[1])), ":", label="lattice-ladder, 16-bit")
axs[0].set(xlabel="Hz", ylabel="dB", ylim=(-80, 40), title="HPF with 16-bit coefficients")
axs[0].grid(alpha=0.3, which="both"); axs[0].legend(fontsize=8)
t = np.linspace(0, 2 * np.pi, 400)
axs[1].plot(np.cos(t), np.sin(t), "k", lw=0.5)
axs[1].plot(np.roots(a_hp).real, np.roots(a_hp).imag, "kx", ms=10, label="exact poles")
axs[1].plot(pd.real, pd.imag, "o", mfc="none", label="direct form, 16-bit")
axs[1].plot(pc.real, pc.imag, "s", mfc="none", label="cascade, 16-bit")
axs[1].set(xlim=(0.97, 1.01), ylim=(-0.02, 0.02), aspect="equal", title="pole positions near z = 1 (zoom)")
axs[1].grid(alpha=0.3); axs[1].legend(fontsize=8)
savefig(fig, "p2_iir_quantisation.png", "phase2")

print("\n2b. FIR G with 16-bit coefficients (stopband for f >= 0.20 fs, passband error for f <= 0.05 fs):")


def fir_stats(hq_resp):
    wf, H = hq_resp
    H = np.abs(H)
    return -20 * np.log10(H[wf >= 0.20].max() / H[0]), np.max(np.abs(20 * np.log10(H[wf <= 0.05] / H[0])))


wf = np.linspace(0, 0.5, 4096)
Gq, fG = q16(G)
sosq = sos_G.copy()
sosq[:, :3], fS = q16(sos_G[:, :3])
fir_rows = [("direct form (exact)", "-", fir_stats(signal.freqz(G, 1, wf, fs=1))),
            ("direct form", fG, fir_stats(signal.freqz(Gq, 1, wf, fs=1))),
            ("cascade, 10 SOS", fS, fir_stats(signal.freqz(*signal.sos2tf(sosq), wf, fs=1))),
            ("direct form, float32", "float32", fir_stats(signal.freqz(q32f(G), 1, wf, fs=1)))]
for name, fmt, (att, pe) in fir_rows:
    print(f"   {name:24s} {fmt:8s} stopband {att:6.2f} dB, passband error {pe:.4f} dB")
assert fir_rows[1][2][0] > 50                          # Q15 direct form keeps > 50 dB

print("\n2c. Mode B FIR (min-phase version for the lattice), 16-bit coefficients, error vs exact 250 Hz-8 kHz:")
wb = np.linspace(250, 8000, 2000)
Hm_exact = np.abs(signal.freqz(hm, 1, wb, fs=FS)[1])
kq, fK = q16(kG)
h0q, f0 = q16([h0])
imp = np.zeros(M_B); imp[0] = 1
hlat = fir_lattice(h0q[0], kq, imp)
hdq, fD = q16(hm)
for name, fmt, h in (("direct form", fD, hdq), ("lattice", f"K {fK}", hlat)):
    e = np.max(np.abs(20 * np.log10(np.abs(signal.freqz(h, 1, wb, fs=FS)[1]) / Hm_exact)))
    print(f"   {name:12s} {fmt:10s} max error {e:.4f} dB")
print("p2_structures OK")
