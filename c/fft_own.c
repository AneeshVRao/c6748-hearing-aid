/* Own radix-2 FFTs written from scratch (decimation in time and in frequency), complex,
 * re/im interleaved, in place. inverse = 1 uses conjugate twiddles and scales by 1/n.
 * Also provides fft256() for Mode B unless the DSPLIB version (fft_dsplib.c) is used.
 */
#include <math.h>
#include <string.h>
#include "ha.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static void bit_reverse(float *x, int n)
{
    int i, j = 0, k;
    for (i = 0; i < n - 1; i++) {
        if (i < j) {
            float tr = x[2 * i], ti = x[2 * i + 1];
            x[2 * i] = x[2 * j]; x[2 * i + 1] = x[2 * j + 1];
            x[2 * j] = tr; x[2 * j + 1] = ti;
        }
        for (k = n >> 1; k <= j; k >>= 1)
            j -= k;
        j += k;
    }
}

static void scale(float *x, int n)
{
    int i;
    for (i = 0; i < 2 * n; i++)
        x[i] /= (float)n;
}

void fft_dit(float *x, int n, int inverse)
{
    int size, half, k, s;
    const double sgn = inverse ? 1.0 : -1.0;
    bit_reverse(x, n);                          /* DIT: reorder the input, then butterflies */
    for (size = 2; size <= n; size <<= 1) {
        half = size >> 1;
        for (k = 0; k < half; k++) {
            float wr = (float)cos(2.0 * M_PI * k / size), wi = (float)(sgn * sin(2.0 * M_PI * k / size));
            for (s = k; s < n; s += size) {
                float *a = &x[2 * s], *b = &x[2 * (s + half)];
                float tr = wr * b[0] - wi * b[1], ti = wr * b[1] + wi * b[0];
                b[0] = a[0] - tr; b[1] = a[1] - ti;
                a[0] += tr;       a[1] += ti;
            }
        }
    }
    if (inverse) scale(x, n);
}

void fft_dif(float *x, int n, int inverse)
{
    int size, half, k, s;
    const double sgn = inverse ? 1.0 : -1.0;
    for (size = n; size >= 2; size >>= 1) {     /* DIF: butterflies first, output bit-reversed */
        half = size >> 1;
        for (k = 0; k < half; k++) {
            float wr = (float)cos(2.0 * M_PI * k / size), wi = (float)(sgn * sin(2.0 * M_PI * k / size));
            for (s = k; s < n; s += size) {
                float *a = &x[2 * s], *b = &x[2 * (s + half)];
                float dr = a[0] - b[0], di = a[1] - b[1];
                a[0] += b[0]; a[1] += b[1];
                b[0] = dr * wr - di * wi; b[1] = dr * wi + di * wr;
            }
        }
    }
    bit_reverse(x, n);
    if (inverse) scale(x, n);
}

#ifndef USE_DSPLIB
void fft256_init(void) {}

void fft256(float *x, float *y, int inverse)
{
    memcpy(y, x, 2 * HA_NFFT * sizeof(float));
    fft_dit(y, HA_NFFT, inverse);
}
#endif
