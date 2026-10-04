/* The complete hearing aid: HPF -> Mode A or Mode B -> limiter.
 *
 * Mode A runs sample by sample inside ha_process() (the audio interrupt).
 * Mode B needs 128 samples per FFT block, so it is double-buffered:
 *   - ha_process() writes each HPF output into bin[fill] and plays bout[play];
 *   - every 128 samples the filled buffer is handed to the background (pending = 1) and the
 *     buffers swap; ha_background() runs the FFT block into the buffer that plays next.
 * A sample therefore leaves 2 blocks (256 samples) after it arrived, plus the FIR's 64-sample
 * group delay: the 2L + (M-1)/2 latency model of research/05 section 7.
 */
#include <string.h>
#include "ha.h"

void ha_set_preset(Ha *h, int preset)
{
    h->preset = preset;
    modeA_set_gains(&h->a, HA_GAIN[preset]);
    h->b.H = HA_H[preset];
}

void ha_set_mode(Ha *h, int mode)
{
    h->mode = mode;
    modeA_init(&h->a, HA_GAIN[h->preset]);      /* restart the newly selected path from silence */
    modeB_init(&h->b, HA_H[h->preset]);
    memset(h->bin, 0, sizeof h->bin);
    memset(h->bout, 0, sizeof h->bout);
    h->fill = h->pos = h->ready = h->play = 0;
    h->pending = 0;
}

void ha_init(Ha *h, int mode, int preset)
{
    memset(h, 0, sizeof *h);
    hpf_init(&h->hpf);
    fft256_init();
    h->preset = preset;
    ha_set_mode(h, mode);
}

void ha_process(Ha *h, const float *in, float *out, int n)
{
    int i;
    for (i = 0; i < n; i++) {
        float v = hpf_process(&h->hpf, in[i]), y;
        if (h->mode == HA_MODE_A) {
            y = modeA_process(&h->a, v);
        } else {
            h->bin[h->fill][h->pos] = v;
            y = h->bout[h->play][h->pos];
            if (++h->pos == HA_L) {
                h->pos = 0;
                if (h->pending) h->overruns++;  /* the previous block was not processed in time */
                h->ready = h->fill;
                h->fill ^= 1;
                h->play ^= 1;                   /* play the block the background just finished */
                h->pending = 1;
            }
        }
        if (y > HA_LIMIT)       { y = HA_LIMIT;  h->clips++; }
        else if (y < -HA_LIMIT) { y = -HA_LIMIT; h->clips++; }
        out[i] = y;
    }
}

int ha_background(Ha *h)
{
    if (!h->pending)
        return 0;
    modeB_block(&h->b, h->bin[h->ready], h->bout[h->play ^ 1]);
    h->pending = 0;
    return 1;
}
