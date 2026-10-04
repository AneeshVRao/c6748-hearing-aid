/* PC check of ccs/hearing_aid/lab_modes.c: runs the lab experiments with TI's natural-C DSPLIB
 * references and checks the results (cycle counts read 0 on the PC; they are measured on the board). */
#include <math.h>
#include <stdio.h>
#include "ha.h"
#include "lab_modes.h"

static int fails;

static void ok(const char *what, int pass, double v)
{
    printf("  %-48s %12.3e  %s\n", what, v, pass ? "PASS" : "FAIL");
    if (!pass) fails++;
}

int main(void)
{
    static const char *bname[B_COUNT] = {"fir_gen (24 taps) vs plain C", "", "biquad vs plain C DF-II-T", "",
        "", "cfftr2_dit + bit reversal vs own FFT", "", "", "cfftr4_dif + digit reversal vs own FFT",
        "fftSPxSP vs own FFT", "ifftSPxSP(fftSPxSP(x)) vs x", "", "", "", "", ""};
    static const float lin[6] = {1, 3, 6, 9, 7, 4}, c4[4] = {8, 7, 6, 9};
    int i;
    double e;

    printf("LAB_ARITH:\n");
    lab_run(1);
    /* the sum (-1.78e9) needs 31 bits: int16/int32/double hold it exactly, float32's 24-bit mantissa cannot */
    ok("int16 MAC == int32 MAC == double MAC (exact)", g_lab.arith_result[0] == g_lab.arith_result[1] &&
       g_lab.arith_result[1] == g_lab.arith_result[3], g_lab.arith_result[0]);
    e = fabs(g_lab.arith_result[2] - g_lab.arith_result[3]) / fabs(g_lab.arith_result[3]);
    ok("float32 MAC: relative error (24-bit mantissa)", e > 0 && e < 1e-5, e);

    printf("LAB_CONV: x = 1 2 3 4, h = 1 1 1\n");
    lab_run(2);
    for (e = 0, i = 0; i < 6; i++) e = fmax(e, fabs(g_lab.conv_linear[i] - lin[i]));
    ok("linear convolution = 1 3 6 9 7 4", e < 1e-6, e);
    for (e = 0, i = 0; i < 4; i++) e = fmax(e, fabs(g_lab.conv_circ4[i] - c4[i]));
    ok("circular N=4 (aliased) = 8 7 6 9", e < 1e-5, e);
    for (e = 0, i = 0; i < 6; i++) e = fmax(e, fabs(g_lab.conv_circ6[i] - lin[i]));
    ok("circular N=6 via DFT = linear", e < 1e-5, e);

    printf("LAB_DFT: N = 256\n");
    lab_run(3);
    ok("own radix-2 FFT vs direct DFT (max |error|)", g_lab.dft_err[0] < 1e-3, g_lab.dft_err[0]);
    ok("DSPLIB fftSPxSP vs direct DFT", g_lab.dft_err[1] < 1e-3, g_lab.dft_err[1]);

    printf("LAB_BENCH: DSPLIB argument / twiddle / ordering checks\n");
    lab_run(4);
    for (i = 0; i < B_COUNT; i++)
        if (bname[i][0]) ok(bname[i], g_lab.bench_err[i] < 1e-3, g_lab.bench_err[i]);
    ok("cfftr2_dit -> icfftr2_dif round-trip gain (no 1/N: 256)", fabs(g_lab.icfftr2_gain - 256) < 0.01,
       g_lab.icfftr2_gain);
    printf("\n%s: %d failed\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails != 0;
}
