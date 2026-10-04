/* Compile-time switches for the board build. Change here, or pass -D... to cl6x (see build.bat). */
#ifndef CONFIG_H
#define CONFIG_H

/* ---- I/O mode (research/06 section 3.6) ---- */
#define IO_LIVE            0   /* LINE IN -> DSP -> LINE OUT (default) */
#define IO_STORED_LINEOUT  1   /* stored test signal in DDR2 -> DSP -> LINE OUT (no signal source needed) */
#define IO_INTERNAL        2   /* stored signal -> DSP -> array in DDR2; no codec; proof by cycle counts */
#ifndef IO_MODE
#define IO_MODE IO_LIVE
#endif

/* ---- audio servicing ----
 * 1: EDMA3 4-sample ping-pong, McASP Read FIFO on (4 words), Write FIFO off   (decided default)
 * 0: fallback, the book's DSP_Init(): one McASP interrupt per sample, FIFO off */
#ifndef IO_FIFO
#define IO_FIFO 1
#endif

/* ---- bring-up: 1 copies input to output with no processing (tests the I/O path alone) ---- */
#ifndef PASSTHROUGH
#define PASSTHROUGH 0
#endif

/* ---- which half of the 32-bit McASP word is processed ----
 * 0: low 16 bits  = codec right channel = jack TIP (works with mono and stereo plugs; default)
 * 1: high 16 bits = codec left channel  = jack RING
 * 2: average of both
 * The output goes to both channels. Board checklist step 4 verifies the assignment. */
#ifndef INPUT_SEL
#define INPUT_SEL 0
#endif

/* ---- lab experiments instead of the hearing aid (results in g_lab, read them in CCS) ---- */
#define LAB_NONE   0
#define LAB_ARITH  1   /* integer / float / double multiply-accumulate timing */
#define LAB_CONV   2   /* linear vs circular convolution */
#define LAB_DFT    3   /* direct DFT vs own FFT vs DSPLIB FFT */
#define LAB_BENCH  4   /* DSPLIB FIR/biquad/FFT benchmarks and per-block cycles of the hearing aid */
#ifndef LAB_MODE
#define LAB_MODE LAB_NONE
#endif

/* ---- start-up state ---- */
#define DEFAULT_MODE    0      /* 0 = Mode A (filter bank), 1 = Mode B (FFT OLA) */
#define DEFAULT_PRESET  0      /* 0 = N3 half-gain, 1 = N2, 2 = Bisgaard S2, 3 = bypass */

#define STORED_LEN      96000  /* 2 s at 48 kHz */

#endif
