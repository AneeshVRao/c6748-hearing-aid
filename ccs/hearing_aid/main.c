/* Real-time digital hearing aid on the TMS320C6748 LCDK.
 * Switches: config.h. Board procedure and what to read back: docs/board_checklist.md.
 *
 * Globals to watch in CCS (Expressions view):
 *   g_ha.mode, g_ha.preset, g_ha.clips, g_ha.overruns     state, limiter count, Mode B deadline misses
 *   g_ha.nr, g_ha.notch_auto, g_ha.nt.n, g_ha.hd.f         extras (DIP SW1-5 / SW1-6), active notches, Hz
 *   g_prof                                                cycles per interrupt / background block, f_CPU
 *   g_ifft_gain                                           start-up check of the ifft scaling (expect 1.0)
 *   g_int[0..3]                                           IO_INTERNAL results: Mode A, B, A + NR, B + NR
 *   g_lab                                                 lab experiments (LAB_MODE != 0)
 */
#include <c6x.h>
#include <math.h>
#include "board_io.h"
#include "lab_modes.h"

volatile float g_ifft_gain;

typedef struct { unsigned max, avg, bg_max, bg_avg; int done; float gain_db[11]; } IntRun;
volatile IntRun g_int[4];                       /* IO_INTERNAL: [0] Mode A, [1] Mode B, [2]/[3] same with NR */
#pragma DATA_SECTION(g_out, ".ddr")
float g_out[4][STORED_LEN];                     /* IO_INTERNAL outputs (Save Memory -> python/board_compare.py) */

#pragma DATA_ALIGN(sc_x, 8)
#pragma DATA_ALIGN(sc_X, 8)
#pragma DATA_ALIGN(sc_y, 8)
static float sc_x[2 * HA_NFFT + 32], sc_X[2 * HA_NFFT + 32], sc_y[2 * HA_NFFT + 32];

static void ifft_selfcheck(void)
{
    float *x = sc_x, *X = sc_X, *y = sc_y;
    float num = 0, den = 0;
    int i;
    for (i = 0; i < HA_NFFT; i++) {
        x[2 * i] = cosf(6.2831853f * 5.0f * i / HA_NFFT) + (i == 3 ? 1.0f : 0.0f);
        x[2 * i + 1] = 0.0f;
    }
    fft256(x, X, 0);
    fft256(X, y, 1);
    for (i = 0; i < HA_NFFT; i++) {
        float r = cosf(6.2831853f * 5.0f * i / HA_NFFT) + (i == 3 ? 1.0f : 0.0f);
        num += y[2 * i] * r;
        den += r * r;
    }
    g_ifft_gain = num / den;                    /* 1.0: ifft scales by 1/N; 256.0: it does not */
}

#if IO_MODE == IO_INTERNAL
static void run_internal(int mode, int nr)
{
    const int slot = mode + 2 * nr;
    unsigned long long sum = 0, bsum = 0;
    unsigned mx = 0, bmx = 0, nb = 0, c, t0;
    float in[BLOCK];
    int pos, i;
    ha_init(&g_ha, mode, DEFAULT_PRESET);
    ha_set_nr(&g_ha, nr);
    for (pos = 0; pos + BLOCK <= STORED_LEN; pos += BLOCK) {
        for (i = 0; i < BLOCK; i++) in[i] = (float)g_stored[pos + i] * (1.0f / 32768.0f);
        t0 = TSCL;
        ha_process(&g_ha, in, &g_out[slot][pos], BLOCK);
        c = TSCL - t0; sum += c; if (c > mx) mx = c;
        t0 = TSCL;
        if (ha_background(&g_ha)) { c = TSCL - t0; bsum += c; nb++; if (c > bmx) bmx = c; }
    }
    g_int[slot].max = mx;
    g_int[slot].avg = (unsigned)(sum / (STORED_LEN / BLOCK));
    g_int[slot].bg_max = bmx;
    g_int[slot].bg_avg = nb ? (unsigned)(bsum / nb) : 0;
    /* on-board tone meter (test T2): the default stored signal holds the 11 audiometric tones,
     * 8000 samples each; Goertzel over 4608 samples starting 2000 samples into each tone
     * (past the 375-sample bank delay and Mode B's 320); every tone sits on a bin (CHANGES C10) */
    if (!g_stored_loaded && !STORED_SPEECH && !nr) {
        static const int f[11] = {250, 375, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000};
        static float tin[4608];
        int t;
        for (t = 0; t < 11; t++) {
            int k = f[t] * 4608 / 48000, s0 = t * 8000 + 2000;
            for (i = 0; i < 4608; i++) tin[i] = (float)g_stored[s0 + i] * (1.0f / 32768.0f);
            g_int[slot].gain_db[t] = 20.0f * log10f(goertzel(&g_out[slot][s0], 4608, k) / goertzel(tin, 4608, k));
        }
    }
    g_int[slot].done = 1;
}
#elif LAB_MODE == LAB_NONE
static void controls(void)                      /* buttons S2/S3 and LEDs D4/D5, polled in the background */
{
    static int last;
    static unsigned t_press, clips_seen, t_clip, blinks, t_blink;
    unsigned now = g_samples;
    int b = buttons();
    if (b != last && now - t_press > 2400) {   /* 50 ms debounce */
        t_press = now;
        if ((b & 1) && !(last & 1)) {           /* S2: toggle Mode A / Mode B */
            unsigned csr = _disable_interrupts();
            ha_set_mode(&g_ha, !g_ha.mode);
            _restore_interrupts(csr);
        }
        if ((b & 2) && !(last & 2)) {           /* S3: next audiogram preset; D5 blinks preset+1 times */
            unsigned csr = _disable_interrupts();
            ha_set_preset(&g_ha, (g_ha.preset + 1) % HA_NPRESET);
            _restore_interrupts(csr);
            blinks = 2 * (g_ha.preset + 1);
            t_blink = now;
        }
        last = b;
    }
    {   /* DIP SW1-5: noise suppression, SW1-6: automatic feedback notch (ON = switch low) */
        static int sw_last = -1;
        int sw = (int)ReadSwitches();               /* book: GPIO0[1..4] = SW1-5..8, 1 = OFF */
        if (sw != sw_last) {
            unsigned csr = _disable_interrupts();
            if (sw_last < 0 || ((sw ^ sw_last) & 1)) ha_set_nr(&g_ha, !(sw & 1));
            if (sw_last < 0 || ((sw ^ sw_last) & 2)) ha_set_notch_auto(&g_ha, !(sw & 2));
            _restore_interrupts(csr);
            sw_last = sw;
        }
    }
    led(4, g_ha.mode == HA_MODE_B);
    if (blinks) {                               /* 200 ms on / 200 ms off */
        if (now - t_blink > 9600) { blinks--; t_blink = now; }
        led(5, blinks & 1);
    } else {                                    /* clip indicator: on for 100 ms after any limiting */
        if (g_ha.clips != clips_seen) { clips_seen = g_ha.clips; t_clip = now; }
        led(5, now - t_clip < 4800 && clips_seen != 0);
    }
    g_prof.rstat = McASP0_Base->rstat;
    g_prof.xstat = McASP0_Base->xstat;
}
#endif

int main(void)
{
    TSCL = 0;                                   /* any write starts the time-stamp counter (S9 2.9.14) */
    leds_init();
    ha_init(&g_ha, DEFAULT_MODE, DEFAULT_PRESET);
    ifft_selfcheck();
#if LAB_MODE != LAB_NONE
    lab_run(LAB_MODE);
    for (;;) led(5, 1);
#elif IO_MODE == IO_INTERNAL
    stored_init();
    run_internal(HA_MODE_A, 0);
    run_internal(HA_MODE_B, 0);
    run_internal(HA_MODE_A, 1);                 /* noise suppression on (verifies the extras on the DSP) */
    run_internal(HA_MODE_B, 1);
    for (;;) led(4, 1);
#else
    stored_init();
    io_start();
    for (;;) {
        unsigned t0 = TSCL;
        if (ha_background(&g_ha)) {             /* Mode B FFT block, outside the interrupt */
            unsigned c = TSCL - t0;
            if (c > g_prof.bg_max) g_prof.bg_max = c;
            g_prof.bg_sum += c;
            g_prof.bg_count++;
        }
        controls();
    }
#endif
}
