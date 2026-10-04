/* LCDK board I/O: codec + McASP + EDMA, LEDs, buttons, cycle counter. */
#ifndef BOARD_IO_H
#define BOARD_IO_H

#include "DSP_Config.h"      /* third_party/rt-dsp (book): register map, codec helpers */
#include "config.h"
#include "ha.h"

#define BLOCK 4              /* samples per EDMA block */

/* cycle statistics, readable in the CCS Expressions view */
typedef struct {
    unsigned isr_max, isr_count;          /* cycles of one audio interrupt (BLOCK samples or 1 sample) */
    unsigned long long isr_sum;
    unsigned bg_max, bg_count;            /* cycles of one Mode B background block (128 samples) */
    unsigned long long bg_sum;
    unsigned cpu_hz_est;                  /* TSCL cycles counted over 48 000 audio samples (= f_CPU) */
    unsigned rstat, xstat;                /* McASP status (error flags) */
} Prof;

extern Ha            g_ha;
extern volatile Prof g_prof;
extern volatile unsigned g_samples;       /* audio samples processed since start */

void io_start(void);                      /* codec, McASP, EDMA (or the per-sample fallback) */
void leds_init(void);
void led(int n, int on);                  /* n = 4, 5, 6 -> LED D4, D5, D6 */
int  buttons(void);                       /* bit 0 = S2 pressed, bit 1 = S3 pressed */
void stored_init(void);                   /* fill the stored test signal unless one was loaded */
extern Int32 g_stored[STORED_LEN];        /* stored input (16-bit samples in 32-bit words), DDR2 */
extern volatile int g_stored_loaded;      /* set to 1 in CCS after "Load Memory" of a speech file */

#endif
