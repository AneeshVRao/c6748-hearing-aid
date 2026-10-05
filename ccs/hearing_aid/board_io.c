/* LCDK board I/O for the hearing aid.
 *
 * Default (IO_FIFO = 1): codec master in DSP mode, McASP0 slave, Read FIFO on (RNUMEVT 4),
 * Write FIFO off, EDMA3 events 0 (RX) and 1 (TX) into 4-sample ping-pong buffers, one EDMA
 * interrupt per block. All register values: research/hardware_notes.md section 1.4.
 * The book's support file (third_party/rt-dsp/LCDK6748_Support_DSP.c) still does pin-mux, PSC,
 * I2C and the codec; only the McASP set-up is ours, because the FIFO must be enabled while the
 * McASP is in reset and the FIFO is reachable only through the DMA port (TRM p. 1107, 1160).
 *
 * Fallback (IO_FIFO = 0): the book's DSP_Init() unchanged, one McASP interrupt per sample.
 */
#include <c6x.h>
#include <math.h>
#include "board_io.h"

void wait(Uint32 delay);                            /* defined in the book support file, */
void Config_LCDK6748(void);                         /* not declared in its header */

Ha            g_ha;
volatile Prof g_prof;
volatile unsigned g_samples;

#pragma DATA_SECTION(g_stored, ".ddr")
Int32 g_stored[STORED_LEN];
volatile int g_stored_loaded = 0;
#if IO_MODE == IO_STORED_LINEOUT
static unsigned stored_pos;
#endif

/* ---------------------------------------------------------------- McASP / EDMA addresses */
#define MCASP_DMA_PORT  0x01D02000u                       /* RBUF/XBUF through the DMA port */
#define RFIFOCTL        (*(volatile Uint32 *)0x01D01018u) /* AFIFO base 0x01D01000 + 18h */
#define RFIFOCTL_CFG    0x00000401u                       /* RNUMEVT = 4 words, RNUMDMA = 1 */
#define RFIFOCTL_RENA   0x00010000u
#define DSP_PORT_FMT    0x000080F0u                       /* as S19's 0x80F8 but RBUSEL/XBUSEL = 0 */

/* PaRAM sets: 0 = RX channel, 1 = TX channel, 64/65 = RX ping/pong reloads, 66/67 = TX reloads */
#define OPT_RX  0x00100004u     /* TCINTEN (bit 20), TCC 0, SYNCDIM = AB-synchronised (bit 2) */
#define OPT_TX  0x00001000u     /* TCC 1, A-synchronised, no interrupt */

#pragma DATA_ALIGN(rx, 8)
#pragma DATA_ALIGN(tx, 8)
static volatile Uint32 rx[2][BLOCK], tx[2][BLOCK];     /* shared with the EDMA */
static volatile int rx_idx;

#if IO_FIFO
static void param(int set, Uint32 opt, Uint32 src, Uint32 dst, Uint32 bidx, int link)
{
    EDMA_params *p = (EDMA_params *)EDMA3_0_PARAM(set);
    p->option = opt;
    p->source = src;
    p->a_b_count = (BLOCK << 16) | 4;               /* BCNT = 4 arrays of ACNT = 4 bytes */
    p->dest = dst;
    p->src_dest_b_index = bidx;                     /* (DSTBIDX << 16) | SRCBIDX */
    p->link_reload = (BLOCK << 16) | (EDMA3_0_PARAM(link) & 0xFFFF);   /* BCNTRLD | LINK */
    p->src_dest_c_index = 0;
    p->c_count = 1;
}

static void edma_init(void)
{
    /* RX: 4 words from the FIFO per event (AB-sync), into rx[0], rx[1], rx[0], ... */
    param(0,  OPT_RX, MCASP_DMA_PORT, (Uint32)rx[0], 4u << 16, 64);
    param(64, OPT_RX, MCASP_DMA_PORT, (Uint32)rx[1], 4u << 16, 65);
    param(65, OPT_RX, MCASP_DMA_PORT, (Uint32)rx[0], 4u << 16, 64);
    /* TX: one word per event (A-sync, Write FIFO off), from tx[0], tx[1], tx[0], ... */
    param(1,  OPT_TX, (Uint32)tx[0], MCASP_DMA_PORT, 4u, 67);
    param(66, OPT_TX, (Uint32)tx[0], MCASP_DMA_PORT, 4u, 67);
    param(67, OPT_TX, (Uint32)tx[1], MCASP_DMA_PORT, 4u, 66);
    *(volatile Uint32 *)EDMA3_0_CC_ECR   = 3;       /* clear pending events 0, 1 */
    *(volatile Uint32 *)EDMA3_0_CC_EESR  = 3;       /* enable events 0, 1 */
    *(volatile Uint32 *)EDMA3_0_CC_DRAE1 = 3;       /* events 0, 1 in shadow region 1 (EDMA3_CC0_INT1) */
    *(volatile Uint32 *)EDMA3_0_CC_IESR  = 1;       /* interrupt on TCC 0 (RX block complete) */
}

static void mcasp0_init_fifo(void)
{
    McASP *m = McASP0_Base;
    m->gblctl = 0; m->rgblctl = 0; m->xgblctl = 0;
    m->srctl[13] = 0; m->srctl[14] = 0;
    RFIFOCTL = RFIFOCTL_CFG;                        /* Read FIFO: configure, then enable, while in reset */
    RFIFOCTL = RFIFOCTL_CFG | RFIFOCTL_RENA;
    wait(10000);
    /* receiver and transmitter: as S19 (burst, external clocks and frame sync, 1 slot) but DMA port */
    m->rmask = 0xFFFFFFFF; m->rfmt = DSP_PORT_FMT; m->afsrctl = 0; m->aclkrctl = 0; m->ahclkrctl = 0;
    m->rtdm = 1; m->rintctl = 0x01; m->rclkchk = 0x00FF0008;
    m->xmask = 0xFFFFFFFF; m->xfmt = DSP_PORT_FMT; m->afsxctl = 0; m->aclkxctl = 0; m->ahclkxctl = 0;
    m->xtdm = 1; m->xintctl = 0x00; m->xclkchk = 0x00FF0008;   /* no CPU data interrupt: EDMA serves it */
    m->srctl[13] = 0x0D;                            /* AXR13 transmit -> codec DIN */
    m->srctl[14] = 0x0E;                            /* AXR14 receive  <- codec DOUT */
    m->pfunc = 0; m->pdir = 0x00002000;
    m->ditctl = 0; m->dlbctl = 0; m->amute = 0;
    m->rgblctl |= GBLCTL_RCLKRST; while (!(m->rgblctl & GBLCTL_RCLKRST));
    m->xgblctl |= GBLCTL_XCLKRST; while (!(m->xgblctl & GBLCTL_XCLKRST));
    m->xstat = 0xFFFF; m->rstat = 0xFFFF;
    m->rgblctl |= GBLCTL_RSRCLR; while (!(m->rgblctl & GBLCTL_RSRCLR));
    m->xgblctl |= GBLCTL_XSRCLR; while (!(m->xgblctl & GBLCTL_XSRCLR));
    m->rgblctl |= GBLCTL_RSMRST; while (!(m->rgblctl & GBLCTL_RSMRST));
    m->xgblctl |= GBLCTL_XSMRST; while (!(m->xgblctl & GBLCTL_XSMRST));
    *(volatile Uint32 *)MCASP_DMA_PORT = 0;         /* prevent an initial underrun (DMA port, XBUSEL = 0) */
    m->rgblctl |= GBLCTL_RFRST; while (!(m->rgblctl & GBLCTL_RFRST));
    m->xgblctl |= GBLCTL_XFRST; while (!(m->xgblctl & GBLCTL_XFRST));
}
#endif

/* ---------------------------------------------------------------- sample conversion */
#if IO_MODE != IO_STORED_LINEOUT
static inline float in_sample(Uint32 w)
{
#if INPUT_SEL == 0
    return (float)(Int16)(w & 0xFFFF) * (1.0f / 32768.0f);
#elif INPUT_SEL == 1
    return (float)(Int16)(w >> 16) * (1.0f / 32768.0f);
#else
    return ((float)(Int16)(w & 0xFFFF) + (float)(Int16)(w >> 16)) * (0.5f / 32768.0f);
#endif
}
#endif

static inline Uint32 out_word(float y)
{
    Int32 s = _spint(y * 32768.0f);              /* round to nearest; |y| <= limiter ceiling, no overflow */
    Uint32 h = (Uint32)(Uint16)(Int16)s;
    return (h << 16) | h;                           /* same sample on left and right */
}

static inline void prof_isr(unsigned c)
{
    if (c > g_prof.isr_max) g_prof.isr_max = c;
    g_prof.isr_sum += c;
    g_prof.isr_count++;
}

static unsigned clk_t0;
static inline void clock_check(int n)
{
    unsigned s = g_samples;
    g_samples = s + n;
    if (s == 0) clk_t0 = TSCL;
    else if (s < 48000 && s + n >= 48000) g_prof.cpu_hz_est = TSCL - clk_t0;   /* 1 s of audio */
}

#define GPIO_D6_ON()  (GPIO_SET_DATA23 = 0x00001000)  /* LED D6 = GP2[12]: CPU-busy scope pin */
#define GPIO_D6_OFF() (GPIO_CLR_DATA23 = 0x00001000)

/* ---------------------------------------------------------------- interrupts */
interrupt void edma_isr(void)
{
    float in[BLOCK], out[BLOCK];
    unsigned t0 = TSCL;
    int i, k = rx_idx;
    GPIO_D6_ON();
    *(volatile Uint32 *)EDMA3_0_CC_ICR = 1;         /* clear TCC 0 */
    rx_idx = k ^ 1;
    for (i = 0; i < BLOCK; i++) {
#if IO_MODE == IO_STORED_LINEOUT
        in[i] = (float)g_stored[stored_pos] * (1.0f / 32768.0f);
        if (++stored_pos == STORED_LEN) stored_pos = 0;
#else
        in[i] = in_sample(rx[k][i]);
#endif
    }
#if PASSTHROUGH
    for (i = 0; i < BLOCK; i++) out[i] = in[i];
#else
    ha_process(&g_ha, in, out, BLOCK);
#endif
    for (i = 0; i < BLOCK; i++) tx[k][i] = out_word(out[i]);
    clock_check(BLOCK);
    prof_isr(TSCL - t0);
    GPIO_D6_OFF();
}

interrupt void mcasp_isr(void)                      /* fallback: one sample per interrupt (book path) */
{
    float in, out;
    unsigned t0 = TSCL;
    GPIO_D6_ON();
    if (CheckForOverrun()) { GPIO_D6_OFF(); return; }
#if IO_MODE == IO_STORED_LINEOUT
    (void)ReadCodecData();
    in = (float)g_stored[stored_pos] * (1.0f / 32768.0f);
    if (++stored_pos == STORED_LEN) stored_pos = 0;
#else
    in = in_sample(ReadCodecData());
#endif
#if PASSTHROUGH
    out = in;
#else
    ha_process(&g_ha, &in, &out, 1);
#endif
    WriteCodecData(out_word(out));
    clock_check(1);
    prof_isr(TSCL - t0);
    GPIO_D6_OFF();
}

/* ---------------------------------------------------------------- start-up */
void io_start(void)
{
#if IO_FIFO
    edma_init();                                    /* EDMA ready before the McASP raises events */
    Config_LCDK6748();                              /* book: pin-mux McASP0/I2C0, McASP power-up */
    Init_Interrupts_EDMA();                         /* book: ISTP = vector table in L2 */
    Init_I2C();
    if (!Init_AIC3106(SampleRateSetting))
        for (;;) ;                                  /* codec did not answer on I2C */
    mcasp0_init_fifo();
    EnableInterrupts_EDMA();                        /* book: INT8 (EDMA3_CC0_INT1), GIE */
#else
    DSP_Init();                                     /* book: per-sample McASP interrupt, FIFO off */
#endif
}

/* ---------------------------------------------------------------- LEDs and buttons */
void leds_init(void)
{
    /* pin-mux: GP6[13] (D4) and GP6[12] (D5) = PINMUX13[15:8] = 88h; GP2[12] (D6) = PINMUX5[15:12] = 8h
     * (TRM p. 247, 230). D7 stays AMUTE (set by Config_LCDK6748). Buttons need no pin-mux. */
    PINMUX13 = (PINMUX13 & ~0x0000FF00u) | 0x00008800u;
    PINMUX5  = (PINMUX5  & ~0x0000F000u) | 0x00008000u;
    GPIO_CLR_DATA67 = 0x00003000; GPIO_DIR67 &= ~0x00003000u;
    GPIO_CLR_DATA23 = 0x00001000; GPIO_DIR23 &= ~0x00001000u;
}

void led(int n, int on)
{
    if (n == 4)      { if (on) GPIO_SET_DATA67 = 0x2000; else GPIO_CLR_DATA67 = 0x2000; }
    else if (n == 5) { if (on) GPIO_SET_DATA67 = 0x1000; else GPIO_CLR_DATA67 = 0x1000; }
    else if (n == 6) { if (on) GPIO_SET_DATA23 = 0x1000; else GPIO_CLR_DATA23 = 0x1000; }
}

int buttons(void)
{
    Uint32 v = GPIO_IN_DATA23;                       /* S2 = GP2[4], S3 = GP2[5], low when pressed */
    return (int)((~v >> 4) & 3u);
}

#if STORED_SPEECH
extern const short HA_SPEECH[STORED_LEN];         /* speech_clip.c, generated by python/export.py */
volatile float g_stored_snr_db = 99.0f;            /* set below 60 in CCS (at main) to add white noise */
#endif

/* default stored signal: the 11 audiometric tones at -40 dBFS RMS, 8000 samples each, then noise.
 * STORED_SPEECH builds: 2 s of built-in speech instead, plus optional white noise at g_stored_snr_db. */
void stored_init(void)
{
    unsigned seed = 12345u;
    int i;
    if (g_stored_loaded) return;
#if STORED_SPEECH
    for (i = 0; i < STORED_LEN; i++) {
        Int32 v = HA_SPEECH[i];
        if (g_stored_snr_db < 60.0f) {              /* uniform noise, RMS = speech RMS (-40 dBFS) / SNR */
            seed = seed * 1664525u + 1013904223u;
            v += (Int32)((float)((Int32)(seed >> 16) - 32768) * (327.7f / 18918.0f) *
                         powf(10.0f, -g_stored_snr_db / 20.0f));
        }
        g_stored[i] = v;
    }
#else
    static const float f[11] = {250, 375, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000};
    int t;
    for (t = 0; t < 11; t++)
        for (i = 0; i < 8000; i++)
            g_stored[t * 8000 + i] = _spint(32768.0f * 0.01414214f *
                                     sinf(6.2831853f * f[t] * (float)i / 48000.0f));
    for (i = 88000; i < STORED_LEN; i++) {          /* uniform noise, -40 dBFS RMS */
        seed = seed * 1664525u + 1013904223u;
        g_stored[i] = (Int32)((Int32)(seed >> 16) - 32768) * 328 / 18918;
    }
#endif
}
