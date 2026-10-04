# Real-Time Digital Hearing Aid: Multirate Filter Bank and FFT Overlap-Add on the TMS320C6748

DSP Lab project, ECE, NIT Warangal. Board: TI LCDK C6748.

This README is a work in progress. The full guide to running every script and building the project arrives in Phase 5.

## Repository layout

| Folder | What it holds |
|---|---|
| `research/` | The frozen research pack: design, sources, calc scripts. Never edited; corrections go in `docs/CHANGES.md` |
| `python/` | The verified Python reference for every block, and the experiments (Phase 1–2) |
| `matlab/` | `.m` versions of the experiments. Unverified, because MATLAB is not installed here |
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

**MATLAB:** `matlab/p1_*.m` mirror these scripts. They are **unverified**, because MATLAB is not installed on the development PC. Run them from inside `matlab/`; figures go to `results/phase1_matlab/`.

**Test speech:** `data/speech_44k1.wav` was made with the Windows text-to-speech voice (Microsoft David, 44.1 kHz, 16-bit). `p1_multirate.py` converts it to `data/speech_48k.wav`. You can replace it with your own recording (test T7).

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
