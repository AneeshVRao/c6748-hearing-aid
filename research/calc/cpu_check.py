"""CPU-load and DSPLIB-constraint check (Update 3).

Every TI number below is cited in the comment next to it; everything else is OUR CALCULATION or a
labelled ASSUMPTION. Run: python3 cpu_check.py > cpu_check_output.txt
"""
import math

FS = 48000
F_CLK = {"456 MHz (S8 p.1 max; S11 §1.1)": 456e6,
         "300 MHz (S11 §3.5 AISgen NAND-boot setting)": 300e6}

# ---------------- TI cycle formulas ----------------
def fir_gen(nh, nr):            # S15 p.4-41: (4*floor((nh-1)/2)+14)*ceil(nr/4)+8 ; needs nh>=4, nr>=4
    assert nh >= 4 and nr >= 4, "DSPF_sp_fir_gen requires nh>=4 and nr>=4 (S15 p.4-41)"
    return (4*((nh-1)//2) + 14)*math.ceil(nr/4) + 8
def fircirc(nh, nr):            # S15 p.4-45: (2*nh+10)*nr/4+18 ; nh even >=4, nr multiple of 4
    assert nh % 2 == 0 and nh >= 4 and nr % 4 == 0, "DSPF_sp_fircirc constraints (S15 p.4-44)"
    return (2*nh + 10)*nr/4 + 18
def biquad(nx):                 # S15 p.4-47: 4*nx+76 ; nx multiple of 3 (S15 p.4-46)
    assert nx % 3 == 0, "DSPF_sp_biquad requires nx multiple of 3 (S15 p.4-46)"
    return 4*nx + 76
def fftSPxSP(N):                # S15 p.4-25 (same formula for ifftSPxSP, p.4-33)
    s = math.ceil(math.log(N, 4) - 1)
    return 3*s*N + 21*s + 2*N + 44
def cfftr2_dit(n):  return 2*n*int(math.log2(n)) + 42          # S15 p.4-16, 32<=n<=32K
def icfftr2_dif(n): return 2*n*int(math.log2(n)) + 37          # S15 p.4-38
def cfftr4_dif(n):  return (14*n//4 + 23)*round(math.log(n, 4)) + 20   # S15 p.4-12
def bitrev_cplx(n): return int(2.5*n + 26)                       # S15 p.4-8
def dotprod(nx):    return nx/2 + 25                             # S15 p.4-54

print("=== Constraint checks against the earlier pack ===")
for label, fn in [("fir_gen nh=21, nr=2 (old 16-sample frame, level 3)", lambda: fir_gen(21, 2)),
                  ("biquad nx=16 (old 16-sample frame)", lambda: biquad(16)),
                  ("biquad nx=1 (per-sample)", lambda: biquad(1)),
                  ("fir_gen nh=21, nr=4 (32-sample frame, level 3)", lambda: fir_gen(21, 4))]:
    try:
        print(f"  {label}: OK, {fn()} cycles")
    except AssertionError as e:
        print(f"  {label}: VIOLATES -> {e}")

# ---------------- operation counts (our calculation, from 05 §9) ----------------
OPS_BANK = 61.0            # design_check.py: ops per input sample for the Mode A tree (G 21 + F 8.5 + 3, x 90k/48k + residual)
OPS_HPF  = 2*9             # 2 biquads x (5 multiplies + 4 adds) per sample  (our count)
OPS_LIM  = 4               # limiter + int16<->float conversion per sample (ASSUMPTION)

print("\n=== Mode A, DEFAULT: per-sample interrupt, plain C (DSPLIB not usable at nr=1, nx=1) ===")
ops = OPS_BANK + OPS_HPF + OPS_LIM
for cpo in (1.0, 3.0, 5.0):                     # ASSUMPTION: cycles per op for compiled C (-o3 best ... -o0-like worst)
    for isr in (200, 600):                      # ASSUMPTION: 2 slot interrupts per stereo I2S frame (L+R) x 100..300 cycles each
        cyc = ops*cpo + isr
        line = f"  {cpo} cyc/op, ISR {isr}: {cyc:.0f} cycles/sample"
        for name, f in F_CLK.items():
            line += f" | {100*cyc*FS/f:.2f} % @ {name.split()[0]}MHz"
        print(line)
print(f"  ops per sample = {OPS_BANK} (bank) + {OPS_HPF} (HPF) + {OPS_LIM} (limiter/convert) = {ops}")
print(f"  per-sample budget = {456e6/FS:.0f} cycles @456 MHz, {300e6/FS:.0f} @300 MHz")

print("\n=== Mode A, OPTION: 32-sample EDMA frames (every level gets >=4 samples) ===")
nr_lv = [32, 16, 8, 4]
cG = sum(fir_gen(21, n) for n in nr_lv)
outs = sum(nr_lv)
cF = outs*8.5*2              # ASSUMPTION: polyphase half-band F in plain C, 2 cycles/MAC
cGain = outs*3*2             # ASSUMPTION
cHPF = 32*OPS_HPF*2          # own-C biquads (32 not a multiple of 3), ASSUMPTION 2 cycles/op
cOver = 500                  # ASSUMPTION: calls, conversion, limiter, EDMA ISR
tot = cG + cF + cGain + cHPF + cOver
print(f"  G fir_gen (nr 32/16/8/4) {cG}, F {cF:.0f}, gains {cGain}, HPF {cHPF}, overhead {cOver} -> {tot:.0f} cycles / 32 samples")
for name, f in F_CLK.items():
    print(f"  load @ {name}: {100*tot*FS/32/f:.2f} %")
print(f"  latency = (375 + 2*32)/48000 + 38/48000 = {(375+64+38)/FS*1e3:.2f} ms")

print("\n=== Mode B: 128-sample frame, FFT-256 OLA ===")
N, L = 256, 128
cf = fftSPxSP(N); ci = fftSPxSP(N)            # ifftSPxSP same formula (S15 p.4-33)
cmul = 4*N                                     # ASSUMPTION
conv = 2*L*2                                   # ASSUMPTION int16<->float in and out
ola = 2*L                                      # ASSUMPTION
hpf = L*OPS_HPF*2                              # ASSUMPTION own-C HPF
frameB = cf + ci + cmul + conv + ola + hpf + 500
print(f"  fftSPxSP {cf} + ifftSPxSP {ci} + cmul {cmul} + conv {conv} + OLA {ola} + HPF {hpf} + overhead 500 = {frameB} cycles/frame")
for name, f in F_CLK.items():
    print(f"  load @ {name}: {100*frameB*FS/L/f:.2f} %  (x2 cache margin, cf. S16 Table 7: {200*frameB*FS/L/f:.2f} %)")

print("\n=== FFT benchmark predictions at N=256 (S15 formulas) ===")
print(f"  cfftr2_dit {cfftr2_dit(256)}, bitrev_cplx {bitrev_cplx(256)}, icfftr2_dif {icfftr2_dif(256)}, "
      f"cfftr4_dif {cfftr4_dif(256)}, fftSPxSP {fftSPxSP(256)}")
print(f"  radix-2 forward+inverse without bit reversal (DIT out bit-reversed -> DIF in bit-reversed, S15 p.4-34): "
      f"{cfftr2_dit(256)+icfftr2_dif(256)} cycles")
print(f"  dotprod nx=21 (alternative G kernel): {dotprod(21):.1f} cycles")

print("\n=== Circular-buffer sizes (power of 2, S9 §3.9.2; S15 p.4-44) ===")
for name, n in [("G delay line", 21), ("F delay line", 31), ("align L0", 365), ("align L1", 165), ("align L2", 65), ("align L3", 15)]:
    p = 1 << (n-1).bit_length()
    print(f"  {name}: {n} floats -> {p} floats = {4*p} bytes")

print("\n=== Mode B inside the DEFAULT per-sample-interrupt framework (software ping-pong) ===")
# ISR only copies samples into a 128-sample ping-pong buffer; FFT work runs in the background loop.
for isr in (200, 600):                                   # same ISR ASSUMPTION as Mode A
    for name, f in F_CLK.items():
        load = 100*(frameB*FS/L + isr*FS)/f
        print(f"  ISR {isr} cycles/sample @ {name.split()[0]} MHz: {load:.2f} %")

# =====================================================================================
# Update 4 (schematic S12 + S19 code + FIFO enabled by default)
# Framing per S19: codec master, DSP mode 16-bit, McASP burst, one 32-bit word per sample (L|R)
#   -> one McASP DMA request per sample (our reading of S19 xfmt/rfmt = 32-bit slot, burst).
# AFIFO pacing generates DMA requests (S14 §2.4.4), so FIFO-enabled I/O uses EDMA with
# ping-pong blocks of B samples and one EDMA completion interrupt per block.
print("\n=== Update 4: EDMA + AFIFO (RNUMEVT = WNUMEVT = 4 words), block B = 4 samples ===")
B = 4
for blk_isr in (300, 900):                      # ASSUMPTION: EDMA completion ISR + buffer swap, cycles per block
    for cpo in (1.0, 3.0, 5.0):
        cyc = ops*cpo + blk_isr/B
        print(f"  Mode A: {cpo} cyc/op, block ISR {blk_isr}: {cyc:.0f} cycles/sample -> "
              f"{100*cyc*FS/456e6:.2f} % @456 MHz, {100*cyc*FS/300e6:.2f} % @300 MHz")
for blk_isr in (300, 900):
    for name, f in F_CLK.items():
        load = 100*(frameB*FS/L + blk_isr*FS/B)/f
        print(f"  Mode B (frame work + block ISR {blk_isr}) @ {name.split()[0]} MHz: {load:.2f} %")
print("  FFT interrupts-off time no longer critical: RFIFO holds up to 64 words before overrun (S14 p.12)")

# =====================================================================================
# Update 5 (S19 package, GEL file and C67x DSPLIB v2.00 package read)
print("\n=== Update 5 checks ===")
print("  Default I/O now: Read FIFO ON (RNUMEVT 4), Write FIFO OFF; EDMA blocks of 4.")
print("  CPU cycles unchanged by turning the Write FIFO off (TX events are serviced by EDMA, not the CPU).")
# (a) DSPF_sp_biquad pole condition (S15 p.4-46): |a1| < 1 and |(a2 - a1^2)/a1| < 1
from scipy.signal import butter
sos = butter(4, 100, 'highpass', fs=FS, output='sos')
for i, s in enumerate(sos):
    a1, a2 = s[4], s[5]
    ok = abs(a1) < 1 and abs((a2 - a1*a1)/a1) < 1
    print(f"  HPF biquad {i+1}: a1={a1:.5f}, a2={a2:.5f}, |(a2-a1^2)/a1|={abs((a2-a1*a1)/a1):.4f} -> "
          f"DSPF_sp_biquad usable: {ok}")
print("  -> HPF stays in plain C (DF-II-T). DSPF_sp_biquad only for the T11 timing benchmark with test coefficients.")
# (b) ifftSPxSP scaling: if the library does not scale by 1/N, fold 1/N into H[k] at start-up -> 0 extra cycles/frame.
print("  ifftSPxSP 1/N scaling: unresolved (see hardware_notes §3.2); fixing it by folding 1/N into H[k] costs 0 cycles/frame.")
# (c) CPU clock sensitivity. NOTE (Update 6): the Update 5 'GEL bug' claim was WRONG - GEL line 732 is in device_PLL1()
#     (DDR PLL); device_PLL0() enables PLL0 at line 658. Kept only as a what-if: load if the core were left in bypass.
for name, f in (("456 MHz", 456e6), ("300 MHz", 300e6), ("24 MHz (PLL0 bypass, oscillator only)", 24e6)):
    worstA = 100*(ops*5.0 + 900/B)*FS/f
    worstB = 100*(frameB*FS/L + 900*FS/B)/f
    print(f"  Worst-case load at {name}: Mode A {worstA:.1f} %, Mode B {worstB:.1f} %")
print("  -> What-if only (no bug, see Update 6). Still confirm the clock on the board: PLL0_PLLCTL.PLLEN = 1 and TSCL count.")

# =====================================================================================
# Update 6: C674x DSPLIB 3.4.0.0 (installed at C:\ti\dsplib_c674x_3_4_0_0) replaces the C67x v2.00 library
# because CGT 8.1.3 links ELF only (README.txt line 112) and dsp67x.lib is COFF.
# Cycle figures from docs/DSPLIB_C674x_TestReport.html (C674x DSPLIB 3.4.0.0):
#   fftSPxSP 1965 (N=256), ifftSPxSP 1985 (N=256), fir_gen 10/16*Nr*Nh + 55, biquad 8*Nx + 72
print("\n=== Update 6: C674x DSPLIB 3.4.0.0 cycle figures (TestReport) ===")
cf6, ci6 = 1965, 1985
frameB6 = cf6 + ci6 + cmul + conv + ola + hpf + 500
print(f"  Mode B frame: fftSPxSP {cf6} + ifftSPxSP {ci6} + rest {cmul+conv+ola+hpf+500} = {frameB6} cycles/frame (was {frameB} with C67x v2.00)")
for blk_isr in (300, 900):
    for name, f in F_CLK.items():
        load = 100*(frameB6*FS/L + blk_isr*FS/B)/f
        print(f"  Mode B (C674x lib, block ISR {blk_isr}) @ {name.split()[0]} MHz: {load:.2f} %")
def fir_gen674(nh, nr):
    assert nh % 4 == 0 and nr % 4 == 0 and nh >= 4 and nr >= 4, "C674x DSPF_sp_fir_gen: nh, nr multiples of 4 (header Assumptions)"
    return 10/16*nr*nh + 55
print(f"  T11 benchmark: fir_gen nh=24 (G padded 21->24 with zeros), nr=48: {fir_gen674(24,48):.0f} cycles; biquad nx=48: {8*48+72} cycles")
print("  Mode A load unchanged (plain C, no DSPLIB in the real-time path).")
