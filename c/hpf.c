/* Input DC/rumble high-pass: 4th-order Butterworth 100 Hz as 2 biquads, DF-II transposed,
 * float32 coefficients and samples, double-precision state (see ha.h, CHANGES C14). */
#include <string.h>
#include "ha.h"

void hpf_init(Hpf *h) { memset(h, 0, sizeof *h); }

float hpf_process(Hpf *h, float x)
{
    x = biquad_df2t(h->s[0], HA_HPF[0], x);    /* biquad_df2t in extras.c, shared with the notch */
    return biquad_df2t(h->s[1], HA_HPF[1], x);
}
