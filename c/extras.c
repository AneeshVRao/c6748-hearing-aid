/* Extras from the project brief (off by default), mirroring python/dsp_ref.py:
 *   - feedback notch: 2nd-order IIR by the bilinear transform, plus automatic howl detection
 *   - noise suppression: minimum-statistics noise floor and a Wiener-type gain (Mode A per band here;
 *     the Mode B part is in modeB_ola.c)
 * All parameters are DESIGN CHOICES, listed in coeffs.h (exported from Python).
 */
#include <math.h>
#include <string.h>
#include "ha.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
#define BIG 1e30f                    /* "no minimum yet" (Python uses +inf; same resulting gain) */

/* ---------------------------------------------------------------- biquad and notch */
float biquad_df2t(double s[2], const float c[5], float x)
{
    double y = c[0] * (double)x + s[0];
    s[0] = c[1] * (double)x - c[3] * y + s[1];
    s[1] = c[2] * (double)x - c[4] * y;
    return (float)y;
}

void notch_design(float c[5], float f0, float Q)
{
    /* H(s) = (s^2 + w0^2) / (s^2 + (w0/Q) s + w0^2), bilinear with pre-warping at f0 */
    double K = tan(M_PI * f0 / HA_FS), n = 1.0 / (1.0 + K / Q + K * K);
    c[0] = (float)((1.0 + K * K) * n);
    c[1] = (float)(2.0 * (K * K - 1.0) * n);
    c[2] = c[0];
    c[3] = c[1];
    c[4] = (float)((1.0 - K / Q + K * K) * n);
}

/* ---------------------------------------------------------------- howl detector */
#ifdef __TI_COMPILER_VERSION__
#pragma DATA_ALIGN(hx, 8)
#pragma DATA_ALIGN(hX, 8)
#endif
static float hx[2 * HA_NFFT + 32], hX[2 * HA_NFFT + 32], hwin[HA_L];

void howl_init(HowlDet *d)
{
    int i;
    memset(d, 0, sizeof *d);
    d->k_prev = -10;
    for (i = 0; i < HA_L; i++)                    /* numpy.hanning(128): symmetric Hann */
        hwin[i] = (float)(0.5 - 0.5 * cos(2.0 * M_PI * i / (HA_L - 1)));
}

float howl_block(HowlDet *d, const float *xb)
{
    static float P[HA_NFFT / 2 + 1];
    const int lo = (int)ceil(HA_HOWL_LO_HZ * HA_NFFT / HA_FS), hi = (int)(HA_HOWL_HI_HZ * HA_NFFT / HA_FS);
    double e = 0.0, rest = 0.0;
    int i, k, nrest = 0, local, hit;
    float papr;
    for (i = 0; i < HA_L; i++) e += (double)xb[i] * xb[i];
    if (e / HA_L < HA_HOWL_FLOOR)                  /* silence: no decision, keep the count */
        return 0.0f;
    for (i = 0; i < HA_L; i++) { hx[2 * i] = xb[i] * hwin[i]; hx[2 * i + 1] = 0.0f; }
    memset(&hx[2 * HA_L], 0, 2 * (HA_NFFT - HA_L) * sizeof(float));
    fft256(hx, hX, 0);
    for (i = 0; i <= HA_NFFT / 2; i++) P[i] = hX[2 * i] * hX[2 * i] + hX[2 * i + 1] * hX[2 * i + 1];
    k = lo;
    for (i = lo + 1; i <= hi; i++) if (P[i] > P[k]) k = i;
    for (i = lo; i <= hi; i++)                    /* mean of the range without the main lobe (+-5 bins) */
        if (i < k - 5 || i > k + 5) { rest += P[i]; nrest++; }
    papr = (float)(P[k] / (rest / nrest + 1e-30));
    if (k - d->k_prev > 1 || d->k_prev - k > 1)   /* a different candidate: start counting again */
        d->count = 0;
    local = k > lo && k < hi && P[k] > P[k - 1] && P[k] > P[k + 1];
    hit = local && papr > (float)pow(10.0, HA_HOWL_PAPR_DB / 10.0);
    d->count = hit ? d->count + 1 : (d->count > 0 ? d->count - 1 : 0);
    d->k_prev = k;
    if (d->count >= HA_HOWL_HOLD && d->nn < HA_HOWL_MAX) {
        double a = log(P[k - 1] + 1e-30), b = log(P[k] + 1e-30), c = log(P[k + 1] + 1e-30);
        float f0 = (float)((k + 0.5 * (a - c) / (a - 2.0 * b + c)) * HA_FS / HA_NFFT);
        int j, ok = 1;
        for (j = 0; j < d->nn; j++)
            if (fabsf(f0 - d->f[j]) <= d->f[j] / HA_NOTCH_Q) ok = 0;
        if (ok) {
            d->f[d->nn++] = f0;
            d->count = 0;
            return f0;
        }
    }
    return 0.0f;
}

/* ---------------------------------------------------------------- noise floor and gain */
void mintrack_init(MinTrack *t, int n_sub, float bias)
{
    int i;
    t->cur = BIG;
    for (i = 0; i < HA_NR_NSUB; i++) t->mins[i] = BIG;
    t->i = 0;
    t->n_sub = n_sub;
    t->bias = bias;
}

float mintrack_update(MinTrack *t, float P)
{
    float m;
    int i;
    if (P > 1e-20f && P < t->cur) t->cur = P;     /* exact digital silence is ignored */
    if (++t->i == t->n_sub) {
        for (i = 0; i < HA_NR_NSUB - 1; i++) t->mins[i] = t->mins[i + 1];
        t->mins[HA_NR_NSUB - 1] = t->cur;
        t->cur = BIG;
        t->i = 0;
    }
    m = t->cur;
    for (i = 0; i < HA_NR_NSUB; i++) if (t->mins[i] < m) m = t->mins[i];
    return t->bias * m;
}

float nr_gain(float P, float N)
{
    float g2 = 1.0f - HA_NR_BETA * N / (P + 1e-30f);
    const float gmin2 = HA_NR_GMIN * HA_NR_GMIN;
    return sqrtf(g2 > gmin2 ? g2 : gmin2);
}

void nrband_init(NrBand *b, float fs_k, float bias)
{
    mintrack_init(&b->mt, (int)floor(HA_NR_SUB * fs_k + 0.5), bias);
    b->a_p = (float)exp(-1.0 / (HA_NR_TAU_P * fs_k));
    b->a_g = (float)exp(-1.0 / (HA_NR_TAU_G * fs_k));
    b->n_warm = (int)floor(3.0 * HA_NR_TAU_P * fs_k + 0.5);
    b->P = 0.0f;
    b->Gs = 1.0f;
    b->seen = 0;
}

float nrband_step(NrBand *b, float s)
{
    float N;
    if (b->seen == 0 && s == 0.0f)                 /* leading zeros (alignment delay): pass through */
        return b->Gs;
    b->seen++;
    b->P = b->a_p * b->P + (1.0f - b->a_p) * s * s;
    N = b->seen > b->n_warm ? mintrack_update(&b->mt, b->P) : 0.0f;
    b->Gs = b->a_g * b->Gs + (1.0f - b->a_g) * nr_gain(b->P, N);
    return b->Gs;
}
