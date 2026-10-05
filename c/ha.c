/* The complete hearing aid: HPF -> [feedback notch] -> Mode A or Mode B [noise suppression] -> limiter.
 *
 * Mode A runs sample by sample inside ha_process() (the audio interrupt).
 * Mode B needs 128 samples per FFT block, so it is double-buffered:
 *   - ha_process() writes each HPF output into bin[fill] and plays bout[play];
 *   - every 128 samples the filled buffer is handed to the background (pending = 1) and the
 *     buffers swap; ha_background() runs the FFT block into the buffer that plays next.
 * A sample therefore leaves 2 blocks (256 samples) after it arrived, plus the FIR's 64-sample
 * group delay: the 2L + (M-1)/2 latency model of research/05 section 7.
 *
 * Extras (off by default; python/dsp_ref.py chain(..., nr, notch)):
 *   - automatic feedback notch: the notch output is collected in 128-sample blocks; the background
 *     runs the howl detector on block j during block j+1, and a new notch becomes active at the start
 *     of block j+2;
 *   - noise suppression: per band in Mode A, per frequency sample (FIR redesign) in Mode B.
 */
#include <string.h>
#include "ha.h"

void ha_set_preset(Ha *h, int preset)
{
    h->preset = preset;
    modeA_set_gains(&h->a, HA_GAIN[preset]);
    h->b.H = HA_H[preset];
    h->b.tgt = HA_TGT[preset];
}

void ha_set_mode(Ha *h, int mode)
{
    h->mode = mode;
    modeA_init(&h->a, HA_GAIN[h->preset]);      /* restart the newly selected path from silence */
    modeB_init(&h->b, HA_H[h->preset]);
    modeB_nr_init(&h->b, HA_TGT[h->preset]);
    h->a.nr = h->b.nr = h->nr;
    memset(h->bin, 0, sizeof h->bin);
    memset(h->bout, 0, sizeof h->bout);
    h->fill = h->pos = h->ready = h->play = 0;
    h->pending = 0;
}

void ha_set_nr(Ha *h, int on)
{
    h->nr = on;
    ha_set_mode(h, h->mode);                    /* fresh noise-floor estimate */
}

void ha_set_notch_auto(Ha *h, int on)
{
    h->notch_auto = on;
    memset(&h->nt, 0, sizeof h->nt);            /* removing the notches as well when switched off */
    howl_init(&h->hd);
    h->dfill = h->dpos = h->dready = 0;
    h->dpending = 0;
}

void ha_init(Ha *h, int mode, int preset)
{
    memset(h, 0, sizeof *h);
    hpf_init(&h->hpf);
    fft256_init();
    howl_init(&h->hd);
    h->preset = preset;
    ha_set_mode(h, mode);
}

void ha_process(Ha *h, const float *in, float *out, int n)
{
    int i, j;
    for (i = 0; i < n; i++) {
        float v = hpf_process(&h->hpf, in[i]), y;
        if (h->notch_auto) {
            for (j = 0; j < h->nt.n; j++)       /* cascade of active notches */
                v = biquad_df2t(h->nt.s[j], h->nt.c[j], v);
            h->dbuf[h->dfill][h->dpos] = v;
            if (++h->dpos == HA_L) {            /* block boundary for the howl detector */
                h->dpos = 0;
                if (h->nt.pend && h->nt.n < HA_HOWL_MAX) {   /* activate the notch decided last block */
                    memcpy(h->nt.c[h->nt.n], h->nt.pend_c, sizeof h->nt.pend_c);
                    h->nt.s[h->nt.n][0] = h->nt.s[h->nt.n][1] = 0.0;
                    h->nt.n++;
                    h->nt.pend = 0;
                }
                h->dready = h->dfill;
                h->dfill ^= 1;
                h->dpending = 1;
            }
        }
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
    int ran = 0;
    if (h->pending) {
        modeB_block(&h->b, h->bin[h->ready], h->bout[h->play ^ 1]);
        h->pending = 0;
        ran = 1;
    }
    if (h->dpending) {
        float f0 = howl_block(&h->hd, h->dbuf[h->dready]);
        if (f0 > 0.0f) {
            notch_design(h->nt.pend_c, f0, HA_NOTCH_Q);
            h->nt.pend = 1;                     /* activated by ha_process at the next block boundary */
        }
        h->dpending = 0;
    }
    return ran;
}
