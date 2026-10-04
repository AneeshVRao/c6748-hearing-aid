"""Gain tables from Bisgaard audiograms + Yang/Liu/Jou eq.(15)/(16) cross-check.
Run: python3 gain_check.py > gain_check_output.txt
All numbers printed here are OUR CALCULATION unless the comment cites a PDF table/equation.
"""
import numpy as np
from scipy import signal
from audiograms import AUDIOGRAMS, FREQS, band_hl, band_gains_db, gain_curve_db, RULES, CAP_DB

fs0, K = 48000.0, 4
NG, BG, NF, BF = 21, 4.5, 31, 4.5
g = signal.firwin(NG, 0.25, window=('kaiser', BG))
f = signal.firwin(NF, 0.5, window=('kaiser', BF)); f[np.abs(f) < 1e-12] = 0
dG, dF = (NG-1)//2, (NF-1)//2

def analyse_synth(x, gains):
    bands, xk = [], x
    for k in range(K):
        gx = signal.lfilter(g, 1, xk)
        bands.append(np.concatenate([np.zeros(dG), xk[:-dG]]) - gx)
        xk = gx[::2]
    y, T = gains[K]*xk, [0]*(K+1)
    for k in range(K-1, -1, -1):
        up = np.zeros(2*len(y)); up[::2] = y
        yi = 2*signal.lfilter(f, 1, up)
        T[k] = dG + dF + 2*T[k+1]
        extra = T[k] - dG
        b = np.concatenate([np.zeros(extra), bands[k][:len(bands[k])-extra]])
        n = min(len(b), len(yi)); y = gains[k]*b[:n] + yi[:n]
    return y, T

def tone_gain(ft, gains):
    t = np.arange(int(fs0))/fs0
    x = 0.01*np.sin(2*np.pi*ft*t)
    y, _ = analyse_synth(x, gains)
    seg = y[8000:8000+38400]; ref = x[:38400]
    win = np.hanning(len(seg))
    Y = np.fft.rfft(seg*win); X = np.fft.rfft(ref*win)
    fr = np.fft.rfftfreq(len(seg), 1/fs0); i0 = np.argmin(np.abs(fr-ft))
    sp = np.sum(np.abs(Y[i0-3:i0+4])**2); xp = np.sum(np.abs(X[i0-3:i0+4])**2)
    spur = 10*np.log10((np.sum(np.abs(Y)**2)-sp)/sp)
    return 10*np.log10(sp/xp), spur

def modeB_error(aud, factor, M=129):
    fk = np.arange((M+1)//2)*fs0/M
    Hk = 10**(gain_curve_db(aud, fk, factor)/20)
    a = (M-1)/2; n = np.arange(M)
    h = np.array([(Hk[0] + 2*np.sum(Hk[1:]*np.cos(2*np.pi*np.arange(1, len(Hk))*(i-a)/M)))/M for i in n])
    w, H = signal.freqz(h, 1, worN=8192, fs=fs0)
    sel = (w >= 250) & (w <= 8000)
    return np.max(np.abs(20*np.log10(np.abs(H[sel])) - gain_curve_db(aud, w[sel], factor)))

test_f = list(FREQS) + [8000.0]
print("=== Band HL and gains (cap %.0f dB) ===" % CAP_DB)
for name, aud in AUDIOGRAMS.items():
    print(f"\n--- {name} ---")
    bh = band_hl(aud)
    for rule, fac in RULES.items():
        gd = band_gains_db(aud, fac)
        print(f"rule {rule}: " + ", ".join(f"{b}={x:.2f}" for (b, _, _), x in zip(bh, gd)))
    for (b, hl, how) in bh:
        print(f"  {b}: HL {hl:.2f} dB  [{how}]")
    for rule, fac in RULES.items():
        gd = band_gains_db(aud, fac)
        gains = list(10**(np.array(gd)/20))
        rows, worst_err, worst_spur = [], 0, -999
        for ft in test_f:
            gm, sp = tone_gain(ft, gains)
            tgt = float(gain_curve_db(aud, ft, fac)[0])
            rows.append(f"{int(ft)}:{gm:.1f}(tgt {tgt:.1f})")
            worst_err = max(worst_err, abs(gm-tgt)); worst_spur = max(worst_spur, sp)
        print(f"  Mode A {rule}: " + "  ".join(rows))
        print(f"  Mode A {rule}: max |measured - per-frequency target| = {worst_err:.2f} dB; worst spur {worst_spur:.1f} dBc;"
              f" max inter-band gain step = {max(abs(np.diff(gd))):.2f} dB; max-min band gain = {max(gd)-min(gd):.2f} dB")
        print(f"  Mode B {rule}: max |error| 250-8000 Hz = {modeB_error(aud, fac):.2f} dB")

# ---- Yang, Liu, Jou 2016 (PDF5) eq.(15) delay and eq.(16) cost ----
print("\n=== PDF5 eq.(15)/(16) applied to our Mode A ===")
# eq.(15): d_n = sum_i ((N_i-1)/2)*(fs/fs_i)  [samples at fs]
# eq.(16): c_n = sum_i ((N_i+1)/2)*(fs_i/fs)  [multiplies per input sample, symmetric odd-length FIR]
rates = [fs0/2**k for k in range(K)]
def d15(path):  return sum((N-1)/2*(fs0/r) for N, r in path)
def c16(path):  return sum((N+1)/2*(r/fs0) for N, r in path)
# deepest path (band B1): G at 48k,24k,12k,6k then F at 6k,12k,24k,48k
pathB1 = [(NG, r) for r in rates] + [(NF, r) for r in rates]
print(f"B1 path delay eq.(15) = {d15(pathB1):.1f} samples = {d15(pathB1)/fs0*1e3:.3f} ms")
for k in range(K):
    path = [(NG, r) for r in rates[:k+1]] + [(NF, r) for r in rates[:k]]
    print(f"  band at level {k} before alignment: {d15(path):.1f} samples")
# whole-bank cost: every G and F filter counted once (shared tree)
c_shared = sum(c16([(NG, r), (NF, r)]) for r in rates)
print(f"Whole tree eq.(16) (G and F as full symmetric FIRs at fs_k): {c_shared:.2f} MPY/sample")
# refinements: F is half-band (17 non-zero taps, 9 unique after symmetry) and polyphase
c_hb = sum(c16([(NG, r)]) + 9/2*(r/fs0) for r in rates)
print(f"With half-band zeros + polyphase for F (9 unique mults per 2 outputs): {c_hb:.2f} MPY/sample")
gainmults = sum(1/2**k for k in range(K+1))
print(f"+ band gain multiplies: {gainmults:.4f} per input sample -> {c_hb+gainmults:.2f}")
print("(design_check.py counted 61 ops/sample: G without symmetry 21, F 8.5, +3 gain/add ops per level sample)")

# ---- what it would take to reach the class-2 60 dB stopband (PDF5 Sec. II-A) ----
print("\n=== Lengths for >=60 dB stopband (Kaiser, same edges) ===")
def att(h, fstop):
    w, H = signal.freqz(h, 1, 1 << 15, fs=1.0); H = np.abs(H)/abs(H[0]); return -20*np.log10(H[w >= fstop].max())
for name, fc, fstop, Ns in (("G", 0.125, 0.20, range(21, 41, 2)), ("F", 0.25, 0.30, range(31, 64, 4))):
    found = None
    for N in Ns:
        best = max((att(signal.firwin(N, 2*fc, window=('kaiser', b)), fstop), b) for b in np.arange(3.0, 8.01, 0.25))
        if best[0] >= 60: found = (N, best); break
    print(f"{name}: shortest N with >=60 dB: {found[0]} taps (beta {found[1][1]:.2f}, {found[1][0]:.1f} dB)" if found else f"{name}: none in range")
    if name == "G": NG60 = found[0]
    else: NF60 = found[0]
T0_60 = ((NG60-1)//2 + (NF60-1)//2)*(2**K-1)
print(f"Latency with these: T0 = {T0_60} samples = {T0_60/fs0*1e3:.2f} ms (+0.79 ms codec = {T0_60/fs0*1e3+0.79:.2f} ms)")
