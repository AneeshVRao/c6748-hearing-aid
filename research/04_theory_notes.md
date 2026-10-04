# 04 – Theory Notes (Step 5)

Each topic has four parts: **Idea** (plain words), **Key equations**, **Worked example**, and **In our project**.

**New in this update:** §14 (delay/cost formulas, complementary split), §16 (gain rules) and §17 (WDRC).

**Textbook references.** The theory is standard and is covered in Proakis & Manolakis [S21]:

- Ch. 7 – DFT
- Ch. 8 – FFT
- Ch. 9 – structures
- Ch. 10 – filter design
- Ch. 11 – multirate

Oppenheim & Schafer [S22] covers the same material. Section numbers are not given because we could not confirm them. Worked-example numbers were checked in `calc/design_check.py`.

**Notation.**

| Symbol | Meaning |
|---|---|
| x[n] | input |
| h[n] | filter impulse response, length M |
| N | DFT/FFT size |
| W_N = e^(−j2π/N) | twiddle factor |
| fs | sampling rate |

---

## 1. DFT and its properties

**Idea.** The DFT takes N time samples and gives N frequency samples: how much of each frequency k·fs/N the signal contains.

**Key equations.**

- DFT: X[k] = Σ_{n=0}^{N−1} x[n] W_N^{kn}
- Inverse DFT: x[n] = (1/N) Σ_k X[k] W_N^{−kn}

Properties we use:

| Property | Statement |
|---|---|
| Linearity | DFT of (a·x + b·y) = a·X + b·Y |
| Circular shift | x[(n − m) mod N] ↔ W_N^{km} X[k] |
| Real-signal symmetry | X[N − k] = X*[k], so only N/2 + 1 bins are independent |
| Circular convolution | x ⊛ h ↔ X[k]·H[k] |
| Parseval | Σ \|x\|² = (1/N) Σ \|X\|² |

**Worked example.** x = [1, 2, 0, 0], N = 4. Then X[k] = 1 + 2·e^(−jπk/2):

- X[0] = 3
- X[1] = 1 − 2j
- X[2] = −1
- X[3] = 1 + 2j

X[3] = X[1]*, which shows the real-signal symmetry.

**In our project.** Mode B transforms every 256-sample block. The Mode B filter's 129-tap frequency response is described by only 65 independent samples because h[n] is real.

## 2. Linear filtering using the DFT

**Idea.** Multiplying two DFTs gives *circular* convolution. To get the normal *linear* convolution, zero-pad both sequences so the result has room: N ≥ L + M − 1.

**Worked example.** x = [1, 2], h = [1, 1].

- Linear convolution: [1, 3, 2].
- With N = 2 (too small), the circular result is [1 + 2, 3] = [3, 3]. The last sample has wrapped around (time aliasing).
- With N ≥ 3, the result is correct.

**In our project.** Block L = 128 and filter M = 129 give L + M − 1 = 256, so N = 256 is exactly enough (§5 of `05`).

## 3. Overlap-add and overlap-save

**Idea.** Audio never ends, so cut it into blocks, filter each block with the FFT, and join the pieces.

- **Overlap-add (OLA).** Each block of L new samples is zero-padded to N and filtered, which gives L + M − 1 outputs. The last M − 1 outputs ("tail") are added to the start of the next block's output.
- **Overlap-save (OLS).** Each FFT input holds N samples: M − 1 old samples plus L new ones. The first M − 1 outputs are wrong (circular wrap) and are discarded. The remaining L are kept.

**Key equations.**

- OLA: y = Σ_r y_r[n − rL], where y_r = IDFT{ DFT{x_r, N} · H[k] }.
- Cost per output sample ≈ [2·FFT(N) + N complex multiplies] / L.

**Worked example (our numbers).**

- OLA: N = 256, M = 129, L = 128. Each block produces 256 outputs. The first 128 go out (after adding the previous tail) and the last 128 are kept as the next tail.
- OLS: feed 256 samples (128 old + 128 new) and discard the first 128 outputs.

**In our project.** OLA is Mode B on the board. OLS is built in MATLAB as a comparison (optional on board).

## 4. FFT: radix-2 DIT and DIF

**Idea.** Split an N-point DFT into two N/2-point DFTs, again and again, until only 2-point "butterflies" remain. The cost drops from N² to about (N/2)·log2 N complex multiplies.

**Key equations.**

- **DIT** (split the input into even- and odd-indexed samples):
  - X[k] = E[k] + W_N^k O[k]
  - X[k + N/2] = E[k] − W_N^k O[k]
  - The input is in bit-reversed order (or the output is, depending on the version).
- **DIF** (split the output into even and odd bins):
  - Butterfly a' = a + b, b' = (a − b)·W_N^k
  - Output in bit-reversed order.

**Worked example.**

- N = 256: direct DFT needs 256² = 65,536 complex multiplies.
- Radix-2 needs (256/2)·8 = 1,024.
- Bit reversal for N = 8 (3 bits): index 1 = 001 → 100 = 4, and index 3 = 011 → 110 = 6.

**In our project.**

- We write our own radix-2 DIT in C (learning step).
- We time TI's `DSPF_sp_cfftr2_dit` (formula 2N·log2N + 42 = 4,138 cycles at N = 256 [S15]).
- The DIF form is used as the inverse transform, `DSPF_sp_icfftr2_dif`.

## 5. Radix-4 and split-radix

**Idea.** Radix-4 splits into four N/4 DFTs. Its butterfly needs fewer non-trivial multiplies, because multiplying by ±j is just a swap and sign change.

- Radix-4 complex multiplies ≈ (3N/8)·log2 N. That is 768 at N = 256, against 1,024 for radix-2 (both counts include trivial twiddles).
- Split-radix uses radix-2 for the even outputs and radix-4 for the odd outputs. It has the lowest operation count of the three for power-of-2 sizes (qualitative statement; we do not quote an exact count).

**In our project.**

- Comparison only. At N = 256 = 4⁴ the TI formulas give: radix-4 `DSPF_sp_cfftr4_dif` 3,696 cycles, radix-2 4,138, mixed-radix `DSPF_sp_fftSPxSP` 2,923 [S15].
- We measure these on the board (T11).
- No split-radix function exists in S15, so split-radix stays theory only.

## 6. Goertzel algorithm

**Idea.** If you only need a few frequency bins, run a tiny IIR filter for each bin instead of a full FFT.

**Key equations.** For bin k, with ω = 2πk/N:

- Run s[n] = x[n] + 2cos(ω)·s[n−1] − s[n−2] for n = 0 … N−1.
- Then |X[k]|² = s[N−1]² + s[N−2]² − 2cos(ω)·s[N−1]·s[N−2].
- Cost: 1 real multiply per sample per bin.

**Worked example.**

- 100 ms block at 48 kHz → N = 4800, so bins are 10 Hz apart. A 1 kHz tone sits in k = 1000·4800/48000 = 100.
- 11 audiometric bins cost 11 × 4800 = 52,800 multiplies per block. A 4800-point FFT is not a power of 2, and it would compute all 4800 bins we don't need.

**In our project.** The on-board tone meter measures the gain at each audiometric frequency (T2).

## 7. Chirp-Z transform

**Idea.** Evaluate the z-transform on any arc or segment, for example 512 points between 600 and 900 Hz only. It works as a "zoom FFT" without making the FFT huge.

**Key equations.**

- X(z_k) = Σ x[n] z_k^(−n), with z_k = A·W^(−k).
- It is computed with 3 FFTs (Bluestein's method).

**In our project.** MATLAB `czt` zooms on the crossover regions of the filter bank. This is analysis only.

## 8. Linear-phase FIR and zero locations

**Idea.** If h[n] is symmetric, every frequency is delayed by the same amount. Bands can then be lined up in time and added back without phase smearing.

**Key equations.**

- Symmetry: h[n] = h[M−1−n].
- Group delay = (M−1)/2 samples.
- Four types (I–IV) by odd/even length and symmetric/antisymmetric. Type I (odd M, symmetric) has no forced zeros at z = ±1, so it can do lowpass, highpass and bandpass.
- Zeros come in groups: z₀, 1/z₀, z₀*, 1/z₀*. Zeros on the unit circle come in conjugate pairs.

**Worked example.** G has M = 21, so its delay is 10 samples (0.21 ms at 48 kHz). Its zero plot (`calc/fig_prototype_filters.png`) shows:

- zeros on the unit circle across the stopband (these make the attenuation notches);
- one group of four zeros off the circle, z = 0.514 ± 0.102j and their reciprocals 1.873 ± 0.372j, which shape the passband. This is the reciprocal-conjugate quadruple predicted by linear phase (values calculated).

**In our project.** G and F are Type I. Their constant delays make the alignment formula in §7 of `05` possible.

## 9. FIR design by windowing

**Idea.** Take the ideal filter's infinite impulse response (a sinc), cut it to M samples, and taper the ends with a window to reduce ripple.

**Key equations.**

- h[n] = h_d[n]·w[n], where h_d[n] = sin(ω_c(n−α)) / (π(n−α)) and α = (M−1)/2.
- Kaiser window length: M ≈ (A − 7.95)/(14.36·Δf) + 1.
- Half-band filter: with ω_c = π/2, every second tap is zero (except the centre, which is 0.5).

**Worked example.**

- G: A = 50 dB, Δf = 0.15 → M ≈ 20.5 → 21. Kaiser β = 4.5 achieves 52.5 dB.
- F: half-band, 31 taps, 14 of them exactly zero → only 17 multiplies per output pair.

**In our project.**

- Mode A filters.
- MATLAB: `fir1(20, 0.25, kaiser(21,4.5))` and `fir1(30, 0.5, kaiser(31,4.5))` (MATLAB normalises to Nyquist).

## 10. FIR design by frequency sampling

**Idea.** Choose the desired gain at M equally spaced frequencies; the inverse DFT gives the filter. This suits a hearing aid well, because the audiogram is literally a list of gains at frequencies.

**Key equations.** For Type I (M odd), with H(k) = desired magnitude at f_k = k·fs/M:

h[n] = (1/M)·[ H(0) + 2·Σ_{k=1}^{(M−1)/2} H(k)·cos(2πk(n − α)/M) ]

**Worked example.** M = 5, H = [1, 1, 0] (pass DC and the first bin, stop the second):

- h = [−0.1236, 0.3236, 0.6000, 0.3236, −0.1236].
- Check: the sum is 1.000 = H(0).

**In our project.**

- Mode B: M = 129 at 48 kHz gives a grid every 372.1 Hz. The gains are interpolated from the audiogram on a log-frequency axis.
- The maximum deviation from the target (Bisgaard N3, half-gain) is 0.38 dB between grid points (calculated, `calc/design_check_output.txt`).

## 11. IIR design from analog filters

**Idea.** Analog filter theory (Butterworth etc.) is mature. Design in s, then map to z.

| Method | Mapping | Good / bad |
|---|---|---|
| Impulse invariance | Sample the analog impulse response: h[n] = T·h_a(nT); pole p → z = e^(pT) | Keeps the time shape, but **aliases**. Unusable for highpass or bandstop |
| Bilinear transform | s = (2/T)·(1 − z⁻¹)/(1 + z⁻¹) | No aliasing, stable → stable. Frequency is warped, so pre-warp: Ω = (2/T)·tan(ω/2) |
| Matched z | Map every pole *and* zero: (s − a) → (1 − e^(aT) z⁻¹) | Simple. Zeros near Nyquist can be misplaced; fine at low fc |

**Worked example.** First-order highpass, fc = 100 Hz, fs = 48 kHz, analog H(s) = s/(s + ω_c).

- **Bilinear (pre-warped):** K = tan(π·100/48000) = 0.006545.
  - H(z) = 0.993497·(1 − z⁻¹)/(1 − 0.986995·z⁻¹).
- **Matched z:** the zero at s = 0 maps to z = 1, and the pole maps to e^(−2π·100/48000) = 0.986995. At such a low fc the two methods agree to 6 decimals.
- **Impulse invariance:** h_a(t) = δ(t) − ω_c·e^(−ω_c t). The δ(t) term cannot be sampled, which shows why the method fails for a highpass.

**In our project.**

- 4th-order Butterworth HPF at 100 Hz, bilinear, runs on the board (removes codec DC and rumble).
- The WDRC smoother α = e^(−1/(τ·fs)) is the matched-z (equivalently impulse-invariant) image of an RC low-pass.

## 12. FIR structures

| Structure | Equation / idea | In our project |
|---|---|---|
| Direct form | y[n] = Σ h[k]·x[n−k] (tapped delay line) | G and F on the board |
| Cascade | H(z) = Π of 2nd/4th-order sections | MATLAB: Q15 sensitivity versus direct form |
| Frequency-sampling | H(z) = (1 − z^(−M))/M · Σ_k H(k)/(1 − e^(j2πk/M)·z⁻¹): a comb plus a bank of resonators | MATLAB: rebuild the Mode B FIR and check equality |
| Lattice | Stages f_m = f_{m−1} + K_m·g_{m−1}(n−1), g_m = K_m·f_{m−1} + g_{m−1}(n−1) | MATLAB only. A linear-phase FIR has \|K_last\| = 1, so the lattice does not apply; use a minimum-phase FIR instead |

## 13. IIR structures

**Biquad:** H(z) = (b0 + b1·z⁻¹ + b2·z⁻²)/(1 + a1·z⁻¹ + a2·z⁻²).

| Structure | Idea | In our project |
|---|---|---|
| Direct form I | Separate delay lines for x and y (4 states per biquad) | Coded on board for comparison |
| Direct form II | One shared delay line (2 states) | Coded; the transposed DF-II is used in the final version |
| Cascade | Chain of biquads | HPF = 2 biquads in plain C (`DSPF_sp_biquad` needs nx to be a multiple of 3 [S15 p. 4-46], so it is used only in the benchmark) |
| Parallel | Partial fractions: sum of 1st/2nd-order sections | MATLAB `residuez` comparison |
| Lattice / lattice-ladder | Reflection coefficients K_m (all-pole part) + ladder taps (zeros); stable if all \|K_m\| < 1 | MATLAB `tf2latc` as a stability check |

**Worked example (biquad 1 of the HPF, calculated):**

- b = [0.98304, −1.96608, 0.98304], a = [1, −1.97593, 0.97610].
- Pole radius = √0.97610 = 0.98798 < 1, so the section is stable.

## 14. Multirate: decimation, interpolation, rational change

**Idea.**

- To lower the rate by D, low-pass first (so nothing folds over), then keep every D-th sample.
- To raise the rate by I, insert I − 1 zeros, then low-pass to remove the copies ("images") and multiply by I.
- For a rational factor I/D, interpolate first, then decimate. Use one filter with cutoff min(π/I, π/D).

**Key equations.**

- Decimation: y[m] = Σ h[k]·x[mD − k].
- Polyphase: compute only the outputs you keep, which costs about 1/D (or 1/I) of the naive amount.

**Worked example.**

- Level 0: 48 kHz → 24 kHz with G (stopband from 0.20·48k = 9.6 kHz). The aliases come from 14.4–24 kHz (≥ 0.30·fs) and land at 0–9.6 kHz, where G has already attenuated them by ≥ 52 dB.
- Rational example for test files: 44.1 kHz → 48 kHz needs I/D = 160/147 (since 48000/44100 = 160/147).

**In our project.**

- Mode A tree (4 × ↓2, 4 × ↑2, half-band F, polyphase).
- 5.1× fewer operations than single-rate (calculated, §9 of `05`).

**Delay and cost of a multirate path [S3, eqs. (15)–(16), p. 1386].** For a band whose signal passes through K odd-length linear-phase filters, filter i with N_i taps at rate fs_i:

- Delay in input samples: d = Σ (N_i − 1)/2 · (fs/fs_i).
- Multiplies per input sample: c = Σ (N_i + 1)/2 · (fs_i/fs).

A filter at a 2× lower rate costs half as much but adds twice the delay (in input samples). Worked example, our B1 path: d = 10·(1+2+4+8) + 15·(1+2+4+8) = 375 samples = 7.81 ms (our calculation).

**Complementary split [S1 §II-C; S4 cols. 3–4].** The complement of a filter H is "impulse minus H", because an impulse is the all-pass. If neighbouring band edges are exact complements, the bands add back to the input. Mode A uses this as band = z^(−10)·x − G·x.

## 15. DSP processor: TMS320C6748 (facts from S8, S9, S14)

| Topic | Facts | Why it matters to us |
|---|---|---|
| Architecture | C674x VLIW core, fixed + floating point, 375/456 MHz, up to 3648 MIPS / 2746 MFLOPS. Eight functional units (.L, .S, .M, .D on two data paths), 64 × 32-bit registers [S8][S9] | Up to 8 instructions per cycle if the compiler can schedule them |
| Harvard architecture | Separate program (L1P, 32 KB) and data (L1D, 32 KB) memories [S8] | Instruction fetch and data access happen in the same cycle |
| Pipelining | Fetch (PG, PS, PW, PR) → decode (DP, DC) → execute (E1–E5) [S9 §4.1]. Fetch packet = 8 instructions; execute packet = 1–8 parallel instructions [S9 §4.1.1–4.1.2]. Delay slots: MPY 1, MPYSP/ADDSP 3, LDW 4, B 5 [S9 Table 3-8 and instruction pages]. Loops are software-pipelined (SPLOOP buffer [S9 Ch. 7]) | `-o3` builds overlap loop iterations: expect large cycle drops against `-o0` (T6) |
| MAC hardware | 2 SP float multiplies/clock; 4 × 16×16 or 2 × 32×32 fixed multiplies/clock [S8] | DSPLIB FIR ≈ nh·nr/2 cycles [S16], i.e. about 2 MACs per cycle |
| Fixed vs floating point | Floating point gives dynamic range without manual scaling. Fixed point (Q15) is cheaper per op on many DSPs but needs scaling. A 30 dB gain = ×31.6 needs about 5 bits of headroom | We run float; Q15 is checked in MATLAB |
| Addressing modes | Linear and circular addressing for A4–A7/B4–B7, set in AMR; circular block = 2^(N+1) bytes [S9 §2.8.3, §3.9.2] | Circular buffers make FIR delay lines without data copying. Sizes must be powers of two (we use 32/512/256/128/16 floats) |
| Memory | L2 256 KB at 0x0080 0000 (local) / 0x1180 0000 (global); shared RAM 128 KB at 0x8000 0000; DDR2 at 0xC000 0000 (LCDK has 128 MB [S11]) [S8] | All real-time data fits in L2; long test captures go to DDR2 |
| Peripherals | McASP (I2S/TDM/DSP formats, 16 serializers, 256-byte audio FIFO, Read side used by default; EDMA events 0/1, interrupt event 61) [S8][S14]; EDMA3 (64 channels; McASP events 0/1) [S8]; I2C (codec at 0x18 [S13]); 64-bit timers and the TSCL cycle counter [S8][S9 §2.9.14]; GPIO buttons/LEDs [S11] | Audio I/O, ping-pong buffering, codec control, cycle timing |

## 16. Hearing-loss gain rules (audiogram → band gain)

**Idea.** An audiogram lists the hearing threshold (dB HL) at each test frequency. A fitting rule turns it into a gain per frequency.

**Rules.**

- **Half-gain rule:** gain = ½ × hearing loss. Attributed to Lybarger 1944/1963, cited via Venema 2001 [S27].
- **NAL-R** (Byrne & Dillon 1986, cited via [S27]) gives slightly less than half gain, with a flatter shape. We illustrate it with 0.4 × HL. **The factor is our choice, not the NAL-R formula.**
- Rules for compression aids (NAL-NL1, DSL) give different gains for soft and loud inputs [S27].

**Worked example.** Bisgaard N3 at 2121 Hz, interpolated between 50 dB (2 kHz) and 55 dB (3 kHz) [S26 Table 2]:

- t = log₂(2121/2000) / log₂(1.5) = 0.145.
- HL = 50 + 0.145 × 5 = 50.73 dB.
- Half gain = 25.36 dB.
- ×0.4 = 20.29 dB.

**In our project.** Static per-band gains for Mode A and the Mode B gain curve; full tables in `research/audiogram.md`.

## 17. Wide dynamic range compression (WDRC) and the AGC loop (optional extra)

**Idea.** Soft sounds get more gain, loud sounds less. Above a knee point, the output rises by only 1/CR dB per dB of input. The gain must change smoothly: fast enough to catch loud onsets (attack), slow enough not to "pump" (release).

**Key equations [S4 eqs. (1)–(7), cols. 9–10; same as S2 eqs. (1)–(7)].** All levels are in dB.

- **Loop:** A[n+1] = A[n] + α(R[n] − (X[n] + A[n])), where R is the target output from the input/output curve.
- **Step response** (input jumps 55 → 90 dB; G0 = gain before, G∞ = gain after): A[n] = (G0 − G∞)(1 − α)^n + G∞. This is a first-order (one-pole) system.
- **Choose α** so the gain is within 3 dB of final after AT samples (attack) or within 4 dB after RT samples (release):
  - α_attack = 1 − (3/(G0 − G∞))^(1/AT)
  - α_release = 1 − (4/(G0 − G∞))^(1/RT)
  - G0 − G∞ = A1 − A2 + 35.
- **Envelope** (S2 §III-B): magnitude of the analytic signal from a Hilbert filter, computed at each band's reduced rate.

**Worked example (our calculation).** Band rate 6 kHz, CR 3:1, AT = 10 ms = 60 samples, RT = 20 ms = 120 samples.

- G0 − G∞ = 35 − 35/3 = 23.33 dB.
- α_attack = 1 − (3/23.33)^(1/60) = 0.0336.
- α_release = 1 − (4/23.33)^(1/120) = 0.0146.

**Syllabus link.** The loop is a first-order IIR filter acting on the gain. Its pole is at z = 1 − α. Stability needs |1 − α| < 1, i.e. 0 < α < 2; values 0 < α < 1 give the smooth, non-oscillating approach used here. This is the same pole-location idea as in §13.

**In our project.** OPTIONAL – confirm; see `05` §6 and `research/literature_extracts.md` B4–B5.

