/* Input DC/rumble high-pass: 4th-order Butterworth 100 Hz as 2 biquads, DF-II transposed,
 * float32 coefficients and samples, double-precision state (see ha.h). */
#include <string.h>
#include "ha.h"

void hpf_init(Hpf *h) { memset(h, 0, sizeof *h); }

float hpf_process(Hpf *h, float x)
{
    int i;
    for (i = 0; i < 2; i++) {
        const float *c = HA_HPF[i];             /* b0 b1 b2 a1 a2 */
        double *s = h->s[i];
        double y = c[0] * (double)x + s[0];
        s[0] = c[1] * x - c[3] * y + s[1];
        s[1] = c[2] * x - c[4] * y;
        x = (float)y;
    }
    return x;
}
