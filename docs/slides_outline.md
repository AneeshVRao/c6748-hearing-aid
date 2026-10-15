# Slides outline (12 slides, about 15 minutes)

Figures are in `results/`. Every number is from `docs/report.md`.

1. **Title**
   - Real-Time Digital Hearing Aid: Multirate Filter Bank and FFT Overlap-Add on the TMS320C6748.
   - Team names, NIT Warangal ECE.

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
   - Figure: `results/phase1/p1_chain_tone_gains.png` (design vs target).

10. **Board results: real time**
    - Live CPU: 10.5 % (A), 4.2 % (B).
    - Lab benchmarks: FFT 2145 cycles vs DFT 108 M; `-O3` vs `-O0`.
    - Four board bugs found and fixed (C27–C30).

11. **Extras**
    - Bilinear notch with automatic howl detection.
    - Noise suppression: +6 to +9 dB SNR (PC), +8.4 / +8.8 dB on the board with built-in speech + noise.
    - Auto notch on the board: 2500 Hz tone removed within 0.5 s, no false notch on speech.
    - Figures: `results/phase3/p3_auto_notch.png`, `p3_nr_snr_gain.png`.

12. **Conclusion and next steps**
    - Mode A vs Mode B comparison table (report §8.1).
    - No external input by decision (C31): board verified with built-in signals; latency, spurs and limiter from simulation.
    - WDRC not built.

**Demo** (after slide 10, about 2 min):
- `stored_speech.out` (no external input): built-in speech to LINE OUT. S2 switches mode, S3 cycles presets including bypass.
- Noise suppression: set `g_stored_snr_db = 5` and flip SW1-5.
