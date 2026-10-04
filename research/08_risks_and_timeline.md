# 08 – Risks and Timeline (Steps 9 and 10)

## Risks and fallbacks

| # | Risk | Likelihood | Effect | Early warning | Fallback |
|---|---|---|---|---|---|
| R1 | **No emulator / board access.** The LCDK has no onboard emulator [S11][S12] | Medium | Blocks all board work | Week 1: can CCS connect? | Book the lab emulator in Week 1. Meanwhile do all MATLAB work and C unit tests on the PC (same C code compiled with gcc, test vectors from MATLAB). As a last resort, run in the CCS simulator if your CCS version has one (unverified) |
| R2 | **Codec / McASP setup fails** (no audio, clicks, wrong rate) | High (most common first problem) | No real-time results | Loopback not working by end of Week 3 | Use proven code: S19 support file or the Processor SDK McASP loopback [S17]. Check I2C address 0x18 [S19], McASP underrun/overrun flags [S14], cables (LINE IN vs MIC IN) |
| R3 | **Latency > 10 ms** | Medium | Misses the target from S1/S6 | T5 result | (a) The Write FIFO is already off (default 8.81 ms); turning the Read FIFO off too gives 8.60 ms; (b) shorten G/F to 17/27 taps: T0 = 21×15 = 315 samples, i.e. −1.25 ms, but the stopband falls to ≈ 31/36 dB (calculated); (c) drop to 3 levels / 4 bands; (d) minimum-phase G and F as in S2 (extra) |
| R4 | **CPU overload / missed deadlines** | Low (estimated 2–7 % at 456 MHz, ≤ 10.2 % at 300 MHz, EDMA + Read FIFO), **if the clock is right** (R11) | Clicks | Cycle log; McASP error flags | Build with `-o3`; move buffers to L2; use DSPLIB; reduce to Mode A only |
| R5 | **Aliasing / imaging** audible near crossovers | Low (simulated ≤ −67 dBc) | Distortion | T9 | Longer G (25 taps → 58.6 dB at β = 5.65, calculated). Latency rises to T0 = 27×15 = 405 samples (+0.63 ms) |
| R6 | **Overflow / clipping** (30 dB gain; Q15 if fixed point) | Medium | Harsh distortion | T10, clip counter | Float build; keep input at −40 dBFS; limiter; reduce the gain cap |
| R7 | **Acoustic feedback (howling)** when using MIC IN + headphones | Medium | Unusable demo | Squeal | Use closed headphones, lower gain, or demo with LINE IN from a PC. Adaptive feedback cancellation (S2/S5) is out of scope |
| R8 | **Delay misalignment** in Mode A (bands do not add flat) | Medium during coding | Ripple or notches | Unity-gain test 4.3 | Compare sample by sample with the MATLAB reference; check the delay lengths 365/165/65/15 |
| R9 | **OLA indexing errors** in Mode B | Medium | Periodic clicks every 2.67 ms | Clicks at the frame rate | Test against MATLAB `fftfilt` on test vectors before going real-time |
| R10 | **DSPLIB constraints** (alignment, length multiples, twiddle format). Now known: fir_gen nr ≥ 4, biquad nx multiple of 3 plus pole rule (our HPF fails it), ifftSPxSP 16-word pad, **Update 6:** the C67x v2.00 library cannot be linked (COFF vs ELF-only CGT 8.1.3); use the installed C674x DSPLIB 3.4.0.0 (fir_gen nh/nr multiples of 4; ifft 1/N; no Rev 2.0 bug) | Medium | Wrong output or crashes | Mismatch with MATLAB | Read each function page in SPRU657C; use `#pragma DATA_ALIGN`; fall back to our own C code (slower, still < 5 % CPU) |
| R11 | **Wrong CPU clock assumed** (Update 6: the Update 5 GEL-bug claim is retracted; both GELs set 300 MHz) | Low | Load % wrong | PLLC0 read-out + TSCL (06 step 0) | Report cycles (clock-independent) and load at the measured clock |
| R12 | **Unverified items turn out different** (remaining: Mode B latency model, real EDMA/FIFO behaviour on the board; ifft scaling, LED pin-mux, EDMA PaRAM, PLL and S19 constants now confirmed from the TRM/libraries) | Low–Medium | Small redesigns | Week 2 reading | See fallbacks in `02_sources.md` B |
| R13 | **Scope creep** (WDRC, 11 bands, noise reduction) | High | Unfinished core | Behind schedule at Week 8 | Freeze the core (Mode A + Mode B + tests) by Week 9; extras only after that |
| R14 | **Headphones on LINE OUT**: the jack is driven by the codec's line drivers (LEFT_LO+/RIGHT_LO+ through 10 µF), specified for a 10 kΩ load. The headphone drivers are not wired (S12 sheet 10; S13 p. 6). 16–32 Ω headphones overload the driver, and the 10 µF capacitor cuts below ≈ 0.5–1 kHz | **High** (confirmed by schematic) | Quiet, bass-less output; B1/B2 bands lost | Week 3 loopback | **Use powered speakers or a headphone amplifier on LINE OUT** (required). No register change can fix it, because the HP drivers have no jack |
| R15 | **Codec/McASP bring-up errors** (clock master, framing, FIFO/EDMA set-up). Wiring is now known (S12) and matches S19 | Low–Medium | No audio or clicks | Loopback fails; XSTAT/RSTAT error flags | Start from S19 `DSP_Init_EDMA()` with **`papers/LCDK6748_Support_DSP.c`** (saved); add the Read FIFO (RFIFOCTL before McASP reset release, DMA port 0x01D0 2000, RFMT/XFMT 0x80F0) step by step. If FIFO+EDMA fails, fall back to S19 `DSP_Init()` per-sample interrupts (FIFO off, 8.60 ms) |
| R16 | **No signal source or speakers on the day** | Medium | Demo/test blocked | — | Switch `IO_MODE` to `IO_STORED_LINEOUT` (no source) or `IO_INTERNAL` (no codec/speakers; CCS graphs + cycle-count proof), `06` §3.6 |

## Timeline – one person, 12 weeks, Claude Code writes the code

**Assumptions.** A 12-week semester (DEFAULT – confirm with team); about 8–10 h/week; board and emulator available from Week 2. The one person runs MATLAB/CCS, tests on hardware, checks outputs and writes the report.

| Week | Work | Deliverable / gate |
|---|---|---|
| 1 | Title approval (`01`). Read S2, S1, S8, S11, S13. Book board, emulator and powered speakers/HP amp from the lab. CCS 7.2 and C674x DSPLIB 3.4.0.0 are installed; MATLAB toolboxes | Title approved; tools installed; **CCS connects to board** |
| 2 | MATLAB Stage 1.1–1.4: G, F, HPF, Mode A tree; reproduce the `05` numbers. **Board step 0:** read PLLC0 registers (expect 300 MHz), start TSCL [S9 §2.9.14; TRM §7.3] | MATLAB numbers match `05` (latency 375 samples, ripple, gains) |
| 3 | Board: audio loopback at 48 kHz from S19 or the SDK example. MATLAB Stage 1.5–1.6 (Mode B, OLA/OLS) | **Loopback works**; Mode B MATLAB = `fftfilt` |
| 4 | Stage 2 fixed vs float study. Export coefficients and test vectors. C: HPF (DF-I/II/II-T) on the board | HPF on board; T14 |
| 5 | C: Mode A on PC (gcc) against test vectors, then on the board with unity gains | T3 flat; latency ≈ 375 samples (T5 first try) |
| 6 | Mode A with gain table + Goertzel meter + limiter | T2, T9, T10 for Mode A |
| 7 | C: own radix-2 FFT (check vs MATLAB) → Mode B OLA with DSPLIB FFT on the board | Mode B matches MATLAB |
| 8 | Mode B real-time + mode switch; full T2–T5 for both modes | Both modes working (**core done**) |
| 9 | Profiling: cycles, `-o0`/`-o3`, FFT benchmark (T6, T11). MATLAB comparison studies (czt, lattice, parallel, impulse invariance, matched-z, FIR cascade/freq-sampling) | All comparison plots; **core frozen** |
| 10 | Speech and noise tests (T7, T8, T12, T13). Optional extra: WDRC (T15) **or** minimum-phase | Results folder complete |
| 11 | Write the report: theory (from `04`), design (`05`), implementation, results, syllabus table (`03`) | Full draft |
| 12 | Polish, demo rehearsal, viva preparation (each person must explain every block) | Final report + demo |

**Buffer.** Weeks 10–11 can absorb up to 2 weeks of slip by dropping the extras. If the board is unavailable until later, swap Weeks 3–8 with the MATLAB/PC-only tasks of Weeks 9–10.

**Team split (if all three work).** Not required by the plan, but natural:

- Aneesh: board / CCS (Stages 3–4).
- Akula: MATLAB design + comparison studies (Stages 1–2).
- Adhvay: testing + report (T-tests, graphs).
