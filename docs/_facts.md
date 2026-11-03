# Fact inventory for `docs/project_document.md` (working file)

Built 3 Nov 2026 from the repository only. Every number in the project document must appear here.

**Tags**
- **BOARD**: measured on the LCDK C6748 (readouts in `results/phase4/board/`, summarised in `docs/board_results.md`).
- **SIM**: computed on the PC (Python, MATLAB or the portable C build).
- **CALC**: calculated or estimated from a formula or model, not measured.
- **LIT**: taken from a published source (IDs from `research/02_sources.md`).
- **DESIGN**: a design choice made by the team.
- **DERIVED**: simple arithmetic done for this document from numbers above (working shown).
- **EVERYDAY**: an everyday comparison, not from the repository (from the writing brief).

Note: the folder `results/board/` named in the brief does not exist. Board readouts live in `results/phase4/board/`.

---

## 1. Project facts

| # | Fact | Tag | Source |
|---|---|---|---|
| P1 | Title, team (Aneesh Venkatesha Rao 24ECB0A03, Akula Sahasra 24ECB0A02, Adhvay Shrujal 24ECB0A01), DSP Lab, ECE, NIT Warangal, Batch 1 | — | `docs/report.md` header |
| P2 | Report v1.0, final, 31 Oct 2026; code frozen at v1.0 | — | `docs/report.md`, `docs/CHANGES.md` "Freeze" |
| P3 | Work dates: Phase 0–3 on 4 Oct 2026, MATLAB run 8 Oct, board bring-up 15 Oct, seal-off 31 Oct | — | `docs/CHANGES.md` |
| P4 | Test speech: Windows text-to-speech voices (Microsoft David, 44.1 kHz, 16-bit; second voice "Zira") | — | `README.md`, `python/p3_notch_nr.py` |
| P5 | Built-in speech clip on the board: 2 s, −40 dBFS RMS | DESIGN | `ccs/hearing_aid/speech_clip.c` header, `docs/CHANGES.md` |

## 2. Hardware and set-up

| # | Fact | Tag | Source |
|---|---|---|---|
| H1 | Board: TI LCDK with TMS320C6748 (C674x core), 256 KB L2 memory, 128 MB DDR2 | LIT [S8, S11] | `docs/report.md` §2 |
| H2 | CPU clock 300 MHz (PLL: 24 MHz × 25 / 2) | BOARD | `docs/board_results.md` smoke test step 3 |
| H3 | Clock checked against PC timer: 300.20 / 299.89 MHz (PC timing ±0.1 %); on-board estimate 300 001 218 Hz (300.001 MHz) after fix C27 | BOARD | `docs/board_results.md` step 2 |
| H4 | Exactly 6250.0 cycles per sample (300 MHz / 48 kHz) | BOARD | `docs/board_results.md` step 2 |
| H5 | Device maximum clock 456 MHz; board run at 300 MHz (TI GEL) | LIT [S8] / DESIGN | `research/05_system_design.md` §9, CHANGES C3 |
| H6 | Sample rate 48 kHz, 16-bit codec TLV320AIC3106 | DESIGN / BOARD (48.0 kHz measured) | `docs/report.md` §2, §6.1 |
| H7 | Audio moved in 4-sample blocks; one interrupt per block = 83.3 µs; budget 25 000 cycles per block | DESIGN / CALC | `docs/report.md` §2, §6.3 |
| H8 | C674x: up to 8 instructions per cycle on 8 functional units (2 × .L .S .M .D), 64 registers, hardware floating point | LIT [S8, S9] | `docs/report.md` §7, `docs/viva_notes.md` |
| H9 | Separate L1P (program) / L1D (data) caches, unified 256 KB L2 (Harvard) | LIT [S8] | `docs/report.md` §7 |
| H10 | Code `.text` 22.1 KB; total L2 use 68.6 KB of 255 KB (16 KB stack) | BOARD build (linker map) | CHANGES C19 |
| H11 | Controls: S2 = mode (LED D4), S3 = preset N3/N2/S2/bypass (D5 blinks); DIP SW1-5 = noise suppression, SW1-6 = auto notch; D6 = CPU-busy pin | DESIGN | `docs/report.md` §2 |
| H12 | Read FIFO on (4 words), Write FIFO off; Write FIFO would add 64 samples = 1.33 ms | DESIGN / CALC | `research/calc/latency_check_output.txt`, `docs/viva_notes.md` |
| H13 | Board driven headless from the command line with CCS Debug Server Scripting (`tools/dss_run.js`) | — | `docs/report.md` §4 |
| H14 | Three I/O modes: `IO_LIVE`, `IO_STORED_LINEOUT`, `IO_INTERNAL` | DESIGN | `docs/report.md` §2 |
| H15 | 16 board programs build with 0 warnings | SIM (build) | CHANGES "Freeze" |
| H16 | Tools: CCS 7, TI compiler 8.1.3, C674x DSPLIB 3.4.0.0, Python 3.12, MATLAB, GCC 16 | — | `docs/report.md` §2 |

## 3. Design numbers

| # | Fact | Tag | Source |
|---|---|---|---|
| D1 | Delay target under 10 ms (wearer also hears the direct sound; longer delay gives comb filtering / echo) | LIT [S1, S6] | `docs/report.md` §1 |
| D2 | Input high-pass: 4th-order Butterworth at 100 Hz, bilinear transform, 2 biquads; measured −3.01 dB at 100 Hz | DESIGN / SIM | `docs/report.md` §3.1, §5.1 |
| D3 | Matched-z HPF agrees with bilinear to 0.000 dB above 50 Hz | SIM | `docs/report.md` §3.1 |
| D4 | Mode A: 5 bands, crossovers 750 Hz, 1.5 kHz, 3 kHz, 6 kHz; band rates 48/24/12/6/3 kHz | DESIGN | `docs/report.md` §3.2 |
| D5 | G: 21-tap Kaiser (β = 4.5) low-pass, stopband 52.5 dB; F: 31-tap half-band (17 non-zero taps, centre 0.5), stopband 51.1 dB | DESIGN / SIM | `docs/report.md` §3.2 |
| D6 | Kaiser length formula N ≈ (A − 7.95)/(14.36 Δf) + 1; A = 50 dB, Δf = 0.15 → 21; Δf = 0.10 → 31 | LIT [S21] / CALC | `docs/report.md` §3.2 |
| D7 | Alias rejection −73.4 dB per level; image rejection −74.4 dB; G is 52 dB down at 0.20 fs_k, and after ↓2 the band 0.30–0.50 fs_k folds onto 0–0.20 fs_k | SIM | `docs/report.md` §3.2, §5.1 |
| D8 | Mode A delay T_k = 10 + 15 + 2·T_{k+1} → 375 samples = 7.81 ms; simulated impulse peaks at 375 | CALC / SIM | `docs/report.md` §3.2 |
| D9 | Lowest level alone costs 4.17 ms of delay; stage delays 0.52 / 1.04 / 2.08 / 4.17 ms | CALC | `research/05_system_design.md` §7 |
| D10 | Mode A cost 61 operations per sample vs 313 single-rate: 5.1× cheaper | CALC | `docs/report.md` §3.2 |
| D11 | Mode A history buffers 512/256/128/16 (power of two, masked index); alignment delays 365/165/65/15 samples | DESIGN | `docs/report.md` §3.2 |
| D12 | Reconstruction with all gains 1: ripple +0.020 / −0.010 dB; output = input delayed by 375 samples | SIM | `docs/report.md` §3.2, §5.1 |
| D13 | Mode B: 129-tap FIR by frequency sampling, 65 gain points spaced 372 Hz; block L = 128, FFT N = 256 (≥ 128 + 129 − 1) | DESIGN | `docs/report.md` §3.3 |
| D14 | Mode B FIR follows N3 within 0.38 dB; Kaiser-window design of same length 1.00 dB (MATLAB 1.01) | SIM | `docs/report.md` §3.3, CHANGES C26 |
| D15 | OLA and OLS vs direct convolution: 1.1e-14 / 1.2e-14 | SIM | `docs/report.md` §5.1 |
| D16 | Undersized FFT (time aliasing): errors 0.29 / 9.5 / 18.9 at N = 224 / 192 / 160 | SIM | `docs/report.md` §3.3 |
| D17 | Mode B FFT: DSPLIB `DSPF_sp_fftSPxSP` / `ifftSPxSP`; own radix-2 FFT as build option | DESIGN | `docs/report.md` §3.3 |
| D18 | Band gains (N3, half-gain, 30 dB cap): B5 30.00, B4 30.00, B3 25.36, B2 20.36, B1 17.50 dB; B4 was 30.36 before the cap | CALC | `research/audiogram.md` §3 |
| D19 | Bisgaard N3 thresholds 35, 35, 35, 35, 40, 45, 50, 55, 60, 65 dB HL at 250…6000 Hz; N2 20…50; S2 20…95; no 8 kHz value | LIT [S26] | `research/audiogram.md` §1 |
| D20 | Half-gain rule: gain = 0.5 × hearing loss (Lybarger 1944, 1963, cited via Venema; original not read) | LIT [S27] | `research/audiogram.md` §3 |
| D21 | 30 dB gain cap: design choice to limit feedback and clipping | DESIGN | `research/audiogram.md` §3 |
| D22 | Accuracy vs target: N3 Mode A 1.53 dB (at 750 Hz), Mode B 0.38 dB; Bisgaard S2 Mode A 6.82 dB (at 1.5 kHz), Mode B 0.49 dB; N2 1.01 / 0.22 dB | SIM | `research/audiogram.md` §4 |
| D23 | S2 has a 15.7 dB (15.73) step between neighbouring bands B2 and B3 | CALC | `research/audiogram.md` §4 |
| D24 | 3 dB "just noticeable" limit used by Sokolova et al.; N2 and N3 stay within it in both modes | LIT [S1, S2] / SIM | `research/audiogram.md` §4 |
| D25 | Limiter at −1 dBFS; speech at −40 dBFS RMS (peaks −19.9 dBFS, ~20 dB crest factor) with 30 dB gain: 0.04 % of samples limited (Mode A), 0.03 % (Mode B) | DESIGN / SIM | `docs/report.md` §3.4, CHANGES C11, `c/coeffs.h` |
| D26 | Notch: 2nd-order IIR, bilinear transform, Q = 10; depth 270 dB; −3 dB bandwidth 264 Hz vs f0/Q = 270 Hz | DESIGN / SIM | `docs/report.md` §3.5 |
| D27 | Howl detector: Hann-windowed FFT-256 per 128-sample block, 500 Hz–8 kHz, peak ≥ 25 dB above mean, stable ±1 bin, leaky counter triggers at 75, max 2 notches | DESIGN | `docs/report.md` §3.5, `c/coeffs.h` |
| D28 | Noise suppression gain G = √max(1 − 2N/P, Gmin²), floor Gmin = −12 dB; noise floor by minimum statistics (min of P over 4 × 0.375 s = 1.5 s) | DESIGN | `docs/report.md` §3.5, CHANGES C24 |
| D29 | Six bands would push delay to about 16 ms (16.9 ms in REVIEW) | CALC | `docs/viva_notes.md`, `research/REVIEW.md` §d |
| D30 | 60 dB stopbands (ANSI S1.11 class 2) need G = 27, F = 39 taps → latency 10.79 ms | CALC | `docs/report.md` §8.3 |
| D31 | Codec delay ADC 17/fs + DAC 21/fs = 38 samples = 0.79 ms | LIT [S13] / CALC | `research/05_system_design.md` §7 |
| D32 | Goertzel meter length N = 4608 (96 ms); N = 4800 read 375 Hz 9.3 dB low (C10) | SIM | CHANGES C10 |
| D33 | Block-based Mode A with DSPLIB estimated ~2 % CPU (not built) | CALC | `docs/report.md` §8.1 |
| D34 | Literature delays: Sokolova 2022 32 ms (linear phase, 11 bands) and 5.4 ms (minimum phase) | LIT [S2] | `research/05_system_design.md` §7 |

## 4. Latency (all CALCULATED, none measured on the board)

| # | Fact | Tag | Source |
|---|---|---|---|
| L1 | Mode A end-to-end 8.81 ms = (375 + 10)/48000 + 0.79 ms | CALC | `research/calc/latency_check_output.txt` |
| L2 | Mode B end-to-end 7.67 ms = (320 + 10)/48000 + 0.79 ms; 320 = 2L + (M − 1)/2; buffering model is an assumption | CALC | same; `docs/report.md` §3.3 |
| L3 | Extra I/O buffering 10 samples = 0.208 ms (assumption) | CALC | same |
| L4 | With Write FIFO on: Mode A 10.15 ms (over target), Mode B 9.00 ms | CALC | same |
| L5 | FIFO-off fallback: Mode A 8.60 ms, Mode B 7.46 ms | CALC | same |
| L6 | Mode B buffering delay exactly 256 samples in the PC C build | SIM | CHANGES Phase 3 summary |
| L7 | Latency not measured on the board because no external input was used (C31) | — | CHANGES C31, C37 |

## 5. Results on the PC

| # | Fact | Tag | Source |
|---|---|---|---|
| R1 | G stopband by method (21 taps): rectangular 24.2, Hamming 38.6, Kaiser 52.5, frequency sampling 19.6 (41.0 with a transition sample) dB | SIM | `docs/report.md` §5.1 |
| R2 | Own radix-2 DIT/DIF FFT vs reference, N = 8…1024: ≤ 7.6e-14 | SIM | `docs/report.md` §5.1 |
| R3 | Complex multiplies at N = 256: radix-2 642, radix-4 492, split radix 456 | CALC | `docs/report.md` §5.1 |
| R4 | Goertzel 11 tones all read 0.100000 after fix | SIM | `docs/report.md` §5.1 |
| R5 | Chirp-Z zoom 600–900 Hz: 18.08 to 20.06 dB, matches `freqz` | SIM | `docs/report.md` §5.1 |
| R6 | 44.1 → 48 kHz resampling (160/147): 48000 samples, amplitude 0.500 | SIM | `docs/report.md` §5.1 |
| R7 | float32 vs Q15 SNR: HPF 85.0 vs 12.1 dB; Mode A 138.7 vs 42.7; Mode B 139.5 vs 20.2 | SIM | `docs/report.md` §5.2 |
| R8 | HPF with 16-bit coefficients: direct 4th order unstable (pole radius 1.000000); cascade −3 dB at 100.8 Hz, 0.16 dB error; parallel loses DC zeros (−2.3 dB at 20 Hz); lattice-ladder −3 dB moves to 130 Hz | SIM | `docs/report.md` §5.2 |
| R9 | Biquad form noise in float32: DF-II-T 85.0, DF-I 83.1, DF-II 74.6 dB SNR | SIM | `docs/report.md` §5.2 |
| R10 | FIR lattice impossible for G (zeros on unit circle, \|K\| = 1); shown on minimum-phase Mode B FIR, max \|K\| = 0.48 | SIM | CHANGES C12 |
| R11 | C vs Python: HPF 3.6e-6, FFT 1.2e-7 of peak, Mode A 3.4e-6, Mode B 2.8e-6, full chains ≤ 2.2e-5, NR chains ≤ 1.9e-5; gates 1e-5 (blocks) / 1e-4 (chains) | SIM | `docs/report.md` §5.3 |
| R12 | HPF state needed double precision: float32 state error 3.9e-5 (1.3 LSB); chain then 2.8e-4, failing the 1e-4 gate | SIM | CHANGES C14 |
| R13 | Notch activation in C at the same sample (50 816) and frequency (2495.30 Hz) as Python | SIM | `docs/report.md` §5.3 |
| R14 | Howl on PC: 2.7 kHz removed after 0.20 s (49 dB down); 1.9 kHz after 0.41 s; no false notch on either voice; criterion relaxed 0.3 s → 0.5 s | SIM | CHANGES C23, C25 |
| R15 | Noise suppression on PC: SNR +5.9 to +8.5 dB (A), +6.5 to +9.4 dB (B); two voices, white/pink noise, 0/5/10 dB SNR; speech level −0.9 to −4.1 dB | SIM | `docs/report.md` §3.5 |
| R16 | `run_all.py` 12/12 pass; MATLAB mirrors run 8 Oct 2026 and reproduce Python (small differences in C26) | SIM | CHANGES "Freeze", C26 |
| R17 | Crossover spurs: −68 dBc worst (gate −60 dBc) | SIM | `docs/report.md` §8.4 |

## 6. Results on the board

| # | Fact | Tag | Source |
|---|---|---|---|
| B1 | DSP output vs Python, built-in tones/noise: Mode A 6.1e-6 (= 0.0000061), Mode B 6.1e-6, A + NR 2.0e-5 (= 0.000020 = 0.00002), B + NR 9.4e-6 (gate 1e-4 = 0.0001) | BOARD | `results/phase4/board/compare_internal.txt` |
| B2 | On-board Goertzel gains, Mode A: 17.40 17.41 17.65 19.03 20.66 23.33 25.60 28.02 29.66 30.00 30.00 dB at 250…8000 Hz | BOARD | `compare_internal.txt` |
| B3 | On-board gains, Mode B: 17.59 17.50 17.27 17.53 19.67 22.50 25.00 27.50 29.89 29.99 30.02 dB | BOARD | `compare_internal.txt` |
| B4 | Targets: 17.5 17.5 17.5 17.5 20.0 22.5 25.0 27.5 30.0 30.0 30.0 dB | CALC | `docs/report.md` §6.2 |
| B5 | Board gains equal simulated design within 0.01 dB (gate 0.05 dB) | BOARD | `results/phase3/board_expected.txt`, `docs/board_results.md` step 6 |
| B6 | Live CPU load (codec running, 60 s per mode): Mode A 10.5 % (max 11.1 %), interrupt 2617 avg / 2785 max cycles per 4 samples; Mode B 4.2 % (max 4.3 %), interrupt 829 / 851, background 7242 / 7253 per 128 samples | BOARD | `results/phase4/board/T6_live.txt` |
| B7 | In those 60 s runs: 0 overruns, 0 clips, RSTAT = XSTAT = 0 | BOARD | `T6_live.txt` |
| B8 | Pre-board estimates: Mode A 2.5–10.2 %, Mode B 2.6–5.0 % at 300 MHz | CALC | `docs/report.md` §6.3 |
| B9 | About 90 % of the CPU left free in both modes | DERIVED in report | `docs/report.md` §6.3 |
| B10 | No codec (processing only): Mode A 10.1 %, Mode B 3.8 %, A + NR 25.1 %, B + NR 12.0 % | BOARD | `docs/board_results.md` step 6 |
| B11 | Noise suppression on board (2 s speech + on-board white noise, 5 dB SNR): Mode A +8.39 dB SNR (speech −1.93, noise −10.33 dB), Mode B +8.78 dB (speech −1.56, noise −10.34), i.e. speech down 1.6–1.9 dB; board = Python within 2e-5 | BOARD | `results/phase4/board/speech_nr/compare.txt` |
| B12 | NR loads on the speech clip: 24.5 % (A), 11.8 % (B) | BOARD | `docs/report.md` §6.3 |
| B13 | Auto notch: 12 s of speech (2 s clip looped 6×), no false notch | BOARD | `notch_stored_speech_only.txt` |
| B14 | Auto notch: speech + 2500 Hz tone 10 dB above speech, one notch placed within 0.5 s, at 2500.48828 Hz (readout); other runs 2500.49 / 2500.83 Hz; error ≤ 0.03 % | BOARD | `notch_stored_tone.txt`, `docs/board_results.md` step 10 |
| B15 | Listening demo at +10 dB: user heard the whistle stop; limiter acted on 81 279 samples in the 16 s run (vs 117 / 39 / 156 from speech peaks at 0 dB) | BOARD (+ user's ear) | `docs/board_results.md` step 10 |
| B16 | Tone at speech level (0 dB): no notch in 16 s, as designed; detection threshold between 0 and +10 dB not measured | BOARD | CHANGES C32 |
| B17 | Read FIFO: one interrupt per 4 samples, 104 cycles per interrupt; fallback per-sample path 213 cycles; fallback longest interrupt 1875 of 6250 | BOARD | `docs/board_results.md` steps 2, 3, 9 |
| B18 | `stored.out`: 15 s stored signal to LINE OUT, no underrun, no clips | BOARD | `results/phase4/board/stored.txt` |
| B19 | Inverse FFT gain self-check `g_ifft_gain` = 1.0 | BOARD | `docs/board_results.md` step 3/5 |
| B20 | `lab_arith` 256-term MAC: int16 316, int32 (64-bit acc) 522, float 326, double 1000 cycles; all = −1 782 181 120 | BOARD | `results/phase4/board/lab_arith.txt`, report §6.4 |
| B21 | `lab_conv`: x = 1 2 3 4, h = 1 1 1 → linear 1 3 6 9 7 4; circular N = 4: 8 7 6 9; circular N = 6 = linear | BOARD | `lab_conv.txt` |
| B22 | `lab_dft` N = 256: direct DFT 107 797 012 cycles, own radix-2 FFT 228 676, DSPLIB `fftSPxSP` 2145 (about 50 000× faster than the DFT); errors 3.8e-6 | BOARD | `results/phase4/board/lab_dft.txt` |
| B23 | `lab_bench`: DSPLIB FIR 838 vs plain C 1052 (−O3) vs 25 402 (−O0); biquad DSPLIB 486 vs C 803; `fftSPxSP` 2290, `ifftSPxSP` 2181, `cfftr2_dit` 4668, `cfftr4_dif` 4903; Mode A × 48 samples 22 634; Mode B block 8907; howl block 6726; notch × 48 2580 | BOARD | `lab_bench.txt`, report §6.4 |
| B24 | −O0 vs −O3: Mode A 3.0× slower, Mode B 3.6×, plain-C FIR 24× | BOARD | report §6.4 |
| B25 | Own FFT slow because it computes cos/sin in the loop; 228 720 cycles in `lab_bench` | BOARD | report §6.4 |
| B26 | Buttons: S2/S3 change the LEDs (user-confirmed), D4 follows mode; but each change once moved mode and preset together and one press skipped a preset; not resolved | BOARD (+ user) | `docs/board_results.md` step 4, C33 |
| B27 | Audible range: user heard stored tones at LINE OUT except 6 kHz, whose gain is +30.00 dB on the DSP; cause not determined; bypass test at −26 dBFS inaudible; −12 dBFS rerun aborted ("Target failed to write", connection drop) | BOARD (+ user) | `docs/board_results.md`, C34 |
| B28 | Audio path check: PC tone did not reach LINE IN (input −72.0 / −73.2 dBFS idle/playing); connection intermittent | BOARD | `docs/board_results.md` "Audio path check" |
| B29 | Live auto-notch run with no input: no notch placed (`notch_live.txt`) | BOARD | `results/phase4/board/notch_live.txt` |

## 7. Problems found and fixed

| # | What happened | Fix | Source |
|---|---|---|---|
| X1 | Goertzel meter N = 4800 read 375 Hz 9.3 dB low | N = 4608 | C10 |
| X2 | FIR lattice for G was impossible | used the Mode B FIR instead | C12 |
| X3 | HPF float32 state error too large | double-precision state | C14 |
| X4 | Library test driver used the wrong output ordering for `cfftr4_dif` (bit vs digit reversal; error 37 vs 4.8e-6) | digit reversal | C15 |
| X5 | C674x `icfftr2_dif` does not scale; round-trip gain 256 | documented; Mode B uses `ifftSPxSP` | C16 |
| X6 | Howl detector development: could not reach threshold; false trigger on second voice; spurious second notch; noise tracker stuck at zero | four fixes; one criterion relaxed 0.3 → 0.5 s | C25 |
| X7 | Clock estimate 302.77 MHz | measure over second second | C27 |
| X8 | McASP XDMAERR at start (double write) | remove CPU write | C28 |
| X9 | Audio never started after power cycle (book code cleared pending interrupt) | IEVAL write; 3 of 3 starts | C29 |
| X10 | Leftover EDMA from previous program wrote into new program's memory (18 million "cycles" reading) | `io_quiesce()`; all runs repeated | C30 |
| X11 | PC audio did not reach LINE IN; decision: no external input | built-in test signals | C31 |
| X12 | 6 kHz tone inaudible, connection drop | closed as limitation | C34 |

## 8. Figures worth showing (all exist)

| Figure | What it shows |
|---|---|
| `results/phase4/p4_board_gains.png` | Board-measured band gains vs design and target; error panel shows board − design ≈ 0 and Mode A design − target peak 1.53 dB at 750 Hz |
| `results/phase4/p4_board_vs_python.png` | DSP output minus Python, sample by sample |
| `results/phase4/p4_cpu_load.png` | Measured CPU load per mode, live and no-codec |
| `results/phase4/p4_o0_vs_o3.png` | −O0 / −O3 cycle ratios on the board |
| `results/phase1/p1_chain_tone_gains.png` | Tone gains of the full chain vs target (simulated) |
| `results/phase1/p1_chain_spectrograms.png` | Speech before/after processing (simulated) |
| `results/phase1/p1_multirate_levels.png` | Decimation without G aliases; with G the alias is ~−73 dB; same for interpolation with F |
| `results/phase1/p1_fir_G_methods.png` | Window comparison for G |
| `results/phase1/p1_fir_modeB_methods.png` | Frequency sampling vs window for Mode B FIR |
| `results/phase1/p1_fir_zeros.png` | Zeros of G |
| `results/phase1/p1_ola_vs_direct.png` | OLA equals direct convolution; time aliasing when N is too small |
| `results/phase1/p1_iir_hpf_methods.png` | HPF by bilinear vs matched-z vs impulse invariance |
| `results/phase1/p1_fft_opcounts.png` | FFT operation counts |
| `results/phase2/p2_iir_quantisation.png` | HPF structures with 16-bit coefficients |
| `results/phase2/p2_snr_float_vs_q15.png` | float32 vs Q15 SNR |
| `results/phase3/p3_auto_notch.png` | Speech + 2.7 kHz howl, before/after automatic notch (simulated) |
| `results/phase3/p3_nr_snr_gain.png` | NR SNR gain (simulated) |
| `results/phase3/p3_nr_spectrograms.png` | NR spectrograms (simulated) |
| `research/calc/fig_modeA_bands.png` | Five Mode A bands and their sum |

## 9. Planned but not done or not measured

- Latency on the board (T5): calculated only.
- Crossover spurs (T9) and limiter (T10) on the analogue path: simulation only.
- T1 noise floor, T7 own voices: not done.
- WDRC (compression): not built.
- Input channel (tip vs ring): not tested.
- Notch detection threshold between 0 and +10 dB: not measured.
- No-DSPLIB builds `live_ownfft` / `internal_ownfft`: built, not run on the board.
- ANSI 60 dB stopbands; Q15 board build; hardware circular addressing (AMR) and `DSPF_sp_fircirc`; overlap-save and 48 → 32 kHz on the board; digital image processing.
- Block-based Mode A with DSPLIB (~2 % estimated).
- Real-time listening: only board dumps converted to WAV and played on the laptop afterwards.
- S3-alone button retest.
- Primary sources for the noise-suppression and howl methods: not consulted, not cited.
- True mixed-radix FFT case (radix-4 + radix-2 stages) not exercised.

## 10. Disagreements between files

| Item | Values | Used in the document |
|---|---|---|
| Direct DFT cycles | 107 797 012 (`lab_dft.txt`, report) vs 107 796 990 (`board_results.md` step 8) | readout value, 107 797 012 |
| Number of notch runs | "three runs" (report §8.4) vs "two runs" (viva notes); readouts show 2500.48828 Hz; other values 2500.49, 2500.83 | "repeated runs, 2500.48–2500.83 Hz" |
| Mode A CPU estimate | "2.5–10.2 %" (report) vs "≤ 10.2 %" (board_results) | 2.5–10.2 % |
| Six-band delay | "about 16 ms" (viva) vs "≈ 16.9 ms" (REVIEW) | "about 16–17 ms" |
| Number of corrections | report §8.2 says 31; CHANGES.md now runs to C37 | "37 numbered entries (C1–C37)" |
| `fftSPxSP` cycles | 2145 (`lab_dft`) vs 2290 (`lab_bench`); TI test report 1965 | both board values, as a range |
| Float MAC cycles | 324 (old typo) vs 326 (readout) | 326 |

## 11. Everyday comparisons (not from the repository)

| # | Comparison | Tag |
|---|---|---|
| E1 | A blink takes about 100 ms | EVERYDAY (from the writing brief) |
| E2 | A film shows 24 still pictures per second | EVERYDAY (common knowledge) |
| E3 | Every 10 dB is ten times more sound power (definition of the decibel) | EVERYDAY (definition) |

## 12. Derived numbers (working shown)

| # | Number | Working |
|---|---|---|
| V1 | About 21 µs between samples | 1 / 48 000 s = 20.8 µs |
| V2 | 300 million clock cycles per second | 300 MHz |
| V3 | 8.81 ms is about one twelfth of a blink | 8.81 / 100 ≈ 0.09 |
| V4 | Live Mode A load check | 2617 / 25 000 = 10.5 % |
| V5 | Live Mode B load check | (829 + 7242 / 32) / 25 000 = 4.2 % |
| V6 | Own FFT about 100× slower than DSPLIB | 228 676 / 2145 ≈ 107 |
| V7 | 5 dB SNR ≈ speech carries about 3 times the power of the noise | 10^(5/10) = 3.16 |
| V8 | One Mode B chunk ≈ 2.7 ms | 128 / 48 000 s = 2.67 ms |
| V9 | A 16-bit number has 65 536 possible levels | 2^16 |
| V10 | 10 snapshots of I/O buffering = 0.21 ms | 10 / 48 000 s = 0.208 ms (L3) |
| V11 | Mode B chunking/FIR delay 320 samples = 6.67 ms | 320 / 48 000 s (L2, report §3.3) |
| V12 | Delay is less than a tenth of a blink | 8.81 ms / 100 ms = 0.088 |
| V13 | 0.01 dB is 300 times smaller than the 3 dB "just noticeable" step | 3 / 0.01 = 300 (B5, D24) |
