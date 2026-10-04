# 07 – Testing Plan (Step 8)

**General setup (DESIGN CHOICE).**

- A PC sound card or audio interface plays test signals into LCDK LINE IN [S11] and records LINE OUT on one channel.
- For latency tests, the same signal also goes straight to the second recording channel as a reference.
- Input level is −40 dBFS (because of the up-to-30 dB gain) unless stated.
- All analysis is done in MATLAB. Every test is run for Mode A and Mode B unless stated.

## Tests

| ID | Test | Signal | How to measure | Pass / expected (from `05`) |
|---|---|---|---|---|
| T1 | Loopback / noise floor | Silence, then 1 kHz tone | Record output; FFT | No clicks; note the noise floor (codec SNR spec: ADC 92 dBA, DAC 102 dBA [S13]) |
| T2 | Band gains at audiometric frequencies | 11 tones: 250, 375, 500, 750, 1 k, 1.5 k, 2 k, 3 k, 4 k, 6 k, 8 kHz, 1 s each | (a) On-board Goertzel meter (N = 4800) on input and output; (b) MATLAB on the recording | Within ±1 dB of the simulated gains in `05` §6. Run all six gain cases (Bisgaard N2, N3, S2 × half-gain and ×0.4) from `research/audiogram.md` §4. ≤ 3 dB from target (just-noticeable-difference threshold used in [S2]) is expected for N2/N3. For Bisgaard S2, Mode A is expected to miss by up to 6.8 dB at 1.5 kHz, so compare against Mode B |
| T3 | Frequency response | Log sine sweep 50 Hz–20 kHz, 10 s | Divide output spectrum by input spectrum (or use MATLAB `tfestimate`) | Matches `calc/fig_modeA_bands.png` composite |
| T4 | Response with noise | White and pink noise, 30 s | `tfestimate` / `mscohere` (Welch averaging) | Same as T3; coherence > 0.9 in 100 Hz–10 kHz (pass threshold: DESIGN CHOICE) |
| T5 | **Latency** | Single click (1-sample impulse) or 10 ms tone burst, repeated 10× | Cross-correlate the output channel with the reference channel; subtract the PC loopback delay (cable direct out → in) | Default (Read FIFO on, Write FIFO off): **Mode A ≈ 8.81 ms, Mode B ≈ 7.67 ms**. Optionally repeat with the FIFO off (8.60 / 7.46 ms). This also measures the FIFO cost (`calc/latency_check.py`). Report mean ± std |
| T6 | **CPU load** | Speech | Cycles per frame (TSCL/timer) and GPIO duty cycle; build at `-o0` and `-o3` | Estimates at 456 MHz: Mode A 1.7–6.7 %, Mode B 1.7–3.3 % with the C674x DSPLIB (2.5–10.2 % / 2.8–5.2 % at 300 MHz; `calc/cpu_check_output.txt`). Measure the real clock first (06 board step 0; expect 300 MHz). TSCL counter [S9 §2.9.14]; GPIO duty cycle on LED D6 [S11 Table 8] |
| T7 | Speech quality | Own recorded sentences (both team voices), resampled to 48 kHz if needed (rational I/D, 03) | Spectrograms before/after; informal listening by 3 people | Clear speech, high-frequency boost visible |
| T8 | Speech in noise | Speech + pink noise at 0, 5, 10 dB SNR | Spectrograms; output SNR per band | Documents that linear gain does not improve SNR (motivates the noise-reduction extra) |
| T9 | Aliasing / crossover spurs | Tones at 700, 760, 1450, 1550, 2950, 3050, 5900, 6100 Hz | FFT of output; level of components other than the tone | Spurs ≤ −60 dBc (pass threshold: DESIGN CHOICE; simulated −67 to −85 dBc, `calc/design_check_output.txt`) |
| T10 | Overload / limiter | Tone stepping −40 → 0 dBFS | Clip counter, waveform | No wrap-around; limiter caps output |
| T11 | FFT and FIR benchmark | Random 256-point frame; 48-sample block for FIR/biquad | Cycles (TSCL) for own radix-2, `cfftr2_dit` + bitrev, `cfftr2_dit` → `icfftr2_dif` (no bit reversal), `cfftr4_dif`, `fftSPxSP`; `DSPF_sp_fir_gen` (nh 24 = G padded with zeros, nr 48) vs our plain-C G; `DSPF_sp_biquad` (nx 48, test coefficients with \|a1\| < 1, see S15 p. 4-46) vs our plain-C biquad; **ifftSPxSP scale check** (ifft of a known spectrum: gain 1 or N) | Compare with the C674x DSPLIB TestReport: fftSPxSP 1965, ifftSPxSP 1985 (N = 256); fir_gen (nh 24, nr 48) 775; biquad (nx 48) 456 (`calc/cpu_check.py` Update 6). For cfftr2/cfftr4/icfftr2 use the C674x headers (S15 C67x formulas: 4138+666 / 8271 / 3696 for reference). S16's 2× cache effect was measured on a C6713, so it is only a guide |
| T12 | Fixed vs float | Speech | MATLAB Q15 vs float SNR; optional board Q15 | SNR table |
| T13 | OLA vs OLS (MATLAB) | Speech | max \|y_OLA − y_OLS\| and op count | Identical to float precision |
| T14 | IIR structure comparison | Tone and impulse | DF-I vs DF-II vs DF-II-T outputs, states used | Same output; DF-II uses half the memory |
| T15 (optional) | WDRC attack/release | Step 55 → 90 dB-equivalent (−60 → −25 dBFS) tone at 2 kHz, the same step size as the ANSI test cited in S2 | Envelope of output; time to settle within 3 dB (attack) and 4 dB (release), definitions from S2 | Close to 10 ms / 20 ms targets |
| T16 | **Fallback I/O modes** | Stored tone + speech vectors (Stage 1.9) | `IO_STORED_LINEOUT`: listen/scope on LINE OUT, XSTAT clean. `IO_INTERNAL`: CCS graph of input/output, save output, compare with MATLAB; log worst TSCL cycles per 4-sample block | Output = MATLAB within 1e-4; worst block < 25 000 cycles at 300 MHz (DESIGN CHOICE thresholds) |

## Graphs for the report

1. Block diagram (from `05` Mermaid, redrawn).
2. G and F magnitude responses and the G zero plot (`calc/fig_prototype_filters.png`, then the MATLAB version).
3. Individual band responses and the composite gain against the target audiogram curve (simulation and measured on one plot).
4. Measured gain at 11 audiometric frequencies: bar chart of target, Mode A and Mode B.
5. Frequency response from the sweep/noise: Mode A against Mode B.
6. Latency: impulse in/out time plot with the delay marked; bar chart of calculated vs measured.
7. CPU cycles table and bar chart (Mode A, Mode B, `-o0` vs `-o3`).
8. FFT benchmark bar chart (radix-2, radix-4, mixed, own code).
9. Spectrograms of speech: input, Mode A, Mode B.
10. Fixed vs float: coefficient-quantised responses and an SNR table.
11. Chirp-Z zoom of a crossover region.
12. HPF: bilinear vs matched-z vs impulse-invariance responses.
13. OLA diagram with our block sizes (L = 128, M = 129, N = 256).
14. Optional: WDRC input/output curve and attack/release plot.

## Data to log for every measurement

Date, mode, build (`-o0`/`-o3`), fs, input level, CPU clock read from PLL, file name of recording. Keep the logs in a `results/` folder next to this pack.
