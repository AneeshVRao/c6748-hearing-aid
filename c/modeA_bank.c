/* Mode A: 4-level complementary octave filter bank (5 bands), processed one input sample at a time.
 * Port of ModeAStream in python/dsp_ref.py.
 *
 * Level k runs at 48 kHz / 2^k and is active when the input counter n is a multiple of 2^k.
 *   analysis : gx = G * x_k;  band b_k = x_k(n-10) - gx;  x_(k+1) = gx at even level times
 *   synthesis: y_k = g_k * b_k(n - ALIGN_k) + 2 * F * (y_(k+1) up-sampled by 2)
 * The half-band F has zero odd taps except the centre, so at even level times only its 16 even taps
 * meet non-zero inputs, and at odd times only the centre tap does (a delayed copy of y_(k+1)).
 * History buffers are written twice (at i and i+N) so every dot product reads a contiguous array.
 */
#include <string.h>
#include "ha.h"

void modeA_set_gains(ModeA *m, const float *gains)
{
    memcpy(m->g, gains, sizeof m->g);
}

void modeA_init(ModeA *m, const float *gains)
{
    int k;
    memset(m, 0, sizeof *m);
    m->ab[0] = m->ab0; m->abmask[0] = 511;
    m->ab[1] = m->ab1; m->abmask[1] = 255;
    m->ab[2] = m->ab2; m->abmask[2] = 127;
    m->ab[3] = m->ab3; m->abmask[3] = 15;
    modeA_set_gains(m, gains);
    for (k = 0; k <= HA_LEVELS; k++)            /* noise suppression state (used only if m->nr) */
        nrband_init(&m->nrb[k], (float)HA_FS / (float)(1 << k), HA_NR_BIAS_A[k]);
}

static float analysis(ModeA *m, int k, float x)
{
    int i = m->ix[k] = (m->ix[k] + 1) & 31;
    float *h = m->xh[k], *p, gx = 0.0f, b;
    int j;
    h[i] = h[i + 32] = x;
    p = &h[i + 32];                             /* p[-j] = x_k(n - j) */
    for (j = 0; j < HA_NG; j++)
        gx += HA_G[j] * p[-j];
    b = p[-HA_DG] - gx;
    i = m->ia[k] = (m->ia[k] + 1) & m->abmask[k];
    m->ab[k][i] = b;
    return gx;
}

static float synthesis(ModeA *m, int k, int even, float ynext)
{
    float *h = m->yh[k], yi = 0.0f, bd;
    int i, j;
    if (even) {
        i = m->iy[k] = (m->iy[k] + 1) & 15;
        h[i] = h[i + 16] = ynext;
        for (j = 0; j < HA_NFE; j++)
            yi += HA_FE[j] * h[i + 16 - j];
        yi *= 2.0f;
    } else {
        yi = 2.0f * HA_FC * h[m->iy[k] + 16 - HA_DF_HALF];
    }
    bd = m->ab[k][(m->ia[k] - HA_ALIGN[k]) & m->abmask[k]];
    if (m->nr)                                  /* noise suppression: per-band gain at the band's rate */
        return m->g[k] * nrband_step(&m->nrb[k], bd) * bd + yi;
    return m->g[k] * bd + yi;
}

float modeA_process(ModeA *m, float x)
{
    unsigned n = m->t++;
    int k, depth = HA_LEVELS;
    float xk = x, y;

    for (k = 0; k < HA_LEVELS; k++) {            /* analysis, down the tree */
        float gx = analysis(m, k, xk);
        if ((n >> k) & 1u) { depth = k; break; } /* odd time at level k: nothing goes further down */
        xk = gx;
    }
    y = 0.0f;
    if (depth == HA_LEVELS)                                  /* residual band B1 at fs/16 */
        y = m->g[HA_LEVELS] * (m->nr ? nrband_step(&m->nrb[HA_LEVELS], xk) : 1.0f) * xk;
    for (k = (depth < HA_LEVELS ? depth : HA_LEVELS - 1); k >= 0; k--)   /* synthesis, back up */
        y = synthesis(m, k, ((n >> k) & 1u) == 0, y);
    return y;
}
