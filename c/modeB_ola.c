/* Mode B: FFT-256 overlap-add with the 129-tap frequency-sampling FIR (H[k] precomputed).
 * L + M - 1 = 128 + 129 - 1 = 256 = N, so the circular convolution equals the linear one.
 */
#include <string.h>
#include "ha.h"

#ifdef __TI_COMPILER_VERSION__
#pragma DATA_ALIGN(xb, 8)
#pragma DATA_ALIGN(yb, 8)
#endif
static float xb[2 * HA_NFFT + 32];   /* + pad: DSPF_sp_ifftSPxSP reads 16 words past the input */
static float yb[2 * HA_NFFT + 32];

void modeB_init(ModeB *m, const float *H)
{
    memset(m->tail, 0, sizeof m->tail);
    m->H = H;
}

void modeB_block(ModeB *m, const float *in, float *out)
{
    int i;
    const float *H = m->H;
    for (i = 0; i < HA_L; i++) { xb[2 * i] = in[i]; xb[2 * i + 1] = 0.0f; }
    memset(&xb[2 * HA_L], 0, 2 * (HA_NFFT - HA_L) * sizeof(float));   /* zero-pad to 256 */
    fft256(xb, yb, 0);
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
