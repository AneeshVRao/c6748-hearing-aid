"""Independent re-check of the key numbers quoted in the pack (Update 3 review).
Computes each value from first principles (no filter simulation) and compares with the value written
in the .md files. Run: python3 review_check.py > review_check_output.txt
"""
import math
from audiograms import AUDIOGRAMS, band_hl, band_gains_db

FS = 48000
checks = []
def chk(name, computed, quoted, tol, where):
    ok = abs(computed - quoted) <= tol
    checks.append(ok)
    print(f"[{'OK ' if ok else 'BAD'}] {name}: computed {computed:.4g}, quoted {quoted} ({where})")

# Mode A delay: T_k = (NG-1)/2 + (NF-1)/2 + 2 T_{k+1}, T_4 = 0
NG, NF, K = 21, 31, 4
T = 0
for _ in range(K): T = (NG-1)//2 + (NF-1)//2 + 2*T
chk("Mode A filter-bank delay (samples)", T, 375, 0, "05 §7")
chk("Mode A filter-bank delay (ms)", T/FS*1e3, 7.81, 0.005, "05 §7")
# eq.(15) of S3
d15 = sum((NG-1)/2*2**k for k in range(K)) + sum((NF-1)/2*2**k for k in range(K))
chk("S3 eq.(15) B1 path", d15, 375, 0, "05 §9, literature_extracts A3")
codec = (17+21)/FS*1e3          # S13 p.8-9 / p.25 / p.29
chk("Codec delay (ms)", codec, 0.79, 0.005, "05 §7")
chk("Mode A total, per-sample (ms)", T/FS*1e3 + codec, 8.60, 0.01, "05 §7, 00, 01")
chk("Mode A total, 16-sample frames (ms)", (T+32)/FS*1e3 + codec, 9.27, 0.01, "05 §7")
chk("Mode A total, 32-sample frames (ms)", (T+64)/FS*1e3 + codec, 9.94, 0.01, "05 §7")
# alignment delays: band at level k already delayed by d15 of its own path; pad to T0
pads = []
for k in range(K):
    own = sum((NG-1)/2*2**j for j in range(k+1)) + sum((NF-1)/2*2**j for j in range(k))
    pads.append((T - own)/2**k)
print("    alignment pads (samples at own rate):", pads, "-> quoted 365/165/65/15 (05 §2, 06 §3.4)")
checks.append(pads == [365, 165, 65, 15])
# Mode B sizes and latency
M, L, N = 129, 128, 256
chk("OLA condition L+M-1 <= N", L+M-1, 256, 0, "05 §5/§7, 04 §2")
chk("Mode B latency (ms)", (2*L + (M-1)/2)/FS*1e3 + codec, 7.46, 0.01, "05 §7")
# Update 4: McASP AFIFO + EDMA blocks of 4 (latency_check.py model; buffering = ASSUMPTION)
rf = 4 + 4 + 2          # RNUMEVT + EDMA block + XBUF/shift
wf = 64                 # Write FIFO keeps itself full (S14 p. 52)
chk("Mode A, Read FIFO only = DEFAULT (ms)", (T+rf)/FS*1e3 + codec, 8.81, 0.01, "05 §7, REVIEW §c, 00, 01")
chk("Mode A, Read+Write FIFO (rejected) (ms)", (T+rf+wf)/FS*1e3 + codec, 10.15, 0.01, "05 §7, REVIEW §c, 00, 01")
chk("Mode B, Read FIFO only = DEFAULT (ms)", (2*L+(M-1)/2+rf)/FS*1e3 + codec, 7.67, 0.01, "05 §7, REVIEW §c, 00, 01")
chk("Mode B, Read+Write FIFO (rejected) (ms)", (2*L+(M-1)/2+rf+wf)/FS*1e3 + codec, 9.00, 0.01, "05 §7, REVIEW §c, 00, 01")
chk("Frequency-sampling grid (Hz)", FS/M, 372.1, 0.05, "05 §5")
chk("Mode B frame period (ms)", L/FS*1e3, 2.67, 0.005, "06, 08 R9")
# ops per sample
ops = (21 + 17/2 + 3)*(48000+24000+12000+6000)/FS + 3000/FS
chk("Mode A ops per input sample", ops, 61.0, 0.05, "05 §9")
single = sum(((NG-1)*2**k + 1 + 2) for k in range(K)) + 1
chk("Single-rate ops per sample", single, 313, 0, "05 §9")
chk("Multirate saving", single/ops, 5.1, 0.05, "05 §9")
# crossovers
for k, q in enumerate([6000, 3000, 1500, 750]):
    chk(f"Crossover level {k} (Hz)", FS/2**k/8, q, 0, "05 §4")
# Kaiser length of G
chk("Kaiser length G", (50-7.95)/(14.36*0.15)+1, 20.5, 0.05, "05 §5, 04 §9")
# gains
quoted = {"N3": [30.00, 30.00, 25.36, 20.36, 17.50], "N2": [25.00, 22.86, 17.86, 12.86, 10.00],
          "S2": [30.00, 30.00, 28.95, 13.23, 10.00]}
for a, q in quoted.items():
    g = band_gains_db(AUDIOGRAMS[a], 0.5)
    for (b, _, _), gv, qv in zip(band_hl(AUDIOGRAMS[a]), g, q):
        chk(f"{a} half-gain {b} (dB)", gv, qv, 0.006, "research/audiogram.md, 05 §6")
# cap check: every gain <= 30
allg = [x for a in AUDIOGRAMS for f in (0.5, 0.4) for x in band_gains_db(AUDIOGRAMS[a], f)]
print(f"[{'OK ' if max(allg) <= 30 else 'BAD'}] 30 dB cap respected: max gain {max(allg):.2f} dB")
checks.append(max(allg) <= 30)
# WDRC alpha example
chk("alpha_attack example", 1-(3/(35-35/3))**(1/60), 0.0336, 0.00005, "05 §6, 04 §17")
chk("alpha_release example", 1-(4/(35-35/3))**(1/120), 0.0146, 0.00005, "05 §6, 04 §17")
# Update 5 checks
chk("Write FIFO 64 words, 1 word per sample period (ms)", 64/FS*1e3, 1.33, 0.005, "hardware_notes §1.4, 05 §7")
chk("Same 64 words if L and R were separate words (ms)", 32/FS*1e3, 0.67, 0.005, "hardware_notes §1.4 (user's figure)")
chk("Codec fs from AIC3106.h REG_PLL_A_48KHZ (Q=4) (Hz)", 24.576e6/(128*4), 48000, 0, "hardware_notes §1.3, §9")
chk("GEL Set_Core_300MHz: 24 MHz*(24+1)/(1+1) (MHz)", 24*(24+1)/(1+1), 300, 0, "hardware_notes §1.7")
chk("GEL Set_Core_456MHz: 24 MHz*(18+1)/(0+1) (MHz)", 24*(18+1)/(0+1), 456, 0, "hardware_notes §1.7")
from scipy.signal import butter as _b
_sos=_b(4,100,'highpass',fs=FS,output='sos')
_ok=all(abs(r[4])<1 and abs((r[5]-r[4]**2)/r[4])<1 for r in _sos)
print(f"    DSPF_sp_biquad pole rule (S15 p.4-46) for our HPF: {'OK' if _ok else 'FAILS'} -> quoted FAILS (hardware_notes §3.2)")
checks.append(not _ok)
# Update 6 checks (TRM S10 + C674x DSPLIB)
chk("CPU clock from TRM formula, GEL 300 MHz call: 24*(PLLM+1)/((PREDIV+1)(POSTDIV+1)(PLLDIV1+1)) (MHz)", 24*(24+1)/((0+1)*(1+1)*(0+1)), 300, 0, "hardware_notes §1.7 (TRM §7.3.9, p.145)")
chk("RFIFOCTL value RENA|RNUMEVT 4|RNUMDMA 1", (1<<16)|(4<<8)|1, 0x00010401, 0, "hardware_notes §1.4 (TRM Table 23-49, p.1160)")
chk("PINMUX13 LED field value (bits 15-8 = 8h,8h)", (0x8<<12)|(0x8<<8), 0x8800, 0, "hardware_notes §1.5 (TRM p.247)")
chk("PINMUX5 LED field value (bits 15-12 = 8h)", 0x8<<12, 0x8000, 0, "hardware_notes §1.5 (TRM p.230)")
chk("Mode B frame cycles with C674x FFTs", 1965+1985+4*256+2*128*2+2*128+128*18*2+500, 10850, 0, "cpu_check Update 6, hardware_notes §4")
chk("T11 fir_gen C674x nh24 nr48", 10/16*48*24+55, 775, 0, "07 T11")
# memory with power-of-2 circular buffers (S9 §3.9.2)
circ = sum(1 << (n-1).bit_length() for n in (365, 165, 65, 15)) + 4*2*32
chk("Mode A circular buffers incl. G/F lines (floats)", circ, 1168, 0, "hardware_notes §6, 06 §3.4")
print(f"\n{sum(checks)}/{len(checks)} checks passed")
