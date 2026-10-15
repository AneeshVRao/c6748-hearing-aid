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
| Audio (1 kHz test tone, PC → LINE IN → LINE OUT) | heard | pass |
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
| Audio | quiet 1 kHz tone played | ask the user |
