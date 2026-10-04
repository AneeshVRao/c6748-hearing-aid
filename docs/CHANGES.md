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

### Additions (no conflict with the pack)

- My own radix-2 **DIF** FFT, written from scratch. The pack has only an own DIT FFT; the DIF appears there only as the DSPLIB `icfftr2_dif`.
- Operation-count tables for radix-2, radix-4 and split-radix FFTs.
- Small lab-experiment modes in the CCS project: arithmetic, linear/circular convolution, DFT vs FFT, and DSPLIB FIR/FFT benchmarks.

### Tools and repository

- **Public repository.** The book's board-support code (rt-dsp.com) and TI files have no clear licence for redistribution. They are therefore **not committed**. `tools/fetch_board_files.py` downloads them into `third_party/` (git-ignored). `research/papers/` stays git-ignored.
- **PC C compiler:** WinLibs GCC 16.2.0 (mingw-w64 UCRT) was installed with winget. It is used to test the portable C against Python. CCS 7 has no C674x simulator.
- **matplotlib** was installed with pip.
