# CHANGES – corrections and decisions made after the research pack

The research pack in `research/` is frozen. It is never edited. Corrections, clarifications and new decisions are recorded here instead. Each entry names the pack file it affects.

## Phase 0 (4 Oct 2026)

### Path map (files moved, contents unchanged)

| Old path (as cited inside the pack) | New path |
|---|---|
| `00_…08_*.md`, `CHANGES.md` | `research/00_…08_*.md`, `research/CHANGES.md` |
| `calc/*` | `research/calc/*` |
| `papers/*` | `research/papers/*` (git-ignored) |
| `research/audiogram.md`, `research/hardware_notes.md`, … | unchanged (already in `research/`) |

When a pack file says `calc/x.py`, read it as `research/calc/x.py`. The calc scripts use relative paths, so run them from inside `research/calc/`.

### Re-run of the pack's scripts

- `audiograms.py`, `design_check.py`, `gain_check.py`, `cpu_check.py`, `latency_check.py` and `review_check.py` were re-run on a copy (Python 3.12.10, NumPy, SciPy).
- Their outputs match the saved `*_output.txt` files exactly. The only difference is how the Windows console prints the `§` character (cp1252 encoding), which is cosmetic.
- `review_check.py`: **55/55 pass**.
- `figs.py` and `figs2.py` were re-run after installing matplotlib. Both figures were produced and look the same as the saved PNGs.

### Corrections and clarifications

| # | Pack file(s) | What the pack says | Correction / clarification |
|---|---|---|---|
| C1 | `08` timeline, `REVIEW` d#7 and d#9, `08` R13 | 12-week plan with a three-person team split; WDRC "after Week 8"; core frozen "by Week 9" | **Fixed decision: 2 weeks, one person.** The new schedule is in `README.md`. WDRC is built only after T2–T5 pass, and it is the first item dropped if time runs short. |
| C2 | `05` §9, `06` §3.3, `REVIEW` issue 31, `hardware_notes` §3.2 | HPF is plain C because `DSPF_sp_biquad` fails its pole rule | That pole rule (\|a1\| < 1 …) comes from the **C67x** manual (S15, p. 4-46). The **C674x** 3.4.0.0 header we actually link states no pole rule (`hardware_notes` §3.3). **The decision stands (plain C), but the main reason is different.** We filter one sample at a time, and a DSPLIB block call needs a block of samples (nx ≥ 2), so it cannot run per sample. The report states both reasons. |
| C3 | `05` §9, `07` T6, `08` R4 and others | CPU loads quoted at 456 MHz first | **Fixed decision: 300 MHz** (TI GEL, PLL untouched). The report leads with 300 MHz loads and with cycle counts, which do not depend on the clock. |
| C4 | `07` T6 | "Mode B 1.7–3.3 % (456 MHz) … 2.8–5.2 % at 300 MHz" | The 300 MHz range shown is the **C67x** library figure. With the C674x library, the correct range at 300 MHz is **2.6–5.0 %** (`research/calc/cpu_check_output.txt` lines 75–77: 2.56 % / 4.96 %). |
| C5 | `research/calc/cpu_check_output.txt` line 66 | "ifftSPxSP 1/N scaling: unresolved" | Stale. It was resolved in Update 6: the C674x `ifftSPxSP` scales by 1/N (`hardware_notes` §3.3). It will be confirmed on the board by the start-up self-check. |
| C6 | `REVIEW` §e item 2 | "TRM (S10) not supplied" | Stale. The TRM was read in Update 6 (§e item 1 of the same file says so). |
| C7 | `06` §3.4 vs `hardware_notes` §6 | Mode B memory 8.8 KB vs 6.8 KB | Not a real conflict: `06` counts H[k] (2 KB) inside Mode B, while `hardware_notes` counts it under coefficients. Total internal data is ≈ 15 KB either way. |
| C8 | `06` Stage 1, `REVIEW` §e item 7 | "Team runs the scripts in MATLAB" | **MATLAB is not installed** on this PC. Python (NumPy/SciPy) is the verified reference. The `.m` files in `matlab/` are written for submission but are **unverified** until someone runs them in MATLAB. |
| C9 | `05` §7, `hardware_notes` §1.4, `05` §9 | Mode B latency model (2L + 64), "+10 samples" FIFO model, 1–5 cycles/op | Still **estimates**. They stay labelled "estimated" in every document until T5/T6 measure them on the board. |

## Phase 1 (4 Oct 2026)

| # | Pack file(s) | What the pack says | Correction / clarification |
|---|---|---|---|
| C10 | `07` T2, `05` §1 (Goertzel tone meter) | Goertzel with N = 4800 | **Wrong for 375 Hz.** The bin index k = f·N/fs = 375 × 4800 / 48000 = 37.5 is not an integer, so the meter reads 375 Hz **9.3 dB low** (`python/p1_fft.py` showed −9.34 dB before the fix). For all 11 test tones to land on exact bins, N must be a multiple of 384 (375 Hz needs a multiple of 128; 250 Hz needs a multiple of 192). **New value: N = 4608** (96 ms, bins every 10.42 Hz). With it, every tone reads within 0.0001 dB. `goertzel()` now refuses a tone that is not on a bin. |
| C11 | `07` general set-up ("input −40 dBFS") | −40 dBFS input leaves room for the 30 dB gain | **True for tones, not quite for speech.** Our test speech at −40 dBFS RMS has peaks at −19.9 dBFS (crest factor about 20 dB). After up to 30 dB of gain, 0.04 % of the samples in Mode A (0.03 % in Mode B) reach the −1 dBFS limiter (`python/p1_chain.py`). This is the limiter working as intended (test T10), not an error. When the speech tests T7/T8 must be completely clip-free, use −45 dBFS RMS. |

### Phase 1 results that confirm the pack (no change needed)

All of these come from `python/run_all.py`:
- Every number in the `research/audiogram.md` §4 accuracy table matches to within 0.006 dB (1.53/0.38, 6.82/0.49, …).
- The Mode A delay is 375 samples.
- G and F reach 52.5 / 51.1 dB stopband attenuation.
- The HPF is −3.01 dB at 100 Hz.
- OLA and OLS match direct convolution to 1e-14.
- Crossover spurs are −65 dBc or lower.
- Noise coherence is above 0.9 from 100 Hz to 10 kHz.

**New result.** The window-method version of the 129-tap Mode B FIR (`firwin2` with a Kaiser window) misses the N3 target by up to 1.00 dB, compared with 0.38 dB for frequency sampling. This supports the pack's choice of frequency sampling.

## Phase 2 (4 Oct 2026)

| # | Pack file(s) | What the pack says | Correction / clarification |
|---|---|---|---|
| C12 | `03` Unit 5 (FIR lattice) | Use `tf2latc` on "a minimum-phase version of G" | **Not possible.** A lattice needs every zero strictly inside the unit circle. G has 16 stopband zeros **on** the circle, and converting it to minimum phase leaves them there. Each such zero forces a reflection coefficient \|K\| = 1, just as linear phase does (K₂₀ for linear-phase G, K₁₆ for minimum-phase G). **Used instead:** the minimum-phase version of the 129-tap Mode B FIR. Its zeros stay at least 0.058 from the circle, so all 128 reflection coefficients have \|K\| ≤ 0.48. The minimum-phase version is made with the real cepstrum, because finding the roots of a degree-128 polynomial lost 0.2 dB of accuracy (`python/p2_structures.py`). |
| C13 | `03` Unit 5, `06` §3.2 | "DF-II transposed is used in the final code (ASSUMPTION: better float behaviour)" | **Now measured, and confirmed.** HPF in float32, speech at −20 dBFS: DF-II-T gives 85.0 dB SNR (arithmetic noise −105.0 dBFS), DF-I 83.1 dB, DF-II 74.6 dB (−94.6 dBFS). Only DF-I and DF-II-T stay below the codec's own 16-bit noise floor of −101 dBFS (`python/p2_fixed_point.py`). |

### Board arithmetic and structure choice (Phase 2 evidence)

| Question | Evidence | Decision |
|---|---|---|
| float32 or Q15? | SNR vs float64, speech input: HPF 85.0 vs 12.1 dB; Mode A 138.7 vs 42.7 dB; Mode B 139.5 vs 20.2 dB (`p2_fixed_point.py`). The Q15 HPF fails because rounding noise passes through 1/A(z), whose gain is huge near DC with poles at r = 0.995. The Q15 Mode B loses 8 bits in the per-stage scaled FFT. A 16-bit path must also reserve 5 bits of headroom for the 30 dB gain: a −20 dBFS tone clips (+10 dBFS), while −40 dBFS is clean | **float32** (the C674x has hardware single-precision floating point). The pack's decision stands |
| HPF structure | 16-bit coefficients: the single 4th-order direct form puts a pole on z = 1 (unstable). The parallel form loses its DC zeros (−2.3 dB at 20 Hz instead of −55.9 dB). The lattice-ladder stays stable but its −3 dB point moves to 130 Hz. The cascade keeps −3 dB at 100.8 Hz with 0.16 dB passband error (`p2_structures.py`). In float32: DF-II-T has the least noise (C13) | **Cascade of 2 biquads, DF-II-T** |
| FIR structure (G, F) | Q15 direct form keeps the 52.5 dB stopband (52.49 dB). The cascade gives no benefit. The lattice is impossible (C12) | **Direct form**, symmetric taps, plain C (per sample, see C2) |
| Mode B coefficients | float32 FFT path: 139.5 dB SNR | H[k] stored as float32 complex |

Precision note: the "float32" Mode A figure rounds every stored result to float32 but accumulates in float64, so it is an upper bound. The exact float32 numbers come from the C build in Phase 3.

## Phase 3 (4 Oct 2026)

| # | Pack file(s) | What the pack says | Correction / clarification |
|---|---|---|---|
| C14 | `05` §5 (HPF), `06` §3.2 | HPF: 2 biquads, plain C, DF-II-T, float | **The state variables are now kept in double precision**; coefficients and samples stay float32. With poles at r = 0.995, the float32 state produced errors of up to 3.9e-5 of full scale (1.3 LSB of the 16-bit output). The band gains then amplified them up to 30 dB, so the full chain differed from Python by 2.8e-4 and failed the 1e-4 gate. With double-precision state: HPF 3.6e-6, chains ≤ 2.2e-5 (`c/build_pc.bat` → `results/phase3/pc_test_*.txt`). The C674x has hardware double precision. Its cost is **estimated** small (2 biquads per sample) and is measured on the board (`lab_bench`, HPF × 48 samples). The Goertzel test meter also accumulates in double (float32 error 1.9e-4 over 4608 samples, now 1.5e-9). |
| C15 | `06` §3.3, `07` T11 (`DSPF_sp_cfftr4_dif`) | "Output digit-reversed" | The pack is correct, but beware: the library's own test driver (`DSPF_sp_cfftr4_dif_d.c`) applies a radix-2 **bit** reversal afterwards. That driver only compares the assembly with the C reference, never with a true DFT. Checked on the PC with TI's reference code: after a base-4 **digit** reversal the output equals the FFT to 4.8e-6; after bit reversal it is wrong (error 37). `lab_modes.c` uses digit reversal. |
| C16 | `hardware_notes` §3 (`DSPF_sp_icfftr2_dif`) | "The C reference code multiplies by inv (1/n scaling; confirm on board)" | That describes the C67x v2.00 reference. The **C674x** reference `icfftr2_dif` does **not** scale: the `cfftr2_dit → icfftr2_dif` round trip has gain 256 = N (`results/phase3/lab_check.txt`). The Mode B path is not affected; it uses `ifftSPxSP`, which does scale by 1/N. |
| C17 | S19 book code (not in the pack) | — | The book's two examples disagree on which 16-bit half of the McASP word holds the left channel (talk-through ISR: low half = left; EDMA example: low half = right). From the DSP-mode framing (left word first, MSB first), the low half is the codec's right channel, which on the LCDK is the jack's **tip**. Processing the tip keeps a mono plug working. Board checklist step 4 verifies this; `INPUT_SEL` in `config.h` switches it. |
| C18 | `06` §3.3 (`DSPF_sp_bitrev_cplx`) | "cfftr2_dit + bitrev_cplx 4138 + 666 cycles" | `DSPF_sp_bitrev_cplx` needs an index table whose generator exists only in TI's test driver. To avoid copying TI code into a public repository, the benchmark times our plain-C bit reversal instead. The 666-cycle figure stays "estimated (S15 formula)". |
| C19 | `06` §3.4, `REVIEW` "code < 64 KB (ASSUMPTION)" | Code size unknown | **Measured** from the linker map of `live.out`: `.text` 22.1 KB, total L2 use 68.6 KB of 255 KB (16 KB of it stack). |
| C20 | `06` §3.1 (S19 `link6748e.cmd`, `vectors_EDMA.asm`) | Use the book's linker and vector files | Replaced by our own `hearing_aid.cmd` and `vectors.asm` (public repository; also a 16 KB stack instead of the book's 1 KB). Only the book's support file and headers are used, fetched by `tools/fetch_board_files.py`. |

### Phase 3 verification summary

- **C vs Python** (`c/build_pc.bat`), each check run twice, once with our own radix-2 FFT and once with TI's DSPLIB natural-C FFT as the `fft256` backend:

| Block | Max error vs Python | Tolerance |
|---|---|---|
| HPF | 3.6e-6 | 1e-5 |
| FFT | 1.6e-7 (relative) | 1e-5 |
| Goertzel | 1.5e-9 | 1e-5 |
| Mode A | 3.4e-6 | 1e-4 × peak |
| Mode B | 2.8e-6 | 1e-4 × peak |
| Full chains (4 presets × 2 modes) | ≤ 2.2e-5 | 1e-4 |

  No Mode B overruns. The Mode B buffering delay is exactly 256 samples, as designed.
- **Lab experiments:** checked on the PC with TI's reference code (`results/phase3/lab_check.txt`).
- **Board build:** 12 configurations build with `cl6x` 8.1.3 + `dsplib.ae674` with 0 warnings (`ccs/hearing_aid/build.bat`). The CCS project imports and builds headless (`eclipsec` importProject/buildProject) with 0 errors.
- **Not yet verified, needs the board:** everything in `docs/board_checklist.md` (McASP FIFO/EDMA behaviour, all cycle counts, latency, the input channel assignment, LEDs).

## Before the board (5 Oct 2026)

| # | Pack file(s) | What the pack says | Correction / clarification |
|---|---|---|---|
| C21 | `07` T9 | "Level of components other than the tone ≤ −60 dBc" | For **recordings**, the gate is now the **largest single spur**. The total residual is still reported, for information. At −40 dBFS through a 16-bit path, the quantisation noise floor alone gives a total residual of about −46 to −58 dBc after the band gains, whatever the filter bank does. Without dither, 16-bit quantisation of a periodic tone also produces harmonics: −61 dBc at 2.1 kHz for a 700 Hz tone was found in the self-test. The test files in `data/board/` are therefore generated with TPDF dither. With both changes, the self-test recovers the design's real spurs, e.g. −68 dBc at 5.3 kHz (= 6 kHz − 700 Hz) for the 700 Hz tone; Phase 1 found −69 dBc. |
| C22 | `07` T2/T3 | Measure gain against the input | A **bypass-preset recording** of the same tone file is now made first and used as the reference. It removes the codec and sound-card gain, which are unknown to us, from the band-gain result (`python/board_compare.py`). |

## Scope additions from the project brief (5 Oct 2026, approved)

The brief lists two items that were not in the approved design: a **feedback/notch IIR filter by the bilinear transform** and **noise suppression**. Both are now built. Each is switchable and **off by default**, so the verified core is unchanged when they are off. Every parameter is a DESIGN CHOICE.

| # | Item | Design | Verification |
|---|---|---|---|
| C23 | **Feedback notch + automatic howl detection** | **Notch:** 2nd-order IIR, bilinear transform of H(s) = (s² + ω0²)/(s² + (ω0/Q)s + ω0²), pre-warped at f0, Q = 10. Zeros sit exactly on the unit circle, so there is a true null at f0.<br>**Detector:** a Hann-windowed FFT-256 of each 128-sample block, searched from 500 Hz to 8 kHz. A block counts as a hit when its peak is a local maximum at least 25 dB above the mean of the range (main lobe ±5 bins excluded) and stays in the same bin ±1. A leaky counter (+1 per hit, −1 per miss, reset when the bin jumps) triggers at 75. At most 2 notches. The detector watches the notch output.<br>**Timing:** block j is decided in the background during block j+1, and the notch is active from the start of block j+2. | `python/p3_notch_nr.py`:<br>• depth ≥ 100 dB (270 dB) and bandwidth 264 Hz vs f0/Q = 270 (2.1 %)<br>• **no false notch on either speech voice**<br>• 2.7 kHz howl notched after 0.20 s, 49 dB down<br>• 1.9 kHz howl on the second voice notched after 0.41 s<br>C activates at exactly the same sample (50 816) and frequency (2495.30 Hz) as Python (`c/pc_test.c`). |
| C24 | **Noise suppression** | **Gain** per band (Mode A) or per frequency sample (Mode B): G = √max(1 − 2·N/P, Gmin²), Gmin = −12 dB, smoothed with τ = 20 ms. P is the power smoothed with τ = 10 ms.<br>**Noise floor N:** minimum statistics, simplified (the minimum of P over 4 × 0.375 s), times a bias factor measured on white noise (`nr_bias()`: Mode A 1.19–2.31 per band, Mode B 2.23).<br>**Mode B:** the 129-tap FIR is redesigned by frequency sampling every block from (target × G), so each block is still an exact linear convolution (L + M − 1 = 256). | Shadow filtering on two speech recordings with white/pink noise at 0/5/10 dB SNR:<br>• Mode A: +5.9 to +8.5 dB SNR, speech −1.5 to −4.1 dB<br>• Mode B: +6.5 to +9.4 dB, speech −0.9 to −2.5 dB<br>• noise-only stretches −12 dB<br>• with all gains forced to 1, the core is reproduced exactly (0 / 6e-15)<br>C vs Python: ≤ 1.9e-5 (`c/pc_test.c`). |
| C25 | Process notes on the above | Four issues were found and fixed **during** development; all are documented in the scripts. | • The first detector version could not reach its own threshold (Hann main-lobe leakage).<br>• A second voice, never used for tuning, exposed a false trigger at the low edge of the search range (fixed by requiring a local maximum).<br>• A counter shared across frequencies caused a spurious second notch.<br>• The first noise tracker never left zero after the alignment delay; it was replaced by minimum statistics.<br>• **One pre-declared criterion was relaxed:** howl detection time, 0.3 s → 0.5 s (measured 0.20 and 0.41 s). The leaky counter trades speed for robustness against speech masking; shortening the hold just to pass was rejected. |

**Sources.** None of the papers in `research/` describes a noise-suppression or howl-detection algorithm. Yang et al. (S3) and Sokolova et al. (S1, S2) only place noise reduction and adaptive feedback cancellation after the filter bank. The methods used here are standard textbook methods (power spectral subtraction / Wiener-type gain, minimum-statistics noise estimation, notch-filter howling suppression), implemented and verified in this repository. Their original papers have **not** been read or cited yet. They must be found and checked before the report cites them.

**"No external input" preparations.**
- `stored_speech` build: 2 s of speech compiled into the program (`ccs/hearing_aid/speech_clip.c`), with optional on-board white noise via `g_stored_snr_db`.
- `internal_speech` build: the same clip in `IO_INTERNAL`.
- `live_ownfft` and `internal_ownfft` builds: no TI DSPLIB at all; Mode B uses our own radix-2 FFT.

### Additions (no conflict with the pack)

- My own radix-2 **DIF** FFT, written from scratch. The pack has only an own DIT FFT; the DIF appears there only as the DSPLIB `icfftr2_dif`.
- Operation-count tables for radix-2, radix-4 and split-radix FFTs.
- Small lab-experiment modes in the CCS project: arithmetic, linear/circular convolution, DFT vs FFT, and DSPLIB FIR/FFT benchmarks.

### Tools and repository

- **Public repository.** The book's board-support code (rt-dsp.com) and TI files have no clear licence for redistribution. They are therefore **not committed**. `tools/fetch_board_files.py` downloads them into `third_party/` (git-ignored). `research/papers/` stays git-ignored.
- **PC C compiler:** WinLibs GCC 16.2.0 (mingw-w64 UCRT) was installed with winget. It is used to test the portable C against Python. CCS 7 has no C674x simulator.
- **matplotlib** was installed with pip.
