# Board results (measured on the LCDK C6748)

Raw readings from the board, in checklist order. Phase 4 analyses them.

## Smoke test, step 3: CPU clock (8 Oct 2026)

| Register | Address | Value | Meaning |
|---|---|---|---|
| PLLCTL | `0x01C11100` | `0x00000049` | bit 0 = 1: PLL on (not bypassed) |
| PLLM | `0x01C11110` | `0x18` | × (24 + 1) = 25 |
| PREDIV | `0x01C11114` | `0x8000` | ÷ 1 |
| PLLDIV1 | `0x01C11118` | `0x8000` | ÷ 1 (CPU) |
| POSTDIV | `0x01C11128` | `0x8001` | ÷ 2 |
| PLLDIV2 | — | `0x01` | ÷ 2 → 150 MHz |
| PLLDIV3 | — | `0x0B` | ÷ 12 → 25 MHz (EMIFA) |

Bit 15 of each divider is its enable flag; the ratio is the low bits + 1.

**CPU clock = 24 MHz × 25 / (1 × 2 × 1) = 300 MHz.** This matches the GEL and the design value (TRM Tables 7-8, 7-12). The independent TSCL check (`g_prof.cpu_hz_est`) comes in checklist step 2.

## Smoke test, step 4: stock loopback

Done (book `Frame_EDMA_6748`).

## Checklist step 0: DIP SW1-5 and SW1-6 OFF

Done.

## Checklist step 2: `loop_fallback.out` (15 Oct 2026, run headless with `tools/dss_run.js`)

| Reading | Value | Verdict |
|---|---|---|
| Audio (1 kHz test tone, PC → LINE IN → LINE OUT) | **not verified**: see "Audio path" below | — |
| `g_prof.isr_max` | 213 cycles (of 6250 per sample) | pass |
| `g_prof.rstat` / `xstat` | 0 / 0 | pass |
| `g_prof.cpu_hz_est` (old build) | 302 767 578 | **fail**: start-up artefact, see C27 |
| `g_prof.cpu_hz_est` (fixed build) | 300 001 218 | pass (+0.0004 %) |
| ΔTSCL / Δt, two runs 10 s apart (PC timer) | 300.20 / 299.89 MHz | pass (PC timing ±0.1 %) |
| Δsamples / ΔTSCL | 6250.0 cycles per sample, both runs | 300 MHz / 48 kHz exactly |

## Checklist steps 3 and 5: `loop_fifo.out`

| Reading | Value | Verdict |
|---|---|---|
| `g_prof.isr_count` vs `g_samples` | 142 556 × 4 = 570 224 | pass (one interrupt per 4 samples) |
| `g_prof.isr_max` | 104 cycles | pass |
| `g_prof.cpu_hz_est` | 300 001 282 | pass |
| RFIFOCTL `0x01D01018` | `0x00010401` | pass |
| RFIFOSTS `0x01D0101C` | 1 | pass (0–4) |
| `g_prof.rstat` | 0 | pass |
| `g_prof.xstat` | `0x180` (XDMAERR + XERR) at start-up | **fixed** (C28): now 0 |
| `g_ifft_gain` (step 5) | 1.0 | pass |
| Start-up after a power cycle | audio never started | **fixed** (C29): 3 of 3 starts, 48 kHz, XSTAT = RSTAT = 0 |
| Audio | **not verified**: see "Audio path" below | — |

## Audio path check (15 Oct 2026)

Board input captured with `live.out` (howl-detector buffer, 128 samples) while the PC played a 1 kHz tone at −26 dBFS:

| Condition | Input RMS | 1 kHz component |
|---|---|---|
| PC silent | −72.0 dBFS | −101.2 dBFS |
| PC playing 1 kHz | −73.2 dBFS | −113.8 dBFS |

**In this capture no PC signal reached LINE IN.** The user reports that audio *sometimes* reaches the board, so the PC → LINE IN connection is intermittent, not dead. During this capture the tone was coming from the laptop's own speakers: Windows shows only "Speakers (Realtek)", with no headphone or line-in endpoint. The −72 dBFS idle level is hum or pickup on an open input. Everything below that needs audio input is therefore **not yet verified**. The CPU-load figures are unaffected: Mode A/B cycle counts do not depend on the signal (no data-dependent branches except the limiter, which did not act).

## Step 6: `internal.out` (no codec) — PASS

| Run | max \|board − Python\| (gate 1e-4) | Interrupt work per 4 samples, avg / max (cycles) | Background per 128 samples, avg / max |
|---|---|---|---|
| Mode A | 6.1e-6 | 2529 / 3107 | — |
| Mode B | 6.1e-6 | 740 / 775 | 7096 / 8892 |
| Mode A + NR | 2.0e-5 | 6280 / 7237 | — |
| Mode B + NR | 9.4e-6 | 744 / 799 | 72 192 / 72 881 |

Values from the re-run after fix C30 (`tools/board_regress.sh`). Before C30 a leftover EDMA from the previously loaded program was still running; the outputs were already correct, and the cycle counts changed by up to 2.6 % (Mode A + NR: 6447 → 6280 avg).
CPU load with no codec, at 300 MHz: Mode A 10.1 %, Mode B 3.8 % ((740 + 7096/32) / 250 = 3.85 %), Mode A + NR 25.1 %, Mode B + NR 12.0 % (interrupt work / 25 000 cycles per 4 samples; Mode B adds the background block / 800 000 per 128 samples).

On-board Goertzel gains (dB), equal to `board_expected.txt` within 0.01 dB:

| Hz | 250 | 375 | 500 | 750 | 1k | 1.5k | 2k | 3k | 4k | 6k | 8k |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Mode A | 17.40 | 17.41 | 17.65 | 19.03 | 20.66 | 23.33 | 25.60 | 28.02 | 29.66 | 30.00 | 30.00 |
| Mode B | 17.59 | 17.50 | 17.27 | 17.53 | 19.67 | 22.50 | 25.00 | 27.50 | 29.89 | 29.99 | 30.02 |

Real-time gates: Mode A 3107 < 25 000; Mode B 8892 + 32 × 740 = 32 572 < 800 000. With NR: 7237 < 25 000; 72 881 + 32 × 744 = 96 689 < 800 000. All pass.
`-O0` build (`internal_o0`): Mode A 7620 avg (3.0× slower), Mode B 1196 + 25 220 (bg), Mode A + NR 12 499, Mode B + NR bg 257 754. Dumps and readouts: `results/phase4/board/`.

## T6: CPU load, `live.out`, 60 s per mode, EDMA + Read FIFO

| Mode | Interrupt avg / max (cycles per 4 samples) | Background avg / max (per 128 samples) | CPU at 300 MHz | Overruns / clips |
|---|---|---|---|---|
| A | 2617 / 2785 | — | **10.5 %** (peak 11.1 %) | 0 / 0 |
| B | 829 / 851 | 7242 / 7253 | **4.2 %** | 0 / 0 |

Estimates: Mode A ≤ 10.2 % (pack, 300 MHz; measured 10.5 % avg, slightly above); Mode B 2.6–5.0 % (C4; measured 4.2 %, inside).

## Step 8: lab programs — PASS

- `lab_arith`: cycles int16 316, int32 (64-bit acc) 522, float 324, double 1000. All four results = −1 782 181 120. The PC build's float32 result was off by 7e-8 (relative), but the C674x `-O3` code splits the sum across parallel accumulators, and the exact value is a multiple of 128, so it is representable in float32. The difference is summation order, not an error.
- `lab_conv`: linear 1 3 6 9 7 4; circular N = 4: 8 7 6 9; circular N = 6 = linear. All as expected.
- `lab_dft` (N = 256): direct DFT 107 796 990 cycles, own radix-2 228 676, DSPLIB `fftSPxSP` 2145; errors 3.8e-6 / 3.8e-6.
- `lab_bench` (`-O3` / `-O0`, cycles; all errors ≤ 4.8e-06; `icfftr2_gain` = 256.0 (255.999985)):

| # | Block | -O3 | -O0 |
|---|---|---|---|
| 0 | DSPLIB fir_gen (21 taps × 48) | 838 | 849 |
| 1 | plain-C FIR | 1052 | 25 402 |
| 2 | DSPLIB biquad × 48 | 486 | 490 |
| 3 | plain-C biquad × 48 | 803 | 2712 |
| 4 | own radix-2 FFT 256 | 228 720 | 350 118 |
| 5 | cfftr2_dit | 4668 | 4667 |
| 6 | plain-C bit reversal | 5299 | 11 969 |
| 7 | icfftr2_dif | 5546 | 5560 |
| 8 | cfftr4_dif | 4903 | 4885 |
| 9 | fftSPxSP | 2290 | 2237 |
| 10 | ifftSPxSP | 2181 | 2170 |
| 11 | HPF × 48 samples | 5864 | 9898 |
| 12 | Mode A × 48 samples | 22 634 | 79 815 |
| 13 | Mode B block (128) | 8907 | 26 980 |
| 14 | ha_process(4), Mode A | 3048 | 8748 |
| 15 | ha_process(4), Mode B | 784 | 1230 |
| 16 | Mode A × 48 with NR | 68 050 | 139 989 |
| 17 | Mode B block with NR | 70 221 | 257 921 |
| 18 | howl detector block | 6726 | 16 923 |
| 19 | notch × 48 | 2580 | 4770 |

## Step 9: fallback and stored output

- `fallback.out` (per-sample, FIFO off): 48 kHz, `isr_max` 1875 cycles of 6250, RSTAT = XSTAT = 0, no overruns; Mode B selected via `g_req[0]` ran with `bg_max` 8947. (The `isr_max` of the Mode B run still includes its first 3 s in Mode A.)
- `stored.out`: XSTAT = 0 (no underrun), `isr_max` 3492 (includes start-up), no clips, 300.001 MHz.
- Start-up of the FIFO build after the TRM XDATA wait: 5 of 5 starts, XSTAT = RSTAT = 0.

## Step 10: extras on the board, built-in signals only (C31: no live input)

**Feedback notch** (`stored_speech.out`, auto notch on via `g_req[3]`):

| Input | `g_ha.nt.n` | Notch frequency | Verdict |
|---|---|---|---|
| Built-in speech only, 12 s (2 s clip looped 6×) | 0 | — | PASS: no false notch |
| Speech + steady 2500 Hz tone, 10 dB above the speech RMS (`g_stored_tone_hz`) | 1, already 0.5 s after enabling | 2500.49 Hz (earlier run: 2500.83 Hz) | PASS: error ≤ 0.03 %, one notch only |

XSTAT read `0x20` once in the tone run: bit 5 = XDATA ("buffer ready", a status bit; TRM Table 23-41). XERR = 0, so no error.

**Noise suppression** (`internal_speech.out`, built-in speech + board-generated white noise at `g_stored_snr_db` = 5 dB):

| | max \|board − Python\| | Mode A | Mode B |
|---|---|---|---|
| Without NR | 1.5e-5 | — | — |
| With NR | 2.0e-5 / 1.5e-5 | **+8.39 dB SNR** (speech −1.93 dB, noise −10.33 dB) | **+8.78 dB SNR** (speech −1.56 dB, noise −10.34 dB) |

The SNR gain comes from shadow filtering with the Python reference on the board's exact input (`python/board_compare.py nr`); the board output equals that reference within 2e-5. The PC results were +5.9 to +8.5 dB (A) and +6.5 to +9.4 dB (B) on 11.8 s clips. Cycles: Mode A + NR 6115 avg / 7047 max per 4 samples, Mode B + NR background 70 248 avg.

**Listening demos** (`stored_speech.out`, 2500 Hz tone; 6 s with the notch off, then `g_req[3] = 1`; the McASP is stopped at the end):

| Tone level vs speech RMS | Notch | Limiter (`g_ha.clips`) | Heard by the user |
|---|---|---|---|
| +10 dB (`g_stored_tone_db` = 10) | placed at **2500.48 Hz** | 81 279 samples over the whole 16 s run (not split by phase). With about 27 dB of gain at 2.5 kHz the tone reaches the −1 dBFS limiter | whistle, then it **stopped** when the notch came on |
| 0 dB (`g_stored_tone_db` = 0) | **not placed** in 16 s | 117 (notch off, 6 s) / 39 (2 s) / 156 (8 s): occasional speech peaks only | the user could not hear this run |

At 0 dB the tone never stands 25 dB above the band average while speech is present, so the detector correctly leaves it alone. A real howl grows until it dominates (the +10 dB case). Detection threshold between 0 and +10 dB: not measured.

**Re-run** of everything above: `bash tools/board_regress.sh` (about 20 min, headless, no audio input).
