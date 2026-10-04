"""Design-check calculations for the research pack (Python stand-in for the MATLAB prototype).
Run: python3 design_check.py   -> prints every number used in 05_system_design.md
"""
import numpy as np
from scipy import signal

fs0 = 48000.0          # codec rate (DEFAULT)
K = 4                  # number of split levels -> K+1 = 5 bands (DEFAULT)

def kaiser_lp(N, fc_norm, beta):
    # fc_norm: cutoff as fraction of fs (0..0.5)
    return signal.firwin(N, fc_norm*2, window=('kaiser', beta))

def stop_att(h, f_stop, fs=1.0, n=1<<15):
    w, H = signal.freqz(h, 1, worN=n, fs=fs)
    H = np.abs(H)/np.abs(H[0])
    return -20*np.log10(np.max(H[w >= f_stop]))

def pass_ripple(h, f_pass, fs=1.0, n=1<<15):
    w, H = signal.freqz(h, 1, worN=n, fs=fs)
    H = np.abs(H)/np.abs(H[0])
    hp = H[w <= f_pass]
    return 20*np.log10(hp.max()), 20*np.log10(hp.min())

print("=== Filter choices ===")
# G: band-split lowpass, crossover (−6 dB) at fs_k/8, transition 0.05..0.20 fs_k
for N in (17, 21, 25):
    for beta in (4.5, 5.0, 5.65):
        g = kaiser_lp(N, 0.125, beta)
        print(f"G N={N} beta={beta}: stop att (f>=0.20fs) = {stop_att(g,0.20):.1f} dB, "
              f"pass (f<=0.05fs) = {pass_ripple(g,0.05)[1]:.2f} dB")
# F: halfband interpolator, pass 0..0.20 fs_k, stop >= 0.30 fs_k
for N in (23, 27, 31):
    for beta in (4.5, 5.65):
        f = kaiser_lp(N, 0.25, beta)
        print(f"F N={N} beta={beta}: stop att (f>=0.30fs) = {stop_att(f,0.30):.1f} dB, "
              f"pass (f<=0.20fs) min = {pass_ripple(f,0.20)[1]:.3f} dB, "
              f"zero taps = {np.sum(np.abs(f)<1e-12)}")

NG, BG = 21, 4.5
NF, BF = 31, 4.5
g = kaiser_lp(NG, 0.125, BG)
f = kaiser_lp(NF, 0.25, BF)
f[np.abs(f) < 1e-12] = 0.0
print(f"\nCHOSEN: G N={NG} (Kaiser beta {BG}) att={stop_att(g,0.20):.1f} dB ; "
      f"F N={NF} (halfband, Kaiser beta {BF}) att={stop_att(f,0.30):.1f} dB")
nzF = np.count_nonzero(f)
print(f"F nonzero taps = {nzF} (center tap = {f[NF//2]:.4f})")
dG, dF = (NG-1)//2, (NF-1)//2

# ---------------- simulate the multirate tree -----------------
def analyse_synth(x, gains):
    """gains: list of K+1 linear gains, index 0 = top band (highest freq)."""
    # analysis
    bands, lows = [], []
    xk = x
    for k in range(K):
        gx = signal.lfilter(g, 1, xk)
        xd = np.concatenate([np.zeros(dG), xk[:-dG]])
        bands.append(xd - gx)           # complementary high band at rate k
        xk = gx[::2]                    # decimate by 2
    resid = xk
    # synthesis
    y = gains[K]*resid
    T = [0]*(K+1)
    for k in range(K-1, -1, -1):
        up = np.zeros(2*len(y)); up[::2] = y
        yi = 2*signal.lfilter(f, 1, up)          # interpolate (gain 2)
        T[k] = dG + dF + 2*T[k+1]               # path delay at rate k
        extra = T[k] - dG                       # band already has dG delay
        b = np.concatenate([np.zeros(extra), bands[k][:len(bands[k])-extra]])
        n = min(len(b), len(yi))
        y = gains[k]*b[:n] + yi[:n]
    return y, T

N = 1 << 14
imp = np.zeros(N); imp[0] = 1
y, T = analyse_synth(imp, [1]*(K+1))
pk = int(np.argmax(np.abs(y)))
err = y.copy(); err[pk] -= 1
print(f"\nUnity gains: peak at n={pk} (theory T0={T[0]}), latency = {pk/fs0*1e3:.3f} ms")
print(f"Reconstruction error energy = {10*np.log10(np.sum(err**2)+1e-30):.1f} dB rel. impulse")
print("Path delays T_k (samples at own rate):", T)
for k in range(K):
    fk = fs0/2**k
    print(f"  level {k}: fs_k={fk:.0f} Hz, crossover fs_k/8={fk/8:.0f} Hz, "
          f"own-stage delay {(dG+dF)/fk*1e3:.3f} ms")

# composite response, unity gains (magnitude)
w, H = signal.freqz(y, 1, worN=8192, fs=fs0)
band = (w > 50) & (w < 20000)
print(f"Unity-gain composite ripple 50 Hz-20 kHz: max {20*np.log10(np.abs(H[band]).max()):.3f} dB, "
      f"min {20*np.log10(np.abs(H[band]).min()):.3f} dB")

# ---------------- gain table -----------------
from audiograms import AUDIOGRAMS, band_hl, band_gains_db, gain_curve_db, CAP_DB
AUD_DEFAULT = "N3"   # DEFAULT - confirm with team: Bisgaard Table 2 N3 (moderate)
aud = AUDIOGRAMS[AUD_DEFAULT]
cap = CAP_DB
band_names = [b for b, _, _ in band_hl(aud)]
band_gain_db = np.array(band_gains_db(aud, 0.5))
print(f"\nGain table ({AUD_DEFAULT}, half-gain rule, cap 30 dB):")
for (nme, hl, how), gd in zip(band_hl(aud), band_gain_db):
    print(f"  {nme}: HL {hl:.2f} dB ({how}) -> gain {gd:.2f} dB")
gains = list(10**(band_gain_db/20))

# tone test: measure gain at audiometric frequencies + worst alias/spur
print("\nTone test with gain table (steady-state, 1 s tones):")
t = np.arange(int(fs0))/fs0
test_f = [250, 375, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
for ft in test_f:
    x = 0.01*np.sin(2*np.pi*ft*t)
    yy, _ = analyse_synth(x, gains)
    seg = yy[8000:8000+38400]          # whole number of cycles for all test tones
    X = np.fft.rfft(seg*np.hanning(len(seg)))
    fr = np.fft.rfftfreq(len(seg), 1/fs0)
    i0 = np.argmin(np.abs(fr-ft))
    sig_p = np.sum(np.abs(X[i0-3:i0+4])**2)
    tot = np.sum(np.abs(X)**2)
    g_meas = 20*np.log10(np.sqrt(sig_p/np.sum(np.abs(np.fft.rfft(0.01*np.sin(2*np.pi*ft*t[:len(seg)])*np.hanning(len(seg))))[i0-3:i0+4]**2)))
    spur = 10*np.log10((tot-sig_p)/sig_p + 1e-30)
    print(f"  {ft:5d} Hz: gain {g_meas:5.1f} dB, residual spurs/aliases {spur:6.1f} dBc")

# ---------------- MAC counts -----------------
rates = [fs0/2**k for k in range(K)]
macG = NG                     # direct form per sample at rate k
macG_sym = (NG+1)//2          # using symmetry
macF_per_out = nzF/2          # polyphase: avg MACs per output sample at rate k
per_level = macG + macF_per_out + 1 + 2    # + gain mult + 2 adds/subs
ops = sum(per_level*r for r in rates) + fs0/2**K   # residual gain
print(f"\nMultirate ops/s = {ops/1e6:.3f} M  -> {ops/fs0:.1f} ops per input sample")
# single-rate equivalent: each split filter at 48 kHz with same transition in Hz
single = 0
for k in range(K):
    Nk = (NG-1)*2**k + 1
    single += (Nk + 1 + 1) * fs0          # filter + gain + add
single += fs0
print(f"Single-rate equivalent ops/s = {single/1e6:.3f} M -> {single/fs0:.1f} per sample; "
      f"ratio = {single/ops:.2f}x")

for fclk in (456e6, 300e6):
    for cpm in (1.0, 5.0):
        print(f"  Filter-bank-only load @ {fclk/1e6:.0f} MHz, {cpm} cycles/op: {100*ops*cpm/fclk:.2f} %")

# ---------------- latency budget -----------------
codec = (17 + 21)/fs0
print(f"\nCodec ADC+DAC group delay = 38/fs = {codec*1e3:.3f} ms")
print(f"Mode A sample-by-sample latency = {T[0]/fs0*1e3:.3f} + {codec*1e3:.3f} = {(T[0]/fs0+codec)*1e3:.3f} ms")
for Lf in (16, 32):
    print(f"Mode A with {Lf}-sample ping-pong frames = {(T[0]+2*Lf)/fs0*1e3 + codec*1e3:.3f} ms")

# ---------------- Mode B: frequency-sampling FIR + OLA -----------------
M, L, NFFT = 129, 128, 256
assert L + M - 1 <= NFFT
fk = np.arange((M+1)//2) * fs0 / M
logf = np.log2(np.maximum(fk, 1))
gcurve_db = gain_curve_db(aud, fk, 0.5)
Hk = 10**(gcurve_db/20)
# Type I linear phase frequency-sampling design (Proakis-style), M odd
n = np.arange(M)
alpha = (M-1)/2
h = np.zeros(M)
for i in range(M):
    s = Hk[0]
    for k in range(1, (M+1)//2):
        s += 2*Hk[k]*np.cos(2*np.pi*k*(i-alpha)/M)
    h[i] = s/M
w, Hb = signal.freqz(h, 1, worN=8192, fs=fs0)
tgt = 10**(gain_curve_db(aud, w, 0.5)/20)
sel = (w >= 250) & (w <= 8000)
errdb = 20*np.log10(np.abs(Hb[sel])/tgt[sel])
print(f"\nMode B FIR M={M}: grid spacing {fs0/M:.1f} Hz, max |error| 250-8000 Hz = {np.max(np.abs(errdb)):.2f} dB")
latB = (2*L + alpha)/fs0 + codec
print(f"Mode B latency = (2L + (M-1)/2)/fs + codec = ({2*L}+{alpha:.0f})/48000 + codec = {latB*1e3:.3f} ms")
# DSPLIB cycle formulas (SPRU657 / SPRA947)
import math
def c_r2(n): return 2*n*int(math.log2(n)) + 42
def c_r4(n): return (14*n//4 + 23)*int(round(math.log(n, 4))) + 20
def c_mx(n):
    s = math.ceil(math.log(n, 4) - 1)
    return 3*s*n + 21*s + 2*n + 44
def c_brev(n): return int(2.5*n + 26)
print(f"FFT N={NFFT}: cfftr2_dit {c_r2(NFFT)}, cfftr4_dif {c_r4(NFFT)}, fftSPxSP {c_mx(NFFT)}, bitrev_cplx {c_brev(NFFT)} cycles")
cmul = 4*NFFT        # ASSUMPTION: 4 cycles per complex bin multiply (plain C)
conv = 2*NFFT        # ASSUMPTION: int16<->float conversion, 2 cycles/sample
ola = 2*L
frameB = 2*c_mx(NFFT) + cmul + conv + ola
frames_s = fs0/L
print(f"Mode B FFT-path cycles/frame (excl. HPF and overhead; full estimate in cpu_check.py) ~ {frameB} ; frames/s = {frames_s:.0f}; cycles/s = {frameB*frames_s/1e6:.2f} M")
for fclk in (456e6, 300e6):
    print(f"  CPU load @ {fclk/1e6:.0f} MHz: {100*frameB*frames_s/fclk:.2f} % (x2 cache penalty: {200*frameB*frames_s/fclk:.2f} %)")
# DSPF_sp_fir_gen formula (SPRA947): (4*floor((nh-1)/2)+14)*ceil(nr/4)+8
def c_firgen(nh, nr): return (4*((nh-1)//2)+14)*math.ceil(nr/4) + 8
print(f"\nDSPF_sp_fir_gen check vs SPRA947 example (nh=240,nr=200): {c_firgen(240,200)} (doc: 24508)")
print(f"DSPF_sp_fir_gen G (nh={NG}, nr=16 frame): {c_firgen(NG,16)} cycles -> {c_firgen(NG,16)/16:.1f} cycles/output")
print("Biquad: DSPF_sp_biquad needs nx multiple of 3 (S15 p.4-46); HPF is plain C in the build - see cpu_check.py")
# Goertzel for self test
print(f"Goertzel: 1 real MAC + 2 adds per sample per bin; 11 bins x 4800 samples = {11*4800} MACs per 100 ms test block")

# ---------------- extra numbers used in the docs -----------------
print("\n=== Mode A cycle estimate: moved to cpu_check.py (Update 3) ===")
print("The earlier 16-sample-frame estimate used DSPF_sp_fir_gen with nr=2 and DSPF_sp_biquad with nx=16,")
print("both outside the S15 constraints (nr>=4; nx multiple of 3). See cpu_check_output.txt.")

print("\n=== 4th-order Butterworth HP 100 Hz (bilinear, prewarped) ===")
sos = signal.butter(4, 100, 'highpass', fs=fs0, output='sos')
np.set_printoptions(precision=8, suppress=False)
print(sos)
K1 = np.tan(np.pi*100/fs0)
print(f"1st-order example: K=tan(pi*100/48000)={K1:.6f}, pole (1-K)/(1+K)={(1-K1)/(1+K1):.6f}, gain 1/(1+K)={1/(1+K1):.6f}")
print(f"matched-z pole exp(-2*pi*100/48000) = {np.exp(-2*np.pi*100/fs0):.6f}")

print("\n=== WDRC smoothing coefficients alpha = exp(-1/(tau*fs_k)) ===")
for k, r in enumerate([48000, 24000, 12000, 6000, 3000]):
    print(f"rate {r}: attack 10 ms -> {np.exp(-1/(0.010*r)):.5f}, release 20 ms -> {np.exp(-1/(0.020*r)):.5f}")

print("\n=== Memory ===")
dl = [T[k]-dG for k in range(K)]
print("band delay-line lengths:", dl, "total", sum(dl), "floats =", 4*sum(dl), "bytes")
print("G/F state per level:", NG, NF, " -> ", 4*K*(NG+NF), "bytes")
print(f"Mode B buffers: 3 x {NFFT} complex floats = {3*NFFT*8} B, twiddles {NFFT*2*4} B, H[k] {NFFT*8} B")
print(f"10 s capture @48k float = {10*48000*4/1e6:.2f} MB")
print("\nFrequency-sampling worked example M=5, H=[1,1,0]:")
M5=5; H5=[1,1,0]
hh=[(H5[0]+2*sum(H5[k]*np.cos(2*np.pi*k*(n-2)/M5) for k in (1,2)))/M5 for n in range(M5)]
print(np.round(hh,4), "sum", round(sum(hh),4))
print("4-pt DFT of [1,2,0,0]:", np.round(np.fft.fft([1,2,0,0]),4))
print("Kaiser length A=50, df=0.15:", (50-7.95)/(14.36*0.15)+1)
