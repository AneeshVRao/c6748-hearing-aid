# Syllabus coverage: where each topic is implemented

This covers every topic in `research/03_syllabus_mapping.md`, with the file that implements it and how it was verified.

**Status labels**
- **PC-verified:** the script or C test that checks it passes on the PC.
- **Board-verified:** measured on the LCDK (`docs/board_results.md`).
- **Board pending:** still needs a board measurement (`docs/board_checklist.md`).
- **Explained only:** described in the report, with no separate implementation.

## Unit 1 – DFT and filtering long sequences

| Topic | Implementation | Status |
|---|---|---|
| DFT and its properties | Direct DFT vs FFT: `python/p1_fft.py`; `ccs/hearing_aid/lab_modes.c` `lab_dft()`. Real-input symmetry used for the Mode B frequency samples: `python/dsp_ref.py` `freq_sampling_fir()` | Board-verified (N = 256: DFT 107.8 M cycles, DSPLIB FFT 2145) |
| Inverse DFT | `c/fft_own.c` (inverse with 1/N), `c/fft_dsplib.c` (`DSPF_sp_ifftSPxSP`), `c/modeB_ola.c`; start-up check `g_ifft_gain` | Board-verified (`g_ifft_gain` = 1.0) |
| Linear filtering using the DFT | `python/p1_ola.py` (time aliasing for N < L + M − 1); `lab_conv()` (circular vs linear convolution) | PC-verified |
| Overlap-add | `python/dsp_ref.py` `ola()`, `c/modeB_ola.c`, `c/ha.c` (real-time double buffering) | PC-verified (1e-14 Python, 2.8e-6 C) |
| Overlap-save | `python/dsp_ref.py` `ols()`, `python/p1_ola.py` | PC-verified (comparison) |
| FFT-based analysis (brief) | Noise suppression: block power spectrum at the 65 FIR frequency samples and per-block FIR redesign by frequency sampling (`dsp_ref.py` `mode_b_nr()`, `c/modeB_ola.c`). Howl detector: windowed FFT-256 peak search (`c/extras.c` `howl_block()`) | PC-verified (brief item; off by default) |

## Unit 2 – FFT algorithms

| Topic | Implementation | Status |
|---|---|---|
| Radix-2 DIT | own: `dsp_ref.py` `fft_dit()`, `c/fft_own.c` `fft_dit()`; DSPLIB `cfftr2_dit` in `lab_bench()` | Board-verified (cfftr2_dit 4668 cycles) |
| Radix-2 DIF | own: `dsp_ref.py` `fft_dif()`, `c/fft_own.c` `fft_dif()`; DSPLIB `icfftr2_dif` chained after `cfftr2_dit` in `lab_bench()` | PC-verified |
| Radix-4 | operation counts: `python/p1_fft.py`; DSPLIB `cfftr4_dif` + digit reversal in `lab_bench()` | Board-verified (4903 cycles) |
| Split radix | operation counts only (`python/p1_fft.py` `m_sr()`; 456 vs 642 radix-2 multiplies at N = 256) | **Explained only** (+ counts) |
| Goertzel | `dsp_ref.py` `goertzel()`, `c/goertzel.c`, on-board tone meter in `main.c` `run_internal()` | Board-verified (11 gains within 0.01 dB of design) |
| Chirp-Z transform | `python/p1_fft.py` (512-point zoom on the 750 Hz crossover, checked against `freqz`) | PC-verified (analysis only) |

## Unit 3 – FIR filter design

| Topic | Implementation | Status |
|---|---|---|
| Linear-phase FIR | G, F in `dsp_ref.py`; delay alignment in `c/modeA_bank.c` | PC-verified |
| Location of zeros | `python/p1_fir.py` (zero plots, reciprocal-pair check); `python/p2_structures.py` (unit-circle zeros block the lattice) | PC-verified |
| FIR by windowing | `python/p1_fir.py` (rectangular / Hamming / Kaiser) | PC-verified |
| FIR by frequency sampling | `dsp_ref.py` `freq_sampling_fir()`, `python/p1_fir.py` | PC-verified |

## Unit 4 – IIR design from analog prototypes

| Topic | Implementation | Status |
|---|---|---|
| Bilinear transform | HPF: `dsp_ref.py` `HPF_SOS`, `c/hpf.c`; `python/p1_iir.py` | Board-verified (DSP output = Python within 6e-6) |
| Impulse invariance | `python/p1_iir.py` (low-pass aliasing; impossible for the high-pass) | PC-verified (comparison) |
| Matched z-transform | `python/p1_iir.py` | PC-verified (comparison) |
| Bilinear transform (2nd design) | Feedback **notch** filter, pre-warped at f0: `dsp_ref.py` `notch_coeffs()`, `c/extras.c` `notch_design()` (designed on the DSP at run time), cascaded after the HPF | PC-verified (brief item; off by default) |

## Unit 5 – FIR and IIR structures

| Topic | Implementation | Status |
|---|---|---|
| FIR direct form | `c/modeA_bank.c` (G, half-band F); `p2_structures.py` | PC-verified |
| FIR cascade | `p2_structures.py` (10 second-order sections; 16-bit quantisation) | PC-verified (comparison) |
| FIR frequency-sampling structure | `p2_structures.py` (comb + 129 resonators) | PC-verified (comparison) |
| FIR lattice | `p2_structures.py` (minimum-phase Mode B FIR; G impossible, CHANGES C12) | PC-verified (comparison) |
| IIR direct form I and II | `p2_structures.py`; float32 DF-I / DF-II / DF-II-T noise in `p2_fixed_point.py` | PC-verified |
| IIR cascade | `c/hpf.c` (board), `p2_structures.py` | Board-verified |
| IIR parallel | `p2_structures.py` (`residuez`) | PC-verified (comparison) |
| IIR lattice and lattice-ladder | `p2_structures.py` (Gray–Markel; \|K\| < 1 stability check) | PC-verified (comparison) |

## Unit 6 – Multirate DSP

| Topic | Implementation | Status |
|---|---|---|
| Decimation by D | `c/modeA_bank.c` (4 × ↓2, D up to 16); `python/p1_multirate.py` (73 dB alias rejection) | Board-verified (Mode A output = Python within 6e-6) |
| Interpolation by I | `c/modeA_bank.c` (polyphase half-band); `python/p1_multirate.py` | Board-verified |
| Rational I/D | `python/p1_multirate.py` (44.1 → 48 kHz, 160/147) | PC-verified (supporting) |

## Unit 7 – DSP processors

| Topic | Implementation | Status |
|---|---|---|
| TMS320C6x architecture | Report §7 using the `lab_bench` cycle counts | Explained + board-measured |
| Harvard architecture | Report; code and data placement in `ccs/hearing_aid/hearing_aid.cmd` | **Explained** (+ placement) |
| Pipelining | Report; `-O0` vs `-O3` builds (`lab_bench_o0`, `internal_o0`) | Explained + board-measured (FIR loop 24×, modes 3.0–3.6×) |
| MAC hardware | Report; `DSPF_sp_fir_gen` vs plain-C FIR cycles in `lab_bench()` | Explained + board-measured (838 vs 1052 cycles) |
| Fixed vs floating point | `python/p2_fixed_point.py` (float32 vs Q15); `lab_arith()` (int16/int32/float/double MAC) | Board-verified (316 / 522 / 326 / 1000 cycles) |
| Addressing modes | Power-of-2 circular buffers with index masking in `c/modeA_bank.c` (512/256/128/16, 64/32 doubled histories). The hardware AMR circular mode is **explained only**: the compiler does not use it for C, and the optional `DSPF_sp_fircirc` demo was not built | Implemented (C circular buffers); hardware mode explained only |
| Memory architecture | `hearing_aid.cmd` (L2 RAM, DDR2 `.ddr` section); measured map in CHANGES C19 | Implemented |
| On-chip peripherals | `ccs/hearing_aid/board_io.c` (McASP + Read FIFO, EDMA3 PaRAM/linking, GPIO LEDs/buttons, TSCL); I2C/codec through the book's support file | Board-verified (McASP/EDMA/I2C/TSCL running, 0 errors); LEDs/buttons need a person at the board; no external audio input by decision (C31) |
