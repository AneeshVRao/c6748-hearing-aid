# Slides outline (12 slides, about 15 minutes)

Figures are in `results/`. Every number is from `docs/report.md`.

1. **Title**
   - Real-Time Digital Hearing Aid: Multirate Filter Bank and FFT Overlap-Add on the TMS320C6748.
   - Team names, NIT Warangal ECE.
   - Photo of the set-up (LCDK, XDS100 cable, laptop).

2. **Problem**
   - Hearing loss varies with frequency, so we need per-band gain.
   - Delay must stay under 10 ms.
   - Bisgaard N3 audiogram with the half-gain rule, 30 dB cap.
   - Figure: the audiogram and target gain table.

3. **System overview**
   - Block diagram: codec → McASP/EDMA → HPF → Mode A or B → limiter → codec (report §2).
   - Board: LCDK C6748 at 300 MHz.
   - Controls: S2 mode, S3 preset, DIP extras.

4. **Mode A: multirate filter bank**
   - 4 levels of G (21-tap Kaiser) ↓2 and F (31-tap half-band) ↑2; complementary.
   - Delay 375 samples, 5.1× cheaper than single rate.
   - Figure: `results/phase1/p1_multirate_levels.png`.

5. **Mode B: FFT overlap-add**
   - Frequency-sampling FIR, M = 129.
   - Block L = 128, FFT N = 256; time aliasing if N is too small.
   - Figures: `results/phase1/p1_ola_vs_direct.png`, `p1_fir_modeB_methods.png`.

6. **Filter design choices**
   - Window comparison (24 / 39 / 52.5 dB).
   - HPF by bilinear transform vs matched-z and impulse invariance.
   - Figures: `p1_fir_G_methods.png`, `p1_iir_hpf_methods.png`.

7. **Structures and number format**
   - Cascade vs direct / parallel / lattice under 16-bit coefficients.
   - float32 vs Q15 SNR table.
   - Figures: `results/phase2/p2_iir_quantisation.png`, `p2_snr_float_vs_q15.png`.

8. **Verification chain**
   - Python reference → MATLAB → C on the PC → C on the DSP.
   - Pre-declared gates (1e-5 / 1e-4 / 0.05 dB).
   - Board run headless with CCS scripting.

9. **Board results: correctness**
   - DSP output vs Python: ≤ 2e-5.
   - On-chip Goertzel gains vs design: within 0.01 dB (table, report §6.2).
   - Figures: `results/phase4/p4_board_gains.png` (board vs design vs target), `results/phase4/p4_board_vs_python.png`.

10. **Board results: real time**
    - Live CPU: 10.5 % (A), 4.2 % (B).
    - Lab benchmarks: FFT 2145 cycles vs DFT 108 M; `-O3` vs `-O0`.
    - Four board bugs found and fixed (C27–C30).
    - Figures: `results/phase4/p4_cpu_load.png`, `results/phase4/p4_o0_vs_o3.png`.

11. **Extras**
    - Bilinear notch with automatic howl detection.
    - Noise suppression: +6 to +9 dB SNR (PC), +8.4 / +8.8 dB on the board with built-in speech + noise.
    - Auto notch on the board: 2500 Hz tone removed within 0.5 s, no false notch on speech.
    - Figures: `results/phase3/p3_auto_notch.png`, `p3_nr_snr_gain.png`.

12. **Conclusion and next steps**
    - Mode A vs Mode B comparison table (report §8.1).
    - No external input by decision (C31): board verified with built-in signals; latency, spurs and limiter from simulation.
    - Limitations: latency calculated (8.81 / 7.67 ms), not measured; 6 kHz tone not heard at LINE OUT (cause not found); S2/S3 mode/preset jump not resolved; NR/howl methods not cited from primary sources.
    - WDRC not built.

**Demo** (after slide 10, about 2 min). No external input and no external speakers (C31, C36):
- Board, headless: run the notch example from the README (`stored_speech.out`, `g_stored_tone_hz = 2500`, auto notch on via `g_req[3]`) and show `g_ha.nt.n` = 1 and `g_ha.hd.f[0]` ≈ 2500 Hz. Set mode and preset with `g_req` rather than S2/S3 (C33).
- Laptop speakers: play the board's own output as WAVs (`python python/board_compare.py wav …`, see `docs/board_results.md`): noisy input, then Mode A and Mode B without and with noise suppression. Say that this is the DSP's exact output played back, not real time. At 0 dB (speech level) it is deliberately left alone; the trigger level between 0 and +10 dB was not measured (C32).
