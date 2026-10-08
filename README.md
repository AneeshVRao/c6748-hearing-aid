# Real-Time Digital Hearing Aid: Multirate Filter Bank and FFT Overlap-Add on the TMS320C6748

DSP Lab project, ECE, NIT Warangal. Board: TI LCDK C6748.

This README is a work in progress. The full guide to running every script and building the project arrives in Phase 5.

## Repository layout

| Folder | What it holds |
|---|---|
| `research/` | The frozen research pack: design, sources, calc scripts. Never edited; corrections go in `docs/CHANGES.md` |
| `python/` | The verified Python reference for every block, and the experiments (Phase 1–2) |
| `matlab/` | `.m` versions of the experiments, verified in MATLAB on 8 Oct 2026 (`docs/CHANGES.md` C26) |
| `c/` | Portable C for each block, plus a PC test harness (GCC) |
| `ccs/` | The CCS 7 project for the LCDK (CGT 8.1.3, C674x DSPLIB 3.4.0.0) |
| `tools/` | Helper scripts, e.g. a script that fetches the third-party board files |
| `results/` | Plots and logs created by the scripts |
| `docs/` | Changes log, board checklist, report, viva notes, slides outline |

## Running the Python reference (Phase 1)

```bash
pip install -r requirements.txt
```

```bash
python python/run_all.py
```

`run_all.py` runs the self-check in `dsp_ref.py` and each experiment. Every script checks its own results with `assert` and writes its plots to `results/phase1/`.

| Script | Block |
|---|---|
| `python/dsp_ref.py` | Shared reference for all blocks (filters, gain presets, Mode A vectorised and per-sample streaming, OLA/OLS, own FFTs, Goertzel). Self-check: streaming = vectorised, OLA = direct, own FFT = numpy |
| `python/p1_fir.py` | 1. FIR by Kaiser window vs frequency sampling; zero plots |
| `python/p1_iir.py` | 2. HPF by bilinear vs matched-z; impulse invariance (low-pass only) |
| `python/p1_multirate.py` | 3. Decimation and interpolation per level; 44.1 → 48 kHz with I/D = 160/147 |
| `python/p1_ola.py` | 4. Overlap-add and overlap-save vs direct convolution; time aliasing when N is too small |
| `python/p1_fft.py` | 5. Own radix-2 DIT/DIF FFTs; radix-2/4/split-radix operation counts; Goertzel; Chirp-Z zoom |
| `python/p1_chain.py` | 6. Gain presets, full Mode A/B chains: tones, noise, speech, speech + noise |
| `python/p2_structures.py` | Phase 2: FIR direct / cascade / lattice / frequency-sampling structure; IIR DF-I / DF-II / DF-II-T / cascade / parallel / lattice-ladder; 16-bit coefficient quantisation (plots in `results/phase2/`) |
| `python/p2_fixed_point.py` | Phase 2: float32 vs Q15 data path (HPF forms, Mode A, Mode B), overflow and headroom |
| `python/p3_notch_nr.py` | Extras from the brief: bilinear feedback notch with automatic howl detection; noise suppression in both modes (SNR gain by shadow filtering). Takes about 5 minutes |
| `python/board_compare.py` | Phase 4 analysis of board dumps and recordings (`selftest` checks it on fabricated recordings) |

**MATLAB:** `matlab/p1_*.m` and `p2_*.m` mirror these scripts. They were run in MATLAB (Signal Processing Toolbox) on 8 Oct 2026 and match Python (log in `results/phase1_matlab/run_log.txt`; differences in `docs/CHANGES.md` C26). Run them from inside `matlab/`; figures go to `results/phase1_matlab/`.

**Test speech:** `data/speech_44k1.wav` was made with the Windows text-to-speech voice (Microsoft David, 44.1 kHz, 16-bit). `p1_multirate.py` converts it to `data/speech_48k.wav`. You can replace it with your own recording (test T7).

## Portable C and PC tests (Phase 3)

Needs GCC (WinLibs mingw-w64; `winget install BrechtSanders.WinLibs.POSIX.UCRT`) and the C674x DSPLIB at `C:\ti\dsplib_c674x_3_4_0_0`. The DSPLIB is needed because the test also compiles TI's natural-C reference FFTs.

```bash
c\build_pc.bat
```

The script does four things:
1. Runs `python/export.py`, which writes the coefficients (`c/coeffs.c/.h`) and the test vectors.
2. Builds the C code twice: once with our own FFT, once with the DSPLIB reference FFT.
3. Builds the lab-experiment check.
4. Runs all three. Results go to `results/phase3/`.

Tolerances: single blocks 1e-5 of full scale; modes and full chains 1e-4. Measured errors are in `docs/CHANGES.md` (Phase 3).

| File | Block |
|---|---|
| `c/ha.h`, `c/ha.c` | Complete hearing aid: HPF → Mode A or B → limiter; Mode B double buffering |
| `c/hpf.c` | 100 Hz HPF, 2 biquads DF-II-T (double-precision state) |
| `c/modeA_bank.c` | 5-band multirate filter bank, per sample, power-of-2 circular buffers |
| `c/modeB_ola.c` | FFT-256 overlap-add |
| `c/fft_own.c` | Own radix-2 DIT/DIF FFTs |
| `c/fft_dsplib.c` | `fft256()` on DSPLIB `fftSPxSP`/`ifftSPxSP` (board; TI reference code on the PC) |
| `c/goertzel.c` | Tone meter |
| `c/extras.c` | Feedback notch (bilinear, designed at run time), howl detector, noise-floor tracker and noise-suppression gain (off by default) |
| `c/pc_test.c`, `c/lab_check.c` | PC tests |

## Board build (CCS project)

```bash
python tools/fetch_board_files.py
```

```bash
ccs\hearing_aid\build.bat
```

`build.bat` builds all 16 board programs with `cl6x` 8.1.3 into `ccs\build\<name>\<name>.out`:
- all but two link TI's `dsplib.ae674`;
- `live_ownfft` and `internal_ownfft` use no library at all;
- `stored_speech` and `internal_speech` play a built-in speech clip, so they need no external input.

On the board, DIP switches SW1-5 and SW1-6 turn on noise suppression and the automatic feedback notch. To work in the CCS IDE instead, use **Project → Import CCS Projects** and select `ccs/hearing_aid`. Compile-time switches (I/O mode, FIFO on/off, lab experiment, input channel) are in `ccs/hearing_aid/config.h`.

Board procedure, step by step, with what to read back: [docs/board_checklist.md](docs/board_checklist.md). Smoke test first: [docs/board_smoke_test.md](docs/board_smoke_test.md).

## Progress (8 Oct 2026)

| Item | Status |
|---|---|
| Phase 0–3: audit, Python reference, structures/fixed point, portable C, CCS project | Done |
| Extras: feedback notch + howl detector, noise suppression, no-input builds | Done (PC verified) |
| MATLAB `.m` files | Done, verified in MATLAB (C26) |
| Board: smoke test (clock 300 MHz, stock loopback), DIP 5/6 off | Done ([docs/board_results.md](docs/board_results.md)) |
| Board: checklist steps 2–10 | Next: `loop_fallback.out` |
| Phase 4: board vs simulation | Waiting for board data |
| Phase 5: report, viva notes, slides | Not started |
| WDRC (optional) | Only after T2–T5 pass |

## Schedule (2 weeks, one person)

| Day | Engineering work | Board work (on the LCDK) |
|---|---|---|
| 1 | Phase 0 audit; Phase 1 blocks 1–3 | — |
| 2 | Phase 1 blocks 4–6; `.m` files | — |
| 3 | Phase 2: filter structures and fixed point | Smoke test: CCS connects, read the clock, stock loopback |
| 4–5 | Phase 3: portable C, PC tests, CCS project, command-line build, board checklist | — |
| 6–8 | Fix whatever the board results show | Board checklist: loopback → FIFO → LEDs → ifft check → Mode A → Mode B → tests T2–T6 and T11 |
| 9 | Phase 4: board vs simulation analysis | Re-runs if needed |
| 10 | Phase 5: documentation | Demo rehearsal |

WDRC (wide dynamic range compression) is optional. It is built only after tests T2–T5 pass, and it is the first thing dropped if time runs short.

## Third-party board files

The board-support code comes from the Welch, Wright & Morrow book (rt-dsp.com) and TI. It is not in this repository because its licence for redistribution is unclear. `tools/fetch_board_files.py` (added in Phase 3) downloads it into `third_party/`, which git ignores.
