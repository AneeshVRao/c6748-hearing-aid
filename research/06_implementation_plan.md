# 06 – Implementation Plan (Step 7)

The work runs in four stages, each with a pass/fail gate:

**MATLAB prototype → fixed vs floating point check → C on CCS → real-time test on the board.**

Labels are the same as in the other files: [Sx], DESIGN CHOICE, ASSUMPTION.

---

## Stage 1 – MATLAB prototype

**Goal.** Reproduce every number in `05_system_design.md` in MATLAB, and produce the reference outputs (test vectors) that the C code must match.

| Step | What to do | MATLAB functions | Pass gate |
|---|---|---|---|
| 1.1 | Design G and F | `fir1(20,0.25,kaiser(21,4.5))`, `fir1(30,0.5,kaiser(31,4.5))`, `freqz`, `zplane` | Stopband ≥ 50 dB (Python gave 52.5 / 51.1 dB) |
| 1.2 | Mode A tree, sample-accurate (port `calc/design_check.py`, function `analyse_synth`) | `filter`, indexing `x(1:2:end)`, `upsample` | Impulse peak at n = 375, ripple < 0.05 dB with unity gains |
| 1.3 | Gain table, tone test | `sin`, `fft`, `goertzel` | Gains within 0.5 dB of §6 table |
| 1.4 | HPF | `butter(4,100/24000,'high')`, `tf2sos` | −3 dB at 100 Hz |
| 1.5 | Mode B: frequency-sampling FIR + OLA | Own frequency-sampling formula (04 §10), `fft`/`ifft`, OLA loop; check with `fftfilt` | OLA output = `filter(h,1,x)` to < 1e-6 |
| 1.6 | OLS variant | Own loop | Same output as OLA |
| 1.7 | Comparison studies | `czt`, `tf2latc`, `residuez`, impulse invariance (`impinvar`), matched-z by hand, radix-2/4 own FFT in a `.m` file | Plots for report |
| 1.8 | Rational resampling of test speech | `resample(x,160,147)` | Plays correctly at 48 kHz |
| 1.9 | Export | `fprintf` coefficient `.h` files, binary test vectors | Files ready for CCS |

Claude Code writes these scripts. The team runs them in MATLAB and checks the gates.

## Stage 2 – Fixed vs floating point check (MATLAB)

| Check | Method | What to report |
|---|---|---|
| Coefficient quantisation | Round G, F and the HPF to Q15 (`round(h*32768)/32768`) and re-plot the responses | Stopband change; for HPF biquads, pole movement (direct form vs cascade) |
| Data path overflow | Q15 input at −20, −30, −40 dBFS through 30 dB gain | Clip count; shows why ≥ 5 bits of headroom are needed |
| SNR float vs Q15 | Same speech file, compare outputs | SNR in dB per mode |
| Decision | C674x has hardware float [S8], so the board build uses **float** (DESIGN CHOICE). A Q15 build is optional | — |

## Stage 3 – C code on CCS

### 3.1 Starting point (pick one, in this order)

1. **S19 package (saved: `papers/code_2017_02_05.zip`, unzipped to `papers/S19_code_2017_02_05/`).** Use the files in `code/common_code/LCDK/` (`AIC3106.h`, `DSP_Config.h`, `LCDK_Support_DSP.h`, `OMAPL138_defines.h`, `link6748e.cmd`, `vectors_EDMA.asm`), the GEL/target files in `code/target_configuration/LCDK/`, and the EDMA example `code/chapter_06/ccs/Frame_EDMA_6748/` as the project template.
   - **Replace** the package's `LCDK_Support_DSP.c` with **`papers/LCDK6748_Support_DSP.c`** (saved in Update 6). Only it has `Config_LCDK6748()` (McASP/I2C pin-mux + McASP power-up); the rest is identical. Swap steps: `research/hardware_notes.md` §10.
   - It runs the codec as master in DSP mode on I2C0 (0x18) with AXR13/AXR14. All of this matches the schematic (§8, §9).
   - **Use `DSP_Init_EDMA()`**, then add: Read FIFO set-up, DMA-port access and 4-word RX events (below).
2. **Processor SDK: not needed** (your decision). Everything planned from it (GEL file, register defines) is in the S19 package (§9).

First milestone: **audio loopback** (line in → line out) with no processing. Do not write DSP code until this works.

**Codec and McASP checklist** (full detail with citations in `research/hardware_notes.md` §1.3–1.4):

- AIC3106 at I2C address 0x18 [S13 Table 10-7].
- Registers 2, 3, 7, 8, 9, 15/16, 19/22, 37, 43/44, 82/92, 86/93, 101, 102 (values in `research/hardware_notes.md` §1.3; all confirmed in `LCDK_Support_DSP.c` `Init_AIC3106()` lines 430–524 and `AIC3106.h` lines 128–129).
- Follow the McASP 10-step initialisation order with GBLCTL read-back [S14 §2.4.1.2, §2.4.1.4].
- Framing as in S19: codec master (reg 8 = 0xF0), DSP mode 16-bit (reg 9 = 0x40); McASP slave, burst, 32-bit slot, 0 delay (XFMT = RFMT = 0x80F8). Line in on regs 19/22 = 0x04; line out on regs 82/92 = 0x80 and 86/93 = 0x09; 48 kHz with the PLL off (reg 3 = 0x20, Q = 4, MCLK 24.576 MHz) — see `research/hardware_notes.md` §1.3.
- **AFIFO (DEFAULT): Read FIFO ON** – write RFIFOCTL (0x01D0 1018) = 0x0000 0401, then 0x0001 0401, **before taking the McASP out of reset**, i.e. right after `GBLCTL = 0` in `Init_McASP0()` [TRM Table 23-49, p. 1160]. **Write FIFO OFF** (WFIFOCTL at reset). Service with EDMA events 0/1 into 4-sample ping-pong blocks [TRM Table 23-6, p. 1103].
- **McASP data port (required with the FIFO):** RFMT = XFMT = **0x0000 80F0** (RBUSEL/XBUSEL = 0) instead of S19's 0x0000 80F8; EDMA source/destination **0x01D0 2000**. "Only the DMA port has access to the AFIFO" [TRM Table 23-9 note, p. 1107].
- **EDMA PaRAM (values from the TRM, `research/hardware_notes.md` §1.4):** RX: OPT 0x0010 0004 (AB-sync, interrupt, TCC 0), ACNT 4, BCNT 4, SRCBIDX 0, DSTBIDX 4, CCNT 1, linked ping/pong. TX: OPT 0x0000 1000 (A-sync, TCC 1), ACNT 4, BCNT 4, SRCBIDX 4, DSTBIDX 0, CCNT 1, linked [TRM §16.2.2, p. 554–555; Table 16-15, p. 611–612; Figure 16-7, p. 556]. Interrupt only on RX completion, as S19 does (`ISRs.c` line 45).
- **LED pin-mux (add to init):** `PINMUX13 = (PINMUX13 & ~0x0000FF00) | 0x00008800;` (D4, D5) and `PINMUX5 = (PINMUX5 & ~0x0000F000) | 0x00008000;` (D6) [TRM p. 247, 230]. D4 = mode, D5 = clip + preset blink count, D6 = CPU-busy pin, D7 = AMUTE (DECIDED).
- Use EDMA events 0 (RX) and 1 (TX) [S8 Table 6-12] with an EDMA completion interrupt. MCASP0_INT (event 61 [S8 Table 6-6]) is used only for overrun/underrun errors.
- Do not open XBUF/RBUF in a CCS memory window [S14 p. 36].
- Codec register bytes: copy them from S19. They were checked against the schematic (S12) in Update 4 and line by line against the package in Update 5.
- **Board step 0 (before any audio):** confirm the CPU clock. Use TI's target **LCDK C6748** (GEL `C6748_LCDK.gel`, sets 300 MHz). Read PLLC0 PLLCTL/PLLM/PREDIV/PLLDIV1/POSTDIV (0x01C1 1100/1110/1114/1118/1128) and compute f = 24 MHz × (PLLM+1)/((PREDIV+1)(POSTDIV+1)(PLLDIV1+1)); expect 300 MHz [TRM §7.3, p. 137–152]. Cross-check with TSCL over 48 000 samples. (The Update 5 "GEL bug" was a misreading and is retracted, `research/hardware_notes.md` §1.7.)

### 3.2 Code structure (DESIGN CHOICE)

```
/src
  main.c            – init (+ LED pin-mux), button S2/S3 polling (GPIO2[4]/[5]), LEDs D4/D5/D6, ifft scale self-check, IO_MODE switch (live / stored→LINE OUT / internal), background loop (Mode B FFT)
  codec_io.c        – from S19 DSP_Init_EDMA() + Read FIFO set-up (Write FIFO off): EDMA 4-sample ping-pong blocks (both modes), Mode B 128-sample software buffer
  hpf.c             – 2 biquads in plain C (DF-I, DF-II, DF-II-T versions, #ifdef); DSPF_sp_biquad only in benchmark (nx multiple of 3)
  modeA_bank.c      – 4-level tree, per sample, plain C; power-of-2 circular buffers (G/F 32 floats, align 512/256/128/16)
  modeB_ola.c       – FFT-256 OLA, H[k] table
  fft_own.c         – our radix-2 DIT (learning + comparison)
  goertzel.c        – 11-bin tone meter
  wdrc.c            – optional
  limiter.c         – hard/soft clip (MPO)
  profile.c         – cycle counter helpers
/include coeffs_G.h coeffs_F.h coeffs_hpf.h Hk_modeB.h (exported from MATLAB)
/test   vectors from MATLAB + compare routine
```

### 3.3 TI library functions [S15][S16]

| Function | Used for | Notes |
|---|---|---|
| `DSPF_sp_fftSPxSP` / `DSPF_sp_ifftSPxSP` (**C674x DSPLIB 3.4.0.0**) | **Mode B** forward/inverse FFT-256 (the only DSPLIB calls in the real-time path) | **1965 / 1985 cycles** (C674x TestReport). N = 256, n_min = 4, offset = 0, n_max = 256. Twiddles: `tw_gen()` and `brev[64]` from `DSPF_sp_fftSPxSP_d.c`. x/w/y 8-byte aligned, no overlap. ifft output scaled by 1/N (`_cn.c` line 167; our gcc round-trip test). Interrupt-tolerant (no Rev 2.0 bug) |
| `DSPF_sp_fir_gen` (C674x) | Benchmark only (T11) | **nh and nr multiples of 4** (pad G 21 → 24 with zeros), double-word aligned, reverse-order coefficients, interruptible. 10/16·Nr·Nh + 55 → 775 cycles (nh 24, nr 48) |
| `DSPF_sp_fircirc` | Circular-addressing demo (optional) | Buffer 2^(csize+1) bytes, aligned; nh even (pad G to 22 taps with a zero), nr multiple of 4. (2nh+10)·nr/4+18 [S15 p. 4-45] |
| `DSPF_sp_biquad` (C674x) | Benchmark only | nx ≥ 2, interruptible; 8·Nx + 72 → 456 cycles at nx = 48. HPF stays plain C |
| `DSPF_sp_dotprod` | Optional alternative inner loop for G | nx/2+25 [S15 p. 4-54] |
| `DSPF_sp_cfftr2_dit` + `DSPF_sp_bitrev_cplx` | Radix-2 comparison | 4138 + 666 cycles [S15 p. 4-16, 4-8] |
| `DSPF_sp_cfftr4_dif` | Radix-4 comparison | 3696 cycles; output digit-reversed [S15 p. 4-12] |
| `DSPF_sp_icfftr2_dif` | DIF inverse comparison | **Input bit-reversed, output normal** [S15 p. 4-34], so it chains directly after cfftr2_dit. 4133 cycles [S15 p. 4-38] |

**Library in use (Update 6, PROPOSED CHANGE – confirm, forced by the tools):** **C674x DSPLIB 3.4.0.0**, already installed at `C:\ti\dsplib_c674x_3_4_0_0`. The C67x v2.00 you installed (`C:\CCStudio\c6700\dsplib\lib\dsp67x.lib`) is COFF, and the only installed compiler (CGT 8.1.3) links ELF only (its README, line 112). **CCS settings:** include path `C:\ti\dsplib_c674x_3_4_0_0\packages` with `#include <ti/dsplib/dsplib.h>`; linker search path `C:\ti\dsplib_c674x_3_4_0_0\packages\ti\dsplib\lib`, library `dsplib.ae674` (`research/hardware_notes.md` §3.3). The cfftr2/cfftr4/icfftr2 comparison rows above use C67x formulas; re-read their C674x headers before the benchmark.

### 3.4 Memory plan (sizes calculated in `calc/design_check_output.txt`)

| Data | Size | Where | Why |
|---|---|---|---|
| Code | < 64 KB (ASSUMPTION) | L2 RAM (0x1180 0000) [S8] | Fast; L1P caches it |
| G, F, HPF coefficients | < 1 KB | L2 | Read every sample |
| Mode A circular buffers, power-of-2 sizes (512 + 256 + 128 + 16 alignment + 4 × 2 × 32 G/F lines = 1168 floats) | ≈ 4.7 KB | L2 | Read every sample; power-of-2 needed for circular addressing [S9 §3.9.2] |
| Mode B buffers (x 512+16 pad, y 512, overlap 128, twiddles 512, H[k] 512 floats) | ≈ 8.8 KB | L2 | FFT working set |
| Ping-pong audio buffers | < 2 KB | L2 (or shared RAM 0x8000 0000) | EDMA target |
| Test capture (10 s, float) | 1.92 MB | **DDR2** (0xC000 0000; 128 MB on LCDK [S8][S11]) | Too big for internal memory |

Cache: keep L1P and L1D as cache (DESIGN CHOICE). Do not put DDR2 buffers inside the real-time loop.

### 3.5 Measuring cycle counts

1. **CCS profile clock** (Run → Clock → Enable): count cycles between two breakpoints. This is good for single function calls, but it needs the board halted, so it is not usable in real time.
2. **Time-stamp counter**: TSCL/TSCH is a 64-bit counter of CPU clocks. It is off after reset, and **any write to TSCL starts it** [S9 §2.9.14, p. 55–56]. Write once at start-up, then read `TSCL` before and after each function (`t0 = TSCL; …; cyc = TSCL − t0;`). The TI compiler normally exposes TSCL through `c6x.h` (check the compiler docs).
3. **GPIO toggle + oscilloscope**: drive LED D6 (GPIO2[12]) high on block-ISR entry and low on exit; the duty cycle is the CPU load. Needs the PINMUX5 line above [TRM p. 230].
4. **CPU load** = (cycles per frame) / (frame period × f_clk). Example: Mode B frame work is 12,746 / (2.667 ms × 456 MHz) = 1.05 % (`calc/cpu_check_output.txt`).
5. Measure at `-o0` and `-o3` to show the effect of software pipelining (syllabus: pipelining).
6. Read the actual CPU clock (board step 0 above) so the load percentages use the true value.

### 3.6 I/O modes, including "no external input" fallbacks (DESIGN CHOICE, Update 6)

One compile-time switch, `#define IO_MODE`, with live audio as the default. Full table: `research/hardware_notes.md` §11.

| `IO_MODE` | Input → output | Use it when | Real-time proof |
|---|---|---|---|
| `IO_LIVE` (**default**) | LINE IN → Read FIFO/EDMA → DSP → EDMA → LINE OUT | Normal operation and the demo | Clean audio, no McASP error flags, T5, TSCL |
| `IO_STORED_LINEOUT` | Stored test signal in DDR2 → DSP → EDMA → codec → LINE OUT | No signal source available; repeatable listening tests | Codec clock still paces the output; no XSTAT underrun; TSCL per block |
| `IO_INTERNAL` | Stored vector in DDR2 → DSP → output array in DDR2; inspect with the CCS graph tool, save with *Save Memory* and compare with MATLAB | Before codec bring-up, or with no codec/speakers at all | **Cycle count:** worst TSCL cycles per 4-sample block < 25 000 at 300 MHz (6250 per sample); output matches MATLAB < 1e-4 |

## Stage 4 – Real-time test on the board

| Order | Milestone | Pass gate |
|---|---|---|
| 4.1 | Loopback at 48 kHz | Clean audio, no clicks (watch for McASP underrun flags [S14]) |
| 4.2 | HPF only | DC removed; 1 kHz tone unchanged |
| 4.3 | Mode A with unity gains | Output = input delayed ≈ 375 samples + codec |
| 4.4 | Mode A with gain table | Tone gains match §6 within 1 dB |
| 4.5 | Mode B | Matches MATLAB to < 1e-4 (float) on the test vector |
| 4.6 | Limiter + mode switch | No overflow at full-scale input |
| 4.7 | Profiling, FFT comparison | Table of cycles and load |
| 4.8 | Optional: WDRC, minimum-phase, 6th band | — |

## Tools checklist

- **Emulator.** The LCDK has **no onboard emulator**; use the 14-pin JTAG header [S11 §1.1]. Listed emulators are XDS100, XDS200, XDS510, XDS560, and XDS110 (C6748 LCDK only) [S11 Table 2]. **Arrange this in Week 1.**
- CCS 7.2 with CGT C6000 8.1.3 (installed), C674x DSPLIB 3.4.0.0 (installed). Emulator from the lab.
- MATLAB with Signal Processing Toolbox.
- A stereo audio interface or sound card, 3.5 mm cables, **powered speakers or a headphone amplifier** (from the lab; LINE OUT cannot drive headphones), an oscilloscope (for latency and GPIO).
