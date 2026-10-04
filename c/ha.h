/* Hearing-aid signal processing: portable C, shared by the PC test and the C6748 board build.
 * Every block mirrors python/dsp_ref.py; c/pc_test.c checks them against Python's outputs.
 */
#ifndef HA_H_INCLUDED
#define HA_H_INCLUDED

#include "coeffs.h"

enum { HA_MODE_A = 0, HA_MODE_B = 1 };

/* ---- input high-pass: 2 biquads, DF-II transposed (Phase 2: lowest float32 noise) ----
 * The two state variables per biquad are kept in double precision: with poles at r = 0.995 the
 * float32 state noise reached 1.3 LSB of the 16-bit output and was amplified up to 30 dB by the
 * gains (docs/CHANGES.md C14). The C674x has hardware double precision. */
typedef struct { double s[2][2]; } Hpf;
void  hpf_init(Hpf *h);
float hpf_process(Hpf *h, float x);

/* ---- Mode A: 5-band multirate octave filter bank, one sample at a time ---- */
typedef struct {
    float xh[HA_LEVELS][64];     /* G input history, written twice (i and i+32) for linear reads */
    float yh[HA_LEVELS][32];     /* half-band input history (y of the level below), doubled as well */
    float ab0[512], ab1[256], ab2[128], ab3[16];   /* band alignment delay lines (power of 2) */
    float *ab[HA_LEVELS];
    int   abmask[HA_LEVELS];
    int   ix[HA_LEVELS], iy[HA_LEVELS], ia[HA_LEVELS];
    unsigned t;                  /* input sample counter */
    float g[HA_LEVELS + 1];      /* linear band gains B5..B1 */
} ModeA;
void  modeA_init(ModeA *m, const float *gains);
void  modeA_set_gains(ModeA *m, const float *gains);
float modeA_process(ModeA *m, float x);

/* ---- Mode B: FFT-256 overlap-add, 128 new samples per block ---- */
typedef struct {
    float tail[HA_L];            /* overlap from the previous block */
    const float *H;              /* 2*HA_NFFT floats, re/im interleaved */
} ModeB;
void modeB_init(ModeB *m, const float *H);
void modeB_block(ModeB *m, const float *in, float *out);    /* in, out: HA_L samples */

/* FFT used by Mode B: complex, N = 256, re/im interleaved, out-of-place; inverse scales by 1/N.
 * fft_own.c (own radix-2) or fft_dsplib.c (TI DSPF_sp_fftSPxSP / ifftSPxSP) provides it. */
void fft256_init(void);
void fft256(float *x, float *y, int inverse);

/* ---- own radix-2 FFTs (learning + comparison), any power-of-2 n, in place ---- */
void fft_dit(float *x, int n, int inverse);
void fft_dif(float *x, int n, int inverse);

/* ---- Goertzel tone meter: amplitude of the tone at bin k of an n-sample block ---- */
float goertzel(const float *x, int n, int k);

/* ---- complete hearing aid: HPF -> Mode A or B -> limiter ---- */
typedef struct {
    Hpf   hpf;
    ModeA a;
    ModeB b;
    int   mode, preset;
    /* Mode B double buffering (see ha.c): filled in the audio interrupt, processed in the background */
    float bin[2][HA_L], bout[2][HA_L];
    int   fill, pos, ready, play;
    volatile int pending;
    unsigned overruns;           /* background FFT not finished within one block (128 samples) */
    unsigned clips;              /* samples limited */
} Ha;
void ha_init(Ha *h, int mode, int preset);
void ha_set_mode(Ha *h, int mode);
void ha_set_preset(Ha *h, int preset);
void ha_process(Ha *h, const float *in, float *out, int n);   /* audio interrupt: n samples */
int  ha_background(Ha *h);                                    /* background loop: Mode B FFT */

#endif
