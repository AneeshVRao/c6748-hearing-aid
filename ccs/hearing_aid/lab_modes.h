/* Lab experiment results (see lab_modes.c). Cycle counts come from TSCL on the board. */
#ifndef LAB_MODES_H
#define LAB_MODES_H

enum {
    B_FIR_DSPLIB, B_FIR_C, B_BIQUAD_DSPLIB, B_BIQUAD_C,
    B_FFT_OWN, B_CFFTR2, B_BITREV_C, B_ICFFTR2, B_CFFTR4, B_FFTSPXSP, B_IFFTSPXSP,
    B_HPF48, B_MODEA48, B_MODEB_BLOCK, B_HA_A4, B_HA_B4, B_COUNT
};

typedef struct {
    int      done;
    unsigned arith_cycles[4];        /* 256 MACs: int16, int32 (64-bit acc), float, double */
    double   arith_result[4];
    float    conv_linear[6], conv_circ4[4], conv_circ6[6];
    unsigned dft_cycles[3];          /* N = 256: direct DFT, own radix-2, DSPLIB fftSPxSP */
    float    dft_err[2];             /* own FFT and DSPLIB FFT vs direct DFT */
    unsigned bench[B_COUNT];         /* cycles, indexed by the enum above */
    float    bench_err[B_COUNT];     /* max |error| vs plain C or own FFT */
    float    icfftr2_gain;           /* cfftr2_dit -> icfftr2_dif round-trip gain */
} Lab;

extern volatile Lab g_lab;
void lab_run(int mode);

#endif
