/* Mode B: FFT-256 overlap-add with the 129-tap frequency-sampling FIR (H[k] precomputed).
 * L + M - 1 = 128 + 129 - 1 = 256 = N, so the circular convolution equals the linear one.
 * With noise suppression on, the FIR is redesigned every block from (target x gain) at its 65
 * frequency samples, so every block is still an exact linear convolution (python/dsp_ref.py mode_b_nr).
 */
#include <math.h>
#include <string.h>
#include "ha.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
#define BIG 1e30f

#ifdef __TI_COMPILER_VERSION__
#pragma DATA_ALIGN(xb, 8)
#pragma DATA_ALIGN(yb, 8)
#pragma DATA_ALIGN(hb, 8)
#pragma DATA_ALIGN(Hb, 8)
#endif
static float xb[2 * HA_NFFT + 32];   /* + pad: DSPF_sp_ifftSPxSP reads 16 words past the input */
static float yb[2 * HA_NFFT + 32];
static float hb[2 * HA_NFFT + 32], Hb[2 * HA_NFFT + 32];   /* noise suppression: redesigned FIR */
static float nr_cos[HA_NR_NJ][(HA_MB + 1) / 2];             /* cos(2 pi j (n - 64) / 129), n = 0..64 */
static int   nr_bin[HA_NR_NJ];

void modeB_init(ModeB *m, const float *H)
{
    memset(m->tail, 0, sizeof m->tail);
    m->H = H;
}

void modeB_nr_init(ModeB *m, const float *tgt)
{
    int j, n;
    for (j = 0; j < HA_NR_NJ; j++) {
        nr_bin[j] = (int)floor((double)j * HA_NFFT / HA_MB + 0.5);
        for (n = 0; n < (HA_MB + 1) / 2; n++)
            nr_cos[j][n] = (float)cos(2.0 * M_PI * j * (n - (HA_MB - 1) / 2) / HA_MB);
        m->P[j] = 0.0f;
        m->Gs[j] = 1.0f;
        m->mcur[j] = BIG;
        for (n = 0; n < HA_NR_NSUB; n++) m->mins[n][j] = BIG;
    }
    m->tgt = tgt;
    m->seen = 0;
    m->mi = 0;
}

static const float *nr_update(ModeB *m)            /* yb holds X[k]; returns the block's new H */
{
    static const double dt = (double)HA_L / HA_FS;
    const float a_p = (float)exp(-dt / HA_NR_TAU_P), a_g = (float)exp(-dt / HA_NR_TAU_G);
    const int n_sub = (int)floor(HA_NR_SUB / dt + 0.5), n_warm = (int)floor(3.0 * HA_NR_TAU_P / dt + 0.5);
    float Pj[HA_NR_NJ], h[(HA_MB + 1) / 2];
    int j, n, any = 0, roll = 0;
    for (j = 0; j < HA_NR_NJ; j++) {               /* power around each frequency sample (3 bins) */
        int b = nr_bin[j], lo = b > 0 ? b - 1 : 0, i;
        float s = 0.0f;
        for (i = lo; i <= b + 1; i++) s += yb[2 * i] * yb[2 * i] + yb[2 * i + 1] * yb[2 * i + 1];
        Pj[j] = s / (float)(b + 2 - lo);
        if (Pj[j] != 0.0f) any = 1;
    }
    if (m->seen > 0 || any) {
        m->seen++;
        if (m->seen > n_warm && ++m->mi == n_sub) { roll = 1; m->mi = 0; }
        for (j = 0; j < HA_NR_NJ; j++) {
            float N = 0.0f;
            m->P[j] = m->seen == 1 ? Pj[j] : a_p * m->P[j] + (1.0f - a_p) * Pj[j];
            if (m->seen > n_warm) {                    /* minimum statistics over 4 x 0.375 s */
                float mn;
                if (m->P[j] > 1e-20f && m->P[j] < m->mcur[j]) m->mcur[j] = m->P[j];
                if (roll) {
                    for (n = 0; n < HA_NR_NSUB - 1; n++) m->mins[n][j] = m->mins[n + 1][j];
                    m->mins[HA_NR_NSUB - 1][j] = m->mcur[j];
                    m->mcur[j] = BIG;
                }
                mn = m->mcur[j];
                for (n = 0; n < HA_NR_NSUB; n++) if (m->mins[n][j] < mn) mn = m->mins[n][j];
                N = HA_NR_BIAS_B * mn;
            }
            m->Gs[j] = a_g * m->Gs[j] + (1.0f - a_g) * nr_gain(m->P[j], N);
        }
    }
    for (n = 0; n < (HA_MB + 1) / 2; n++) {        /* frequency sampling: h[n] = h[128 - n] */
        float s = m->tgt[0] * m->Gs[0] * nr_cos[0][n];
        for (j = 1; j < HA_NR_NJ; j++) s += 2.0f * m->tgt[j] * m->Gs[j] * nr_cos[j][n];
        h[n] = s / HA_MB;
    }
    memset(hb, 0, 2 * HA_NFFT * sizeof(float));
    for (n = 0; n < (HA_MB + 1) / 2; n++) { hb[2 * n] = h[n]; hb[2 * (HA_MB - 1 - n)] = h[n]; }
    fft256(hb, Hb, 0);
    return Hb;
}

void modeB_block(ModeB *m, const float *in, float *out)
{
    int i;
    const float *H;
    for (i = 0; i < HA_L; i++) { xb[2 * i] = in[i]; xb[2 * i + 1] = 0.0f; }
    memset(&xb[2 * HA_L], 0, 2 * (HA_NFFT - HA_L) * sizeof(float));   /* zero-pad to 256 */
    fft256(xb, yb, 0);
    H = m->nr ? nr_update(m) : m->H;
    for (i = 0; i < HA_NFFT; i++) {             /* Y[k] = X[k] H[k] */
        float xr = yb[2 * i], xi = yb[2 * i + 1];
        xb[2 * i]     = xr * H[2 * i] - xi * H[2 * i + 1];
        xb[2 * i + 1] = xr * H[2 * i + 1] + xi * H[2 * i];
    }
    fft256(xb, yb, 1);                          /* inverse, includes 1/N */
    for (i = 0; i < HA_L; i++) {
        out[i] = yb[2 * i] + m->tail[i];        /* first half + previous overlap */
        m->tail[i] = yb[2 * (i + HA_L)];        /* second half kept for the next block */
    }
}
