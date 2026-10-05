/* PC test: runs every C block on the test vectors exported by python/export.py and compares
 * with Python's float64 results. The C code computes in float32, as on the board.
 *
 * Tolerances (max absolute error; signals in full-scale units, 1.0 = 0 dBFS):
 *   single blocks (HPF, own FFT, Goertzel)   1e-5, relative to max(1, peak of the reference)
 *   Mode A / Mode B alone and full chains     1e-4, relative to max(1, peak)  (research/06 T4.5 gate)
 * Mode B in the full chain is compared after removing its 2-block (256-sample) buffering delay.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ha.h"

static const char *dir = "test/vectors";
static int failures = 0;

static double *load(const char *name, long *n)
{
    char path[512];
    FILE *f;
    long bytes;
    double *v;
    snprintf(path, sizeof path, "%s/%s", dir, name);
    f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "cannot open %s (run python/export.py)\n", path); exit(2); }
    fseek(f, 0, SEEK_END); bytes = ftell(f); fseek(f, 0, SEEK_SET);
    v = malloc(bytes);
    if (fread(v, 1, bytes, f) != (size_t)bytes) { fprintf(stderr, "short read %s\n", path); exit(2); }
    fclose(f);
    *n = bytes / 8;
    return v;
}

/* compare float32 C output y (offset by 'lag' samples) with reference r; tolerance relative to max(1, peak) */
static void check(const char *what, const float *y, const double *r, long n, long lag, double tol)
{
    double e = 0, peak = 1;
    long i;
    for (i = 0; i + lag < n; i++) {
        double d = fabs(y[i + lag] - r[i]);
        if (d > e) e = d;
        if (fabs(r[i]) > peak) peak = fabs(r[i]);
    }
    printf("  %-34s max |C - Python| = %.2e  (peak %.2f, tolerance %.0e x %.2f) %s\n",
           what, e, peak, tol, peak, e <= tol * peak ? "PASS" : "FAIL");
    if (e > tol * peak) failures++;
}

int main(int argc, char **argv)
{
    long n, m, i, b;
    double *x = 0, *ref;
    float *xf, *y;
    static ModeA ma;
    static ModeB mb;
    static Ha ha;
    static Hpf hp;
    int p;

    if (argc > 1) dir = argv[1];
#ifdef USE_DSPLIB
    printf("FFT backend: TI DSPLIB natural-C reference (DSPF_sp_fftSPxSP_cn / ifftSPxSP_cn)\n");
#else
    printf("FFT backend: own radix-2 DIT (c/fft_own.c)\n");
#endif
    x = load("in.f64", &n);
    xf = malloc(n * sizeof(float));
    y = malloc((n + 512) * sizeof(float));
    for (i = 0; i < n; i++) xf[i] = (float)x[i];

    printf("Single blocks:\n");
    ref = load("hpf.f64", &m);
    hpf_init(&hp);
    for (i = 0; i < n; i++) y[i] = hpf_process(&hp, xf[i]);
    check("HPF (2 biquads, DF-II-T)", y, ref, n, 0, 1e-5);
    free(ref);

    {   /* own FFTs and the Mode B fft256 backend vs numpy/own reference */
        double *zi = load("fft_in.f64", &m), *zo = load("fft_out.f64", &m), e = 0, e2 = 0, e3 = 0, peak = 0;
        static float a[2 * HA_NFFT], c[2 * HA_NFFT], d[2 * HA_NFFT + 32], o[2 * HA_NFFT + 32];
        for (i = 0; i < 2 * HA_NFFT; i++) a[i] = c[i] = d[i] = (float)zi[i];
        fft_dit(a, HA_NFFT, 0);
        fft_dif(c, HA_NFFT, 0);
        fft256_init();
        fft256(d, o, 0);
        for (i = 0; i < 2 * HA_NFFT; i++) {
            if (fabs(zo[i]) > peak) peak = fabs(zo[i]);
            e = fmax(e, fabs(a[i] - zo[i])); e2 = fmax(e2, fabs(c[i] - zo[i])); e3 = fmax(e3, fabs(o[i] - zo[i]));
        }
        printf("  %-34s DIT %.2e, DIF %.2e, fft256 %.2e of peak %.1f  %s\n", "FFT-256 vs numpy", e / peak,
               e2 / peak, e3 / peak, peak, fmax(e, fmax(e2, e3)) / peak <= 1e-5 ? "PASS" : "FAIL");
        if (fmax(e, fmax(e2, e3)) / peak > 1e-5) failures++;
        /* inverse: ifft(fft(x)) = x */
        fft256(o, d, 1);
        e = 0;
        for (i = 0; i < 2 * HA_NFFT; i++) e = fmax(e, fabs(d[i] - zi[i]));
        printf("  %-34s max error %.2e  %s\n", "fft256 inverse round trip (1/N)", e, e <= 1e-5 ? "PASS" : "FAIL");
        if (e > 1e-5) failures++;
        free(zi); free(zo);
    }
    {
        double *g = load("goertzel_in.f64", &m), *go = load("goertzel_out.f64", &m), e = 0;
        static const int f[11] = {250, 375, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000};
        static float buf[4608];
        int t;
        for (t = 0; t < 11; t++) {
            for (i = 0; i < 4608; i++) buf[i] = (float)g[t * 4608 + i];
            e = fmax(e, fabs(goertzel(buf, 4608, f[t] * 4608 / HA_FS) - go[t]));
        }
        printf("  %-34s max error %.2e (amplitude 0.1)  %s\n", "Goertzel, 11 tones, N = 4608", e, e <= 1e-5 ? "PASS" : "FAIL");
        if (e > 1e-5) failures++;
        free(g); free(go);
    }

    printf("Processing modes alone (N3):\n");
    ref = load("modeA_N3.f64", &m);
    modeA_init(&ma, HA_GAIN[0]);
    for (i = 0; i < n; i++) y[i] = modeA_process(&ma, xf[i]);
    check("Mode A filter bank, per sample", y, ref, n, 0, 1e-4);
    free(ref);
    ref = load("modeB_N3.f64", &m);
    fft256_init();
    modeB_init(&mb, HA_H[0]);
    for (b = 0; b + HA_L <= n; b += HA_L) modeB_block(&mb, &xf[b], &y[b]);
    check("Mode B OLA, block arithmetic", y, ref, n, 0, 1e-4);
    free(ref);

    printf("Full chain (HPF -> mode -> limiter) through ha_process() in 4-sample blocks:\n");
    for (p = 0; p < HA_NPRESET; p++) {
        int mode;
        for (mode = 0; mode < 2; mode++) {
            char name[64], label[64];
            snprintf(name, sizeof name, "chain%c_%s.f64", mode ? 'B' : 'A', HA_PRESET_NAME[p]);
            ref = load(name, &m);
            ha_init(&ha, mode, 0);
            ha_set_preset(&ha, p);
            memset(y, 0, (n + 512) * sizeof(float));
            for (i = 0; i + 4 <= n + 256; i += 4) {           /* +256: flush Mode B's buffering delay */
                static const float zero[4] = {0, 0, 0, 0};
                ha_process(&ha, i + 4 <= n ? &xf[i] : zero, &y[i], 4);
                ha_background(&ha);                           /* background finishes within the block */
            }
            snprintf(label, sizeof label, "Mode %c, %s%s", mode ? 'B' : 'A', HA_PRESET_NAME[p],
                     mode ? " (delay 256 removed)" : "");
            check(label, y, ref, n, mode ? 2 * HA_L : 0, 1e-4);
            if (ha.overruns) { printf("    overruns: %u FAIL\n", ha.overruns); failures++; }
            if (p == 0) printf("    limiter clipped %u samples (loud 1 kHz segment)\n", ha.clips);
            free(ref);
        }
    }
    {   /* extras: noise suppression, and noise suppression + automatic feedback notch */
        double *x2 = load("in_x.f64", &m), *ev = 0;
        long n2 = m, nev;
        float *x2f = malloc(n2 * sizeof(float)), *y2 = malloc((n2 + 512) * sizeof(float));
        int extras;
        for (i = 0; i < n2; i++) x2f[i] = (float)x2[i];
        ev = load("notch_events.f64", &nev);
        printf("Extras (speech + noise 10 dB SNR + 2.5 kHz howl from 0.6 s), preset N3:\n");
        for (extras = 0; extras < 2; extras++) {
            int mode;
            for (mode = 0; mode < 2; mode++) {
                char name[64], label[80];
                long act = -1;
                snprintf(name, sizeof name, "chain%c_N3_%s.f64", mode ? 'B' : 'A', extras ? "extras" : "nr");
                ref = load(name, &m);
                ha_init(&ha, mode, 0);
                ha_set_nr(&ha, 1);
                if (extras) ha_set_notch_auto(&ha, 1);
                memset(y2, 0, (n2 + 512) * sizeof(float));
                for (i = 0; i + 4 <= n2 + 256; i += 4) {
                    static const float zero[4] = {0, 0, 0, 0};
                    int before = ha.nt.n;
                    ha_process(&ha, i + 4 <= n2 ? &x2f[i] : zero, &y2[i], 4);
                    ha_background(&ha);
                    /* a notch is activated at the block boundary after the chunk's last sample, so the
                     * first notched sample is the first sample of the next chunk */
                    if (ha.nt.n > before && act < 0) act = i + 4;
                }
                snprintf(label, sizeof label, "Mode %c, %s%s", mode ? 'B' : 'A', extras ? "NR + auto notch" : "NR",
                         mode ? " (delay 256 removed)" : "");
                check(label, y2, ref, n2, mode ? 2 * HA_L : 0, 1e-4);
                if (extras) {
                    int same = nev == 2 && act == (long)ev[0] && fabs(ha.hd.f[0] - ev[1]) < 0.1;
                    printf("    notch active from sample %ld at %.2f Hz (Python: %ld at %.2f Hz)  %s\n",
                           act, ha.hd.nn ? ha.hd.f[0] : 0.0, nev ? (long)ev[0] : -1, nev ? ev[1] : 0.0,
                           same ? "PASS" : "FAIL");
                    if (!same) failures++;
                }
                if (ha.overruns) { printf("    overruns: %u FAIL\n", ha.overruns); failures++; }
                free(ref);
            }
        }
        free(x2); free(ev); free(x2f); free(y2);
    }
    printf("\n%s: %d check(s) failed\n", failures ? "FAILED" : "ALL PASSED", failures);
    free(x); free(xf); free(y);
    return failures != 0;
}
