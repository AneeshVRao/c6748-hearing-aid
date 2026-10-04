# 01 – Title and Abstract (for faculty approval)

**Title:** Real-Time Digital Hearing Aid using Multirate Filter Bank and FFT-Based Overlap-Add Processing on TMS320C6748

**Team (Batch 1, DSP Lab, Dept. of ECE, NIT Warangal):**

- Aneesh Venkatesha Rao – 24ECB0A03
- Akula Sahasra – 24ECB0A02
- Adhvay Shrujal – 24ECB0A01

## Abstract (150 words)

Hearing loss varies with frequency, so a hearing aid needs per-band gain with little delay. This project builds a real-time digital hearing aid on the TI TMS320C6748 LCDK. AIC3106 codec audio is sampled at 48 kHz and processed in two selectable modes. Mode A is a five-band multirate filter bank: Kaiser-window linear-phase FIR filters and cascaded decimate-by-two stages split the signal at 750 Hz, 1.5, 3 and 6 kHz; each band is amplified by the half-gain rule for a standard moderate audiogram (Bisgaard N3) and the bands are recombined. Mode B applies the same gain curve with an FFT-based overlap-add filter designed by frequency sampling. The design is verified in MATLAB and coded in C with TI DSPLIB. Calculated latency is 8.8 ms (Mode A) and 7.7 ms (Mode B) at an estimated 2–7% CPU load. We will measure frequency response, band gains, latency and CPU cycles.

## Syllabus coverage (5 points)

1. **DFT and FFT:** DFT/IDFT, linear filtering with the DFT, overlap-add (overlap-save compared), radix-2 DIT/DIF, radix-4 and mixed-radix FFT timing, Goertzel tone meter, Chirp-Z zoom analysis.
2. **FIR filters:** linear-phase design, zero locations, window (Kaiser) and frequency-sampling design; direct form on the board; cascade, frequency-sampling and lattice structures compared in MATLAB.
3. **IIR filters:** bilinear-transform Butterworth high-pass in cascade biquads (DF-I/DF-II), with impulse invariance, matched-z, parallel and lattice forms compared.
4. **Multirate DSP:** decimation, half-band interpolation and polyphase filtering in a 4-level octave filter bank; rational I/D resampling for test signals.
5. **DSP processors:** C674x VLIW and Harvard architecture, pipelining and MAC units, fixed vs floating point, circular addressing, L1/L2/DDR2 memory, McASP, EDMA3 and I2C peripherals, cycle profiling.
