"""End-to-end latency for the I/O options (Update 4; default changed in Update 5). Our calculation; buffering model = ASSUMPTION.
Run: python3 latency_check.py > latency_check_output.txt
"""
FS = 48000
BANK = 375            # Mode A filter-bank delay, samples (design_check.py / S3 eq. 15)
MODEB = 2*128 + 64    # Mode B: 2L + (M-1)/2, samples (05 §7 model)
CODEC = 17 + 21       # ADC + DAC group delay in samples (S13 p. 25, p. 29)
B = 4                 # EDMA ping-pong block, samples (DESIGN CHOICE)
RNUMEVT = 4           # Read FIFO threshold, words = samples with S19 framing (1 word per sample:
                      # rtdm = 1 slot, rfmt 32-bit slot, LCDK_Support_DSP.c Init_McASP0; "two Int16 read from McASP each time", ISRs.c line 17)
WFIFO_DEPTH = 64      # Write FIFO keeps itself full (S14 p. 52); 256 bytes = 64 x 32-bit words (S14 p. 12)
XBUF = 2              # XBUF + serializer shift register, words (ASSUMPTION)

def ms(n): return n/FS*1e3

cases = {
 "FIFO off, per-sample CPU ISR (Update 3 default; fallback)": 0,
 "Read FIFO ON (RNUMEVT 4) + EDMA blocks of 4, Write FIFO OFF  <-- DEFAULT (Update 5, accepted)": RNUMEVT + B + XBUF,
 "Read + Write FIFO ON (threshold 4) + EDMA blocks of 4 (Update 4 default; rejected in Update 5)": RNUMEVT + B + WFIFO_DEPTH + XBUF,
}
for name, extra in cases.items():
    a = BANK + extra + CODEC
    b = MODEB + extra + CODEC
    print(f"{name}:\n   extra I/O buffering {extra} samples = {ms(extra):.3f} ms | "
          f"Mode A {ms(a):.2f} ms | Mode B {ms(b):.2f} ms")
print("\nWhy 64 words = 1.33 ms, not 0.67 ms: with S19 framing one 32-bit word holds L+R (one word per sample period),")
print("so 64 words = 64 sample periods = 64/48000 s = 1.333 ms. The 0.67 ms figure assumes I2S with L and R in separate words (2 words/frame).")
print("\nTarget: <= 10 ms (S1, S6). Write FIFO adds up to 64 words because it 'attempts to stay filled' (S14 §2.4.4.1, p. 52).")
