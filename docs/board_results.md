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
