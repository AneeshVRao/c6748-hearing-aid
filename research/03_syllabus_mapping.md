# 03 – Syllabus Mapping (Step 4)

**Depth levels:**

- **Core**: built and running on the board (or as an essential MATLAB design step) and part of the final system.
- **Supporting**: used in MATLAB design, testing or analysis, but not in the real-time signal path.
- **Comparison**: implemented only to compare against the core method (timing, accuracy). We say so openly.
- **Explained**: described in the report (with a measurement where noted), not implemented as a separate block. Added in Update 3 to avoid overclaiming.
- **Not covered**: with the reason.

"Exp." numbers refer to the tests in `07_testing_plan.md`. Section numbers refer to `05_system_design.md`.

## Unit 1 – DFT and filtering long sequences

| Syllabus topic | Where it appears in this project | Depth |
|---|---|---|
| DFT and its properties | Mode B: real-input symmetry (only 65 of 129 frequency samples are independent), circular shift = linear phase term, Parseval for level checks; MATLAB verification of `fft` against direct DFT | Core |
| Inverse DFT | Mode B: IFFT-256 per block (`DSPF_sp_ifftSPxSP`); frequency-sampling design formula is an inverse DFT | Core |
| Linear filtering using the DFT | Mode B: N = 256 ≥ L + M − 1 = 128 + 129 − 1 so circular convolution = linear convolution; MATLAB demo of what goes wrong with N too small (time aliasing) | Core |
| Overlap-add | Mode B real-time block method (L = 128 new samples, 128-sample tail added to next block) | Core |
| Overlap-save | MATLAB implementation with the same filter, compared with OLA on output equality and cost; optional board version (§10.5) | Comparison |

## Unit 2 – FFT algorithms

| Syllabus topic | Where it appears in this project | Depth |
|---|---|---|
| Radix-2 DIT FFT | (a) Our own C radix-2 DIT FFT-256 written as a learning step and checked against MATLAB; (b) `DSPF_sp_cfftr2_dit` + `DSPF_sp_bitrev_cplx` timed on board (Exp. T11) | Core (own code) / Comparison (timing) |
| Radix-2 DIF FFT | `DSPF_sp_icfftr2_dif` as the inverse transform chained after `cfftr2_dit`. The DIT output is bit-reversed and the DIF input expects bit-reversed data, so no bit reversal is needed [S15 p. 4-13, 4-34]. DIF flow graph in report | Comparison |
| Radix-4 FFT | `DSPF_sp_cfftr4_dif` at N = 256 = 4⁴ timed against radix-2 and mixed radix (formula: 3696 vs 4138 vs 2923 cycles) | Comparison (timing only) |
| Split-radix FFT | Theory in the report only. No TI library function exists in S15 and nothing is run | **Explained only** |
| Goertzel algorithm | On-board tone meter: measures output level at the 11 audiometric frequencies to verify band gains (Exp. T2), cheaper than a full FFT for a few bins | Core (test tool) |
| Chirp-Z transform | MATLAB `czt` zoom on the crossover regions (e.g., 600–900 Hz with 512 points) to inspect ripple at fine resolution | Supporting (analysis only) |

## Unit 3 – FIR filter design

| Syllabus topic | Where it appears in this project | Depth |
|---|---|---|
| Linear-phase FIR | G (21 taps) and F (31 taps) are Type I symmetric; constant group delay is what allows the delay alignment of bands (§7) | Core |
| Location of zeros | Zero plot of G: unit-circle zeros in stopband, reciprocal pairs off the circle (`calc/fig_prototype_filters.png`); half-band zero pattern of F | Core (design analysis) |
| FIR design by windowing | G and F: Kaiser-windowed sinc, length from Kaiser formula (A = 50 dB, Δf = 0.15 → 21 taps); compare rectangular/Hamming/Kaiser in MATLAB | Core |
| FIR design by frequency sampling | Mode B FIR (M = 129, 65 gain samples from audiogram); worked example in theory notes | Core |

## Unit 4 – IIR design from analog prototypes

| Syllabus topic | Where it appears in this project | Depth |
|---|---|---|
| Bilinear transform | Input DC/rumble HPF: 4th-order Butterworth at 100 Hz with pre-warping (MATLAB `butter` uses bilinear), runs on board | Core |
| Impulse invariance | MATLAB: design the same filter's low-pass analogue by impulse invariance and show aliasing; show why a high-pass cannot be done this way | Comparison |
| Matched z-transform | (a) MATLAB comparison of 1st-order 100 Hz HPF: matched-z pole 0.986995 vs bilinear 0.986995 (equal to 6 decimals at this low fc); (b) in the optional WDRC, the level-detector smoother (one-pole, α = e^(−1/(τ·fs))) is the matched-z mapping of an RC pole. The gain loop itself uses the [S4] eqs. (6)–(7) coefficients (`05` §6) | Comparison / Core if WDRC built |

## Unit 5 – FIR and IIR structures

| Syllabus topic | Where it appears in this project | Depth |
|---|---|---|
| FIR direct form | G and F as direct-form FIRs in plain C, run per sample on the board. `DSPF_sp_fir_gen` cannot be used per sample (nr ≥ 4, S15 p. 4-41); it is timed in the benchmark (T11) | Core |
| FIR cascade form | MATLAB: factor G into second/fourth-order sections, compare coefficient-quantisation sensitivity (Q15) against direct form | Comparison |
| FIR frequency-sampling structure | MATLAB: realise the Mode B FIR as comb (1 − z^−M) + resonator bank and verify it matches the direct FIR | Comparison |
| FIR lattice | MATLAB `tf2latc` on a non-linear-phase FIR (e.g., minimum-phase version of G). Note: a linear-phase FIR cannot be put in lattice form because its last reflection coefficient is ±1 | Comparison |
| IIR direct form I and II | HPF biquads coded both ways in C; compare memory (4 vs 2 states per biquad) and output equality; DF-II transposed is used in the final code (ASSUMPTION: better float behaviour) | Core |
| IIR cascade | HPF = 2 biquads in cascade, plain C on the board. `DSPF_sp_biquad` needs nx to be a multiple of 3 (S15 p. 4-46), so it is used only in the benchmark | Core |
| IIR parallel | MATLAB `residuez` partial-fraction form of the same HPF, output compared | Comparison |
| IIR lattice and lattice-ladder | MATLAB `tf2latc` on the HPF; use reflection coefficients |k| < 1 as a stability check | Comparison |

## Unit 6 – Multirate DSP

| Syllabus topic | Where it appears in this project | Depth |
|---|---|---|
| Decimation by D | Mode A: 4 cascaded ↓2 stages (G as anti-alias filter), total D up to 16 | Core |
| Interpolation by I | Mode A: 4 cascaded ↑2 stages with half-band F (gain 2), polyphase | Core |
| Rational I/D conversion | MATLAB: convert test speech (e.g., 44.1 kHz → 48 kHz, I/D = 160/147, or 16 → 48 kHz) for playback; optional board 48 → 32 kHz (I/D = 2/3) as in S2 | Supporting / optional |

## Unit 7 – DSP processors

| Syllabus topic | Where it appears in this project | Depth |
|---|---|---|
| TMS C6xxx architecture | C674x VLIW: 8 functional units, 2 data paths, 64 registers [S8][S9]. Report chapter + use of DSPLIB that exploits it | Core |
| Harvard architecture | Separate L1P (program) and L1D (data) caches, unified L2 [S8 p. 3, p. 13]; code and data placement in the linker file | **Explained** (+ memory placement) |
| Pipelining | Pipeline phases PG-PS-PW-PR / DP-DC / E1–E5 and delay slots (MPY 1, MPYSP 3, LDW 4, B 5) [S9 §4.1, Table 3-8]; effect of software pipelining measured with `-o0` vs `-o3` (T6) | **Explained + measured** |
| MAC hardware | 2 SP multiplies/clock, 4 × 16×16 multiplies/clock [S8 p. 1]; DSPLIB FIR cost ≈ nh·nr/2 cycles [S15 p. 4-41/4-43] = 2 MAC/cycle; measured in T11 | **Explained + measured** |
| Fixed vs floating point | C674x does both [S8]; MATLAB Q15 vs float experiment (coefficient quantisation, overflow with 30 dB gain); optional Q15 board build | Core (MATLAB) / Comparison (board) |
| Addressing modes | Circular buffers for all delay lines (power-of-2 sizes 32/512/256/128/16, as the hardware block size is 2^(N+1) bytes [S9 §2.8.3, §3.9.2]); optional `DSPF_sp_fircirc` demo [S15 p. 4-43] vs linear buffer | Core (circular buffer) / Comparison |
| Memory architecture | L1/L2/shared RAM/DDR2 map [S8]; placement of buffers in L2, test captures in DDR2 (§9 of `06`) | Core |
| On-chip peripherals | McASP (DSP-mode audio from the codec, Read FIFO on / Write FIFO off, EDMA events 0/1; MCASP0_INT event 61 for errors) [S14][S8 Tables 6-6, 6-12]; I2C (codec control at 0x18) [S13]; GPIO buttons S2/S3 and LEDs D4–D6 [S11]; TSCL cycle counter [S9]; EDMA3 events 0/1 as an option [S8 Table 6-12] | Core |

## Coverage summary

| Depth | Count | Topics |
|---|---|---|
| Core | 21 | DFT props, IDFT, DFT filtering, OLA, radix-2 DIT (own), Goertzel, linear-phase, zeros, windowing, frequency sampling, bilinear, FIR direct, IIR DF-I/II, IIR cascade, decimation, interpolation, C6x architecture, fixed vs float (MATLAB), addressing, memory, peripherals |
| Comparison | 10 | OLS, DIF, radix-4, impulse invariance, matched-z (unless WDRC), FIR cascade, FIR freq-sampling structure, FIR lattice, IIR parallel, IIR lattice/lattice-ladder |
| Supporting | 2 | Chirp-Z, rational I/D |
| Explained (+ measured where noted) | 4 | Split radix (explained only), Harvard architecture, pipelining (measured), MAC hardware (measured) |
| Not covered | 0 | — |

All topics listed in the brief appear above. The topics marked *Comparison* are only MATLAB or timing studies; the report should say so rather than claim they run in the hearing aid.
