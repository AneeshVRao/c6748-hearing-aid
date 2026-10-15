# Viva notes: likely questions with short answers

Numbers are from `docs/report.md`. "Calc." means calculated, not yet measured.

## The project in 30 seconds

A real-time hearing aid on the TI C6748 LCDK at 48 kHz. Mode A is a 5-band multirate filter bank; Mode B is FFT-256 overlap-add with a 129-tap FIR. Gains follow the half-gain rule on the Bisgaard N3 audiogram, capped at 30 dB. On the board, the DSP's output matches the Python design within 2e-5, and its band gains match within 0.01 dB. Live CPU load is 10.5 % (A) and 4.2 % (B) at 300 MHz.

## Design choices

**Why 48 kHz?**
The octave crossovers fs/8, fs/16, fs/32, fs/64 land exactly on 6 k, 3 k, 1.5 k and 750 Hz, and the codec and book code support 48 kHz directly.

**Why only 5 bands?**
Latency. A linear-phase bank's delay doubles with every extra level. A 6th band would push the delay to about 16 ms, over the 10 ms target.

**Why is the delay 375 samples?**
At each level the delay is T_k = 10 (G) + 15 (F) + 2·T_{k+1}. So T_0 = 25·(2⁴ − 1) = 375 samples = 7.81 ms. The slowest part is the lowest level, because resolving low frequencies takes time.

**Why multirate?**
After each split the low band needs only half the rate, so the same 21-tap filter does the work of a 4× longer one. That gives 61 operations per sample against 313 single-rate (5.1×, calc.).

**Why doesn't decimation alias?**
G is 52 dB down from 0.20 fs_k. After ↓2, everything above 0.30 fs_k folds below 0.20 fs_k and is already suppressed. Measured alias rejection is −73 dB.

**Why is F a half-band filter?**
Every second coefficient is zero (17 of 31 non-zero) and the centre tap is 0.5, so interpolation by 2 costs about half the multiplies. Half-band filters need N = 4m − 1, and 31 fits.

**Why a Kaiser window?**
Its β parameter trades main-lobe width against side-lobe level. For 21 taps it gives 52.5 dB, against 38.6 (Hamming) and 24.2 (rectangular).

**Why frequency sampling for Mode B?**
We specify the gain directly at 65 frequencies. It follows the target within 0.38 dB, against 1.00 dB for a windowed design of the same length.

**Why N = 256 for overlap-add?**
Linear convolution of a 128-sample block with a 129-tap filter is 128 + 129 − 1 = 256 long. Any shorter FFT wraps the tail around (time aliasing); we showed errors growing from 0.29 to 18.9 as N drops.

**Overlap-add vs overlap-save?**
They cost the same. OLA zero-pads the input and adds the output tails; OLS overlaps the inputs and discards the first M − 1 outputs. Both match direct convolution within 1e-14.

**Why the bilinear transform for the HPF?**
It maps the whole jω axis onto the unit circle, so there is no aliasing and a stable analogue filter stays stable. Its frequency warping is removed by pre-warping the cut-off. Impulse invariance cannot be used for a high-pass: the response contains a delta and aliases.

**Why a cascade of biquads?**
With 16-bit coefficients, the single 4th-order direct form puts a pole on z = 1 and becomes unstable. Second-order sections keep the poles accurate. DF-II-T had the least float32 noise.

**Why float and not Q15?**
Measured SNR: HPF 85 vs 12 dB, Mode B 139 vs 20 dB. The C674x has hardware floating point, and a float MAC costs the same as an int16 MAC (326 vs 316 cycles per 256 terms).

**Why double precision for the HPF state?**
The poles sit at r = 0.995, so rounding noise is amplified enormously near DC. With float32 state the error reached 1.3 LSB, and the 30 dB band gains pushed the chain past its 1e-4 gate.

## Results

**How do you know the DSP computes correctly?**
In `IO_INTERNAL` mode the board processes a stored signal with no codec. We dump the output and compare it sample by sample with Python: max error 6e-6 (A), 6e-6 (B), 2e-5 with noise suppression.

**Gain accuracy?**
Mode A is within 1.53 dB of the target (largest at the 750 Hz crossover); Mode B is within 0.38 dB. That is the design accuracy. The board reproduces the simulated gains to 0.01 dB.

**Latency?**
Calc. 8.81 ms (A) and 7.67 ms (B), both under 10 ms. Breakdown: bank 375 samples + FIFO/block ≈ 10 samples + codec 38 samples. By decision (C31) no external audio input is used, so latency is reported from the calculation, not measured on the board.

**CPU load?**
Measured live: 10.5 % (A) and 4.2 % (B) at 300 MHz. Mode B is cheaper because two library FFTs per 128 samples cost less than four levels of per-sample C filtering.

**Which mode is better?**
Mode B: more accurate, handles steep losses (0.49 dB vs 6.82 dB on Bisgaard S2), cheaper and lower delay. Mode A works per sample (no block buffering) and suits per-band compression.

**Why does Mode A fail on steep losses?**
Five octave bands can only change gain in octave steps, and the crossover regions blend neighbours. A 15.7 dB jump between B2 and B3 cannot be followed.

## DSP processor questions

**C674x architecture?**
VLIW: 8 functional units (.L .S .M .D × 2), up to 8 instructions per cycle, 64 registers, fixed and floating point in hardware. L1P/L1D caches, 256 KB L2, DDR2.

**Harvard architecture?**
Separate program and data paths, so an instruction fetch and a data access happen in the same cycle. On the C674x this means separate L1P and L1D caches.

**Pipelining?**
The compiler software-pipelines loops so successive iterations overlap. `-O3` vs `-O0`: 24× on a FIR loop, 3–3.6× on whole modes (measured).

**Why use DSPLIB?**
Hand-optimised assembly: FFT-256 in 2145 cycles, against 228 676 for our textbook C FFT. Ours computes cos/sin inside the loop; a twiddle table would fix most of that.

**Circular addressing?**
Mode A uses power-of-two buffers with index masking in C. The C674x also has hardware circular addressing (the AMR register), but the C compiler does not use it, so we only explain it.

**How does audio get in and out?**
The codec sends 16-bit samples over McASP0. The Read FIFO collects 4 words, the EDMA moves them to RAM, and one interrupt fires per 4-sample block (83.3 µs). The output goes the same way back. The codec is set up over I2C.

**Why the Read FIFO on and the Write FIFO off?**
The Write FIFO stays full, adding 64 samples (1.33 ms) of latency, which pushes Mode A over 10 ms. The Read FIFO adds only up to 4 samples.

**What went wrong on the board?**
Four bugs:
- the clock estimate was skewed by start-up overruns (C27);
- a double write to the McASP (C28);
- an interrupt race: the book's code cleared a pending EDMA interrupt, so audio never started after a power cycle (C29). Fixed with an IEVAL write. It only appeared after a power cycle.
- a leftover EDMA from the previously loaded program wrote into the new program's memory (C30). Fixed by stopping EDMA and McASP at start-up.

## Extras

**How does the feedback notch work?**
A bilinear-transformed 2nd-order notch, Q = 10, designed on the DSP at run time. The howl detector looks for a steady spectral peak 25 dB above average; after at least 75 blocks (0.2 s; measured 0.20 and 0.41 s) it places a notch there. On the board: no false notch on 12 s of speech, and a 2500 Hz tone was notched within 0.5 s (at 2500.5–2500.8 Hz over two runs).

**How does the noise suppression work?**
It estimates each band's noise floor (minimum of the smoothed power over 1.5 s) and turns the band down where the signal is mostly noise (Wiener-type gain, floor −12 dB). On the PC this gave +6 to +9 dB SNR on test speech; on the board, built-in speech with 5 dB SNR noise improved by 8.4 dB (A) and 8.8 dB (B).

## Honest gaps

- By decision (C31) no external audio input is used. The board is verified with built-in signals, so codec-path latency (T5), spurs (T9) and the limiter (T10) are simulation-only. The digital processing on the DSP is verified: output matches Python within 2e-5, gains within 0.01 dB.
- WDRC (compression) was not built.
- The papers we read give no algorithm for noise suppression or howl detection. We used standard methods whose original sources still have to be checked.
- Filter stopbands are 52 dB, not ANSI class 2's 60 dB: a deliberate trade for latency (60 dB would cost 10.79 ms).
