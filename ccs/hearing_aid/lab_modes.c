/* Lab experiments (LAB_MODE in config.h). Results go into g_lab; read them in the CCS Expressions view.
 * The same file builds on the PC (c/build_pc.bat -> lab_check), where the DSPLIB calls map to TI's
 * natural-C reference code and TSCL reads 0: that checks every DSPLIB argument, twiddle table and
 * output ordering before the board runs it. Cycle counts are only meaningful on the board.
 */
#include <math.h>
#include <string.h>
#include "ha.h"
#include "lab_modes.h"

#ifdef __TI_COMPILER_VERSION__
#include <c6x.h>
#include <ti/dsplib/dsplib.h>
#define NOW() TSCL
#else      /* PC: TI natural-C reference functions */
#define NOW() 0u
void DSPF_sp_fir_gen_cn(const float *, const float *, float *, int, int);
void DSPF_sp_biquad_cn(float *, float *, float *, float *, float *, const int);
void DSPF_sp_cfftr2_dit_cn(float *, float *, unsigned short);
void DSPF_sp_icfftr2_dif_cn(float *, float *, unsigned short);
void DSPF_sp_cfftr4_dif_cn(float *, float *, unsigned short);
#define DSPF_sp_fir_gen    DSPF_sp_fir_gen_cn
#define DSPF_sp_biquad     DSPF_sp_biquad_cn
#define DSPF_sp_cfftr2_dit DSPF_sp_cfftr2_dit_cn
#define DSPF_sp_icfftr2_dif DSPF_sp_icfftr2_dif_cn
#define DSPF_sp_cfftr4_dif DSPF_sp_cfftr4_dif_cn
#endif

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
#define N 256

volatile Lab g_lab;

#ifdef __TI_COMPILER_VERSION__
#pragma DATA_ALIGN(xa, 8)
#pragma DATA_ALIGN(xb, 8)
#pragma DATA_ALIGN(xc, 8)
#pragma DATA_ALIGN(w, 8)
#pragma DATA_ALIGN(firx, 8)
#pragma DATA_ALIGN(firh, 8)
#pragma DATA_ALIGN(firy, 8)
#pragma DATA_ALIGN(bq_b, 8)
#pragma DATA_ALIGN(bq_a, 8)
#endif
static float xa[2 * N + 32], xb[2 * N + 32], xc[2 * N + 32], w[2 * N];
static float firx[72], firh[24], firy[48], firy2[48];
static float bq_b[4], bq_a[4], bq_d[2], bq_y[48], bq_y2[48];

static float randf(unsigned *s) { *s = *s * 1664525u + 1013904223u; return (float)(int)(*s >> 9) / 4194304.0f - 1.0f; }

static void test_vector(float *x, int n)       /* deterministic complex test signal */
{
    unsigned s = 7u;
    int i;
    for (i = 0; i < 2 * n; i++) x[i] = randf(&s);
}

static float max_err(const float *a, const float *b, int n)
{
    float e = 0.0f;
    int i;
    for (i = 0; i < n; i++) if (fabsf(a[i] - b[i]) > e) e = fabsf(a[i] - b[i]);
    return e;
}

static void bitrev_cplx_c(float *x, int n)     /* plain-C bit reversal (complex, interleaved) */
{
    int i, j = 0, k;
    for (i = 0; i < n - 1; i++) {
        if (i < j) { float t = x[2 * i]; x[2 * i] = x[2 * j]; x[2 * j] = t;
                     t = x[2 * i + 1]; x[2 * i + 1] = x[2 * j + 1]; x[2 * j + 1] = t; }
        for (k = n >> 1; k <= j; k >>= 1) j -= k;
        j += k;
    }
}

static void digitrev4_cplx_c(float *x, int n)  /* base-4 digit reversal (radix-4 output order), n = 4^m */
{
    static float t[2 * N];
    int i, k, m = 0;
    for (k = n; k > 1; k >>= 2) m++;
    for (i = 0; i < n; i++) {
        int r = 0, v = i;
        for (k = 0; k < m; k++) { r = (r << 2) | (v & 3); v >>= 2; }
        t[2 * r] = x[2 * i]; t[2 * r + 1] = x[2 * i + 1];
    }
    memcpy(x, t, 2 * n * sizeof(float));
}

/* ---------------------------------------------------------------- LAB_ARITH */
void lab_arith(void)
{
    static short s16[N]; static int i32[N]; static float f32[N]; static double f64[N];
    int i, acc_i = 0; long long acc_l = 0; float acc_f = 0; double acc_d = 0;
    unsigned t;
    for (i = 0; i < N; i++) { s16[i] = (short)(i * 37 - 4000); i32[i] = i * 37 - 4000; f32[i] = (float)i32[i]; f64[i] = i32[i]; }
    t = NOW(); for (i = 0; i < N; i++) acc_i += s16[i] * s16[N - 1 - i];         g_lab.arith_cycles[0] = NOW() - t;
    t = NOW(); for (i = 0; i < N; i++) acc_l += (long long)i32[i] * i32[N - 1 - i]; g_lab.arith_cycles[1] = NOW() - t;
    t = NOW(); for (i = 0; i < N; i++) acc_f += f32[i] * f32[N - 1 - i];         g_lab.arith_cycles[2] = NOW() - t;
    t = NOW(); for (i = 0; i < N; i++) acc_d += f64[i] * f64[N - 1 - i];         g_lab.arith_cycles[3] = NOW() - t;
    g_lab.arith_result[0] = (double)acc_i; g_lab.arith_result[1] = (double)acc_l;
    g_lab.arith_result[2] = acc_f;         g_lab.arith_result[3] = acc_d;
}

/* ---------------------------------------------------------------- LAB_CONV */
static void dft(const float *x, float *X, int n, int inverse)   /* direct DFT, complex interleaved */
{
    int k, m;
    for (k = 0; k < n; k++) {
        double re = 0, im = 0;
        for (m = 0; m < n; m++) {
            double a = (inverse ? 2 : -2) * M_PI * k * m / n;
            re += x[2 * m] * cos(a) - x[2 * m + 1] * sin(a);
            im += x[2 * m] * sin(a) + x[2 * m + 1] * cos(a);
        }
        X[2 * k] = (float)(inverse ? re / n : re);
        X[2 * k + 1] = (float)(inverse ? im / n : im);
    }
}

static void circ_conv_dft(const float *x, int nx, const float *h, int nh, float *y, int n)
{
    float a[32], b[32], A[32], B[32];
    int i;
    memset(a, 0, sizeof a); memset(b, 0, sizeof b);
    for (i = 0; i < nx; i++) a[2 * (i % n)] += x[i];   /* sequences longer than n wrap around */
    for (i = 0; i < nh; i++) b[2 * (i % n)] += h[i];
    dft(a, A, n, 0); dft(b, B, n, 0);
    for (i = 0; i < n; i++) {                           /* Y = X H */
        float r = A[2 * i] * B[2 * i] - A[2 * i + 1] * B[2 * i + 1];
        a[2 * i + 1] = A[2 * i] * B[2 * i + 1] + A[2 * i + 1] * B[2 * i];
        a[2 * i] = r;
    }
    dft(a, A, n, 1);
    for (i = 0; i < n; i++) y[i] = A[2 * i];
}

void lab_conv(void)
{
    static const float x[4] = {1, 2, 3, 4}, h[3] = {1, 1, 1};
    int n, k;
    for (n = 0; n < 6; n++) {                           /* linear: y[n] = sum h[k] x[n-k] */
        float s = 0;
        for (k = 0; k < 3; k++) if (n - k >= 0 && n - k < 4) s += h[k] * x[n - k];
        g_lab.conv_linear[n] = s;                       /* expect 1 3 6 9 7 4 */
    }
    circ_conv_dft(x, 4, h, 3, (float *)g_lab.conv_circ4, 4);   /* N = 4 < 4+3-1: aliased, expect 8 7 6 9 */
    circ_conv_dft(x, 4, h, 3, (float *)g_lab.conv_circ6, 6);   /* N = 6 = 4+3-1: equals linear */
}

/* ---------------------------------------------------------------- LAB_DFT */
void lab_dft(void)
{
    unsigned t;
    test_vector(xa, N);
    memcpy(xc, xa, sizeof xa);
    t = NOW(); dft(xa, xb, N, 0);        g_lab.dft_cycles[0] = NOW() - t;    /* direct DFT, N^2 */
    t = NOW(); fft_dit(xc, N, 0);        g_lab.dft_cycles[1] = NOW() - t;    /* own radix-2 */
    g_lab.dft_err[0] = max_err(xb, xc, 2 * N);
    test_vector(xa, N);
    t = NOW(); fft256(xa, xc, 0);        g_lab.dft_cycles[2] = NOW() - t;    /* DSPLIB fftSPxSP */
    g_lab.dft_err[1] = max_err(xb, xc, 2 * N);
}

/* ---------------------------------------------------------------- LAB_BENCH */
void lab_bench(void)
{
    static float ref[2 * N];
    static ModeA ma; static ModeB mb; static Ha ha; static Hpf hp;
    static float in[HA_L], out[HA_L];
    unsigned t, s = 99u;
    int i, j;

    /* FIR: DSPLIB fir_gen (G padded 21 -> 24 taps, nr 48; reversed coefficients) vs plain C, 21 taps */
    for (i = 0; i < 72; i++) firx[i] = randf(&s);
    memset(firh, 0, sizeof firh);
    for (i = 0; i < HA_NG; i++) firh[i] = HA_G[HA_NG - 1 - i];
    t = NOW(); DSPF_sp_fir_gen(firx, firh, firy, 24, 48); g_lab.bench[B_FIR_DSPLIB] = NOW() - t;
    t = NOW();
    for (j = 0; j < 48; j++) { float acc = 0; for (i = 0; i < HA_NG; i++) acc += HA_G[i] * firx[j + HA_NG - 1 - i]; firy2[j] = acc; }
    g_lab.bench[B_FIR_C] = NOW() - t;
    g_lab.bench_err[B_FIR_DSPLIB] = max_err(firy, firy2, 48);

    /* biquad: DSPLIB vs plain C DF-II-T, nx 48, test coefficients with |a1| < 1 (S15 p. 4-46 rule) */
    bq_b[0] = 0.2f; bq_b[1] = 0.4f; bq_b[2] = 0.2f; bq_a[0] = 1.0f; bq_a[1] = -0.5f; bq_a[2] = 0.25f;
    bq_d[0] = bq_d[1] = 0.0f;
    t = NOW(); DSPF_sp_biquad(firx, bq_b, bq_a, bq_d, bq_y, 48); g_lab.bench[B_BIQUAD_DSPLIB] = NOW() - t;
    t = NOW();
    { float s1 = 0, s2 = 0; for (i = 0; i < 48; i++) { float y = bq_b[0] * firx[i] + s1;
        s1 = bq_b[1] * firx[i] - bq_a[1] * y + s2; s2 = bq_b[2] * firx[i] - bq_a[2] * y; bq_y2[i] = y; } }
    g_lab.bench[B_BIQUAD_C] = NOW() - t;
    g_lab.bench_err[B_BIQUAD_DSPLIB] = max_err(bq_y, bq_y2, 48);

    /* reference spectrum: own radix-2 FFT */
    test_vector(ref, N);
    t = NOW(); fft_dit(ref, N, 0); g_lab.bench[B_FFT_OWN] = NOW() - t;

    /* radix-2 DIT (twiddles: N/2 values, bit-reversed order), output bit-reversed -> reorder in C */
    for (i = 0; i < N / 2; i++) { w[2 * i] = (float)cos(2 * M_PI * i / N); w[2 * i + 1] = (float)sin(2 * M_PI * i / N); }
    bitrev_cplx_c(w, N / 2);
    test_vector(xa, N);
    t = NOW(); DSPF_sp_cfftr2_dit(xa, w, N); g_lab.bench[B_CFFTR2] = NOW() - t;
    memcpy(xb, xa, sizeof xa);                          /* keep the bit-reversed spectrum for the DIF chain */
    t = NOW(); bitrev_cplx_c(xa, N); g_lab.bench[B_BITREV_C] = NOW() - t;
    g_lab.bench_err[B_CFFTR2] = max_err(xa, ref, 2 * N);
    /* inverse radix-2 DIF takes the bit-reversed spectrum directly: no reordering step */
    t = NOW(); DSPF_sp_icfftr2_dif(xb, w, N); g_lab.bench[B_ICFFTR2] = NOW() - t;
    test_vector(xa, N);
    {   /* gain of the DIT -> DIF round trip: 1 if the inverse scales by 1/N, N if it does not */
        float num = 0, den = 0;
        for (i = 0; i < 2 * N; i++) { num += xb[i] * xa[i]; den += xa[i] * xa[i]; }
        g_lab.icfftr2_gain = num / den;
    }

    /* radix-4 DIF (twiddles: 3N/4 values in natural order). The output is base-4 DIGIT-reversed; the
     * bit_rev() in TI's test driver does not restore natural order (checked on the PC, CHANGES C15). */
    for (i = 0; i < 3 * N / 4; i++) { w[2 * i] = (float)cos(2 * M_PI * i / N); w[2 * i + 1] = (float)sin(2 * M_PI * i / N); }
    test_vector(xa, N);
    t = NOW(); DSPF_sp_cfftr4_dif(xa, w, N); g_lab.bench[B_CFFTR4] = NOW() - t;
    digitrev4_cplx_c(xa, N);
    g_lab.bench_err[B_CFFTR4] = max_err(xa, ref, 2 * N);

    /* mixed radix (the Mode B FFT) and its inverse */
    test_vector(xa, N);
    t = NOW(); fft256(xa, xc, 0); g_lab.bench[B_FFTSPXSP] = NOW() - t;
    g_lab.bench_err[B_FFTSPXSP] = max_err(xc, ref, 2 * N);
    t = NOW(); fft256(xc, xa, 1); g_lab.bench[B_IFFTSPXSP] = NOW() - t;
    test_vector(xb, N);
    g_lab.bench_err[B_IFFTSPXSP] = max_err(xa, xb, 2 * N);

    /* hearing-aid blocks */
    hpf_init(&hp);
    t = NOW(); for (i = 0; i < 48; i++) out[i] = hpf_process(&hp, firx[i]); g_lab.bench[B_HPF48] = NOW() - t;
    modeA_init(&ma, HA_GAIN[0]);
    t = NOW(); for (i = 0; i < 48; i++) out[i] = modeA_process(&ma, firx[i]); g_lab.bench[B_MODEA48] = NOW() - t;
    for (i = 0; i < HA_L; i++) in[i] = randf(&s) * 0.01f;
    modeB_init(&mb, HA_H[0]);
    t = NOW(); modeB_block(&mb, in, out); g_lab.bench[B_MODEB_BLOCK] = NOW() - t;
    ha_init(&ha, HA_MODE_A, 0);
    t = NOW(); ha_process(&ha, in, out, 4); g_lab.bench[B_HA_A4] = NOW() - t;
    ha_init(&ha, HA_MODE_B, 0);
    t = NOW(); ha_process(&ha, in, out, 4); g_lab.bench[B_HA_B4] = NOW() - t;

    /* extras: noise suppression (after the noise tracker is past its warm-up), howl detector, notch */
    modeA_init(&ma, HA_GAIN[0]);
    ma.nr = 1;
    for (j = 0; j < 4800; j++) modeA_process(&ma, randf(&s) * 0.01f);
    t = NOW(); for (i = 0; i < 48; i++) out[i] = modeA_process(&ma, firx[i]); g_lab.bench[B_MODEA48_NR] = NOW() - t;
    modeB_init(&mb, HA_H[0]);
    modeB_nr_init(&mb, HA_TGT[0]);
    mb.nr = 1;
    for (j = 0; j < 20; j++) modeB_block(&mb, in, out);
    t = NOW(); modeB_block(&mb, in, out); g_lab.bench[B_MODEB_BLOCK_NR] = NOW() - t;
    {
        static HowlDet hd;
        static float c[5];
        static double st[2];
        howl_init(&hd);
        t = NOW(); howl_block(&hd, in); g_lab.bench[B_HOWL_BLOCK] = NOW() - t;
        notch_design(c, 2500.0f, HA_NOTCH_Q);
        st[0] = st[1] = 0.0;
        t = NOW(); for (i = 0; i < 48; i++) out[i] = biquad_df2t(st, c, firx[i]); g_lab.bench[B_NOTCH48] = NOW() - t;
    }
}

void lab_run(int mode)
{
    memset((void *)&g_lab, 0, sizeof g_lab);
    fft256_init();
    if (mode == 1) lab_arith();
    if (mode == 2) lab_conv();
    if (mode == 3) lab_dft();
    if (mode == 4) lab_bench();
    g_lab.done = 1;
}
