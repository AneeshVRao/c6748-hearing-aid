/* fft256() on TI's C674x DSPLIB: DSPF_sp_fftSPxSP / DSPF_sp_ifftSPxSP (mixed radix, N = 256 = 4^4).
 * Board: links dsplib.ae674. PC test: links TI's natural-C reference versions (_cn) instead, so the
 * twiddle table, bit-reverse table and arguments are checked against Python before the board runs.
 * The twiddle layout follows the DSPLIB documentation (tw_gen in the library's test driver):
 * for each radix-4 stage j = 1, 4, 16, ... and i = 0, j, 2j, ... < N/4:
 *   cos/sin of (2 pi i / N), (4 pi i / N), (6 pi i / N).
 * The ifft output is scaled by 1/N (C674x _cn.c), the same convention as fft_own.c.
 */
#include <math.h>
#include "ha.h"

#ifdef __TI_COMPILER_VERSION__
#include <ti/dsplib/dsplib.h>
#include <c6x.h>
#define FFT  DSPF_sp_fftSPxSP
#define IFFT DSPF_sp_ifftSPxSP
#pragma DATA_ALIGN(tw, 8)
#pragma DATA_ALIGN(brev, 8)
#else   /* PC test: TI natural-C reference implementations */
void DSPF_sp_fftSPxSP_cn(int, float *, float *, float *, unsigned char *, int, int, int);
void DSPF_sp_ifftSPxSP_cn(int, float *, float *, float *, unsigned char *, int, int, int);
#define FFT  DSPF_sp_fftSPxSP_cn
#define IFFT DSPF_sp_ifftSPxSP_cn
#endif

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static float tw[2 * HA_NFFT];
static unsigned char brev[64];          /* 6-bit bit-reversal table used by the library */

void fft256_init(void)
{
    int i, j, k = 0, b;
    for (j = 1; j <= HA_NFFT >> 2; j <<= 2)
        for (i = 0; i < HA_NFFT >> 2; i += j) {
            double t = 2.0 * M_PI * i / HA_NFFT;
            tw[k]     = (float)cos(t);     tw[k + 1] = (float)sin(t);
            tw[k + 2] = (float)cos(2 * t); tw[k + 3] = (float)sin(2 * t);
            tw[k + 4] = (float)cos(3 * t); tw[k + 5] = (float)sin(3 * t);
            k += 6;
        }
    for (i = 0; i < 64; i++) {
        int r = 0;
        for (b = 0; b < 6; b++)
            r |= ((i >> b) & 1) << (5 - b);
        brev[i] = (unsigned char)r;
    }
}

void fft256(float *x, float *y, int inverse)
{
#ifdef __TI_COMPILER_VERSION__
    /* DSPLIB FFTs are interrupt-tolerant but not interruptible: run with interrupts off.
     * The McASP Read FIFO (4 of 64 words used) covers the ~2000-cycle (6.6 us) window. */
    unsigned int csr = _disable_interrupts();
#endif
    /* n_min = 4 because 256 is a power of 4; offset 0, n_max = N (whole transform) */
    if (inverse) IFFT(HA_NFFT, x, tw, y, brev, 4, 0, HA_NFFT);
    else         FFT(HA_NFFT, x, tw, y, brev, 4, 0, HA_NFFT);
#ifdef __TI_COMPILER_VERSION__
    _restore_interrupts(csr);
#endif
}
