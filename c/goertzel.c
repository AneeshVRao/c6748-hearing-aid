/* Goertzel tone meter (test T2): amplitude of the component at bin k of an n-sample block.
 * One multiply per sample. Every test tone must sit on a bin: with n = 4608 all 11 audiometric
 * frequencies do (docs/CHANGES.md C10). */
#include <math.h>
#include "ha.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

float goertzel(const float *x, int n, int k)
{
    /* double accumulators: the resonator's poles sit on the unit circle, so float32 rounding
     * builds up over 4608 samples (1.9e-4 relative error); this is a test tool, cost is irrelevant */
    double c = 2.0 * cos(2.0 * M_PI * k / n), s1 = 0.0, s2 = 0.0;
    int i;
    for (i = 0; i < n; i++) {
        double s0 = x[i] + c * s1 - s2;
        s2 = s1;
        s1 = s0;
    }
    return (float)(2.0 * sqrt(s1 * s1 + s2 * s2 - c * s1 * s2) / n);
}
