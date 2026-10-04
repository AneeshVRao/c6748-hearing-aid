# CHANGES

## 2026-10-04 – Update 6: TRM, replacement board file, library paths, fallback I/O

### Decisions recorded (from you)

- LED plan accepted: D4 = mode, D5 = clip + preset (blink count), D6 = CPU-busy scope pin, D7 left to AMUTE.
- Team block unchanged.

### Correction of an Update 5 error

- **"GEL PLL0 bug" withdrawn.** Update 5 said `device_PLL0()` enables PLL1 at GEL line 732. Wrong: line 732 is the last line of `device_PLL1()` (DDR PLL), where PLL1 is correct; `device_PLL0()` enables PLL0 at line 658. I had read two separate printouts (lines 574–632 and 730–746) as one function. TI's CCS 7.2 `C6748_LCDK.gel` has the same structure. Fixed in `hardware_notes` §1.7/§7/§9, `06`, `08` R11, `02`, `REVIEW` (issue 28), `cpu_check.py` (comment), README.

### New findings

| Finding | Basis |
|---|---|
| CGT C6000 8.1.3 (only C6000 compiler on the PC) is ELF-only; C67x v2.00 `dsp67x.lib` is COFF → cannot link. **C674x DSPLIB 3.4.0.0 is already installed** and is ELF (PROPOSED CHANGE – confirm) | CGT README line 112; object header bytes; `dsplib.ae674.mk` line 18 |
| C674x ifftSPxSP scales by 1/N; reference C round trip = x (≤ 1.5e-7); fft 1965 / ifft 1985 cycles at N = 256 | `DSPF_sp_ifftSPxSP_cn.c` line 167; gcc test; `DSPLIB_C674x_TestReport.html` |
| LED pin-mux: PINMUX13[11:8] = 8h (D4), PINMUX13[15:12] = 8h (D5), PINMUX5[15:12] = 8h (D6) | TRM p. 247, 230 |
| AFIFO only via the McASP DMA port (0x01D0 2000; RFMT/XFMT = 0x80F0); RFIFOCTL = 0x401 then 0x10401, before McASP reset release | TRM Table 23-9 note, p. 1107; Table 23-49, p. 1160 |
| EDMA PaRAM for 4-sample blocks: RX AB-sync (OPT 0x00100004, ACNT 4, BCNT 4), TX A-sync (OPT 0x00001000) | TRM §16.2.2, p. 554–556; Table 16-15, p. 611–612 |
| CPU clock formula and register read-out; 300 MHz with the GEL | TRM Tables 6-1, 7-8, 7-12, p. 118, 141, 145 |
| KICK registers disabled from silicon rev 2 | TRM §10.2.2, p. 204 |
| `LCDK6748_Support_DSP.c` differs from the zip file only by `Config_LCDK6748()` and its two calls; pin-mux/PSC values verified against the TRM | diff; TRM p. 166, 220–229 |

### Files changed

| File | Change |
|---|---|
| `research/hardware_notes.md` | Update 6 note; §1.4 EDMA/data-port/RFIFOCTL rows from the TRM; §1.5 LED pin-mux values; §1.7 retraction + clock read-out + which GEL; §3.3 (new) library paths and CCS settings, C674x differences; §4 Mode B with C674x; §7 items 4c, 5, 7, 8; §10 (new) board-file diff and swap steps; §11 (new) I/O modes |
| `05` | Fallback I/O modes line; LED pin-mux; Mode B cycles/load with C674x (10,850 cycles; 1.7–3.3 %) |
| `06` | Replacement file + swap; Read FIFO, DMA port, PaRAM, LED pin-mux lines; board step 0 rewritten; C674x DSPLIB table and CCS settings; §3.6 (new) I/O modes; tools |
| `07` | T6, T11 (C674x figures), **T16 (new)** fallback modes |
| `08` | R10, R11 (back to Low), R12, R15, **R16 (new)**; Weeks 1–2 |
| `02` | S10 saved/read; S19 note; **S28** C674x DSPLIB, **S29** CCS 7.2 LCDK GEL, **S30** CGT 8.1.3 README; unverified list |
| `calc/cpu_check.py` + output | Update 6 section (C674x cycles; Mode B 10,850 cycles); GEL comment corrected |
| `calc/review_check.py` + output | 6 new checks → **55/55** |
| `research/REVIEW.md` | Banner, verdict line, issues 21/28–33 closed or withdrawn, 34–37 new, spec rows, decisions 10/13/15, gaps |
| `papers/DOWNLOAD_LIST.md` | Saved list (TRM, replacement file); no blockers left |
| `00_README.md` | Summary, decisions, Update 6 QC, gaps, checklist |

### About your item 5

Your Update 5 message had six numbered items; I could not find an item 7 about fallback I/O in it, so it was not in my reply. It is added now (`hardware_notes` §11, `06` §3.6, `07` T16, `08` R16).

### Core design

**Unchanged.** Library swapped (tool constraint); latency unchanged (8.81 / 7.67 ms).

## 2026-10-04 – Update 5: S19 package, GEL, DSPLIB v2.00; FIFO decision

### Decisions recorded (from you)

- McASP **Read FIFO ON (threshold 4), Write FIFO OFF** – default everywhere.
- Processor SDK skipped (nothing needs it).
- Emulator and powered speakers come from the lab. CCS already installed.
- Team block left unchanged.

### Files added / unpacked

| Item | What |
|---|---|
| `papers/S19_code_2017_02_05/` | Unzipped `code_2017_02_05.zip` (611 entries) |
| `papers/DSPLIB_sprc121/` | Unzipped `sprc121.zip` → `C67xDSPLIB_v200.exe` (C67x DSPLIB v2.00) + `Readme.txt`. The installer was unpacked in the session workspace only, to read headers and SPRU657B |

### Files changed

| File | Change | Old → new | Basis |
|---|---|---|---|
| `research/hardware_notes.md` §1.3 | Reg 2/3 now confirmed | "constant not read" → 0x00 / 0x20 confirmed | `AIC3106.h` lines 128–129 |
| `research/hardware_notes.md` §1.4 | FIFO default; EDMA 4 words/RX event; DMA-port design choice; 1.33 ms explained | Both FIFOs → Read on / Write off | S14 p. 12, 51–52; S8 Table 6-50; S19 `ISRs.c` |
| `research/hardware_notes.md` §1.5 | Buttons need no pin-mux; LEDs do (TRM); D7 lost to AMUTE; new LED plan (PROPOSED CHANGE – confirm) | — | S8 §3.6 p. 26; `Config_LCDK6748()` |
| `research/hardware_notes.md` §1.7 | GEL: 300 MHz requested; possible PLL0 bypass bug | "NOT FOUND" → partly found | GEL lines 246, 399–405, 732 |
| `research/hardware_notes.md` §3, §3.2 (new) | DSPLIB package vs S15 table: names, arguments, alignment, cycles match; biquad pole rule; Rev 2.0 interrupt bug applies; ifft scaling conflict (gcc test of TI reference C) | — | Package headers; S15 p. 4-27, 4-32, 4-46, B-2 |
| `research/hardware_notes.md` §7, §9 (new) | Status table (pin-mux McASP/I2C found, LED pin-mux open, KICK note); full S19 package check with file : function : line | — | S19 package; S12 |
| `05` §1, §7, §11 | I/O decided; latency rows; LED plan | Mode A 10.15 → **8.81 ms**; Mode B 9.00 → **7.67 ms** | `latency_check.py` |
| `06` §3.1–3.5, tools | Replacement support file required; register list fixed (20/23, 47/64 alternatives removed); Read FIFO/EDMA/DMA-port settings; **board step 0 (PLL0)**; DSPLIB v2.00 notes; scope pin D6 | — | as above |
| `07` T5, T6, T11 | Latency 8.81/7.67; CPU 1.7–6.7 % / 1.8–3.4 %; biquad test coefficients; ifft scale check | — | `cpu_check.py`, `latency_check.py` |
| `08` R3, R4, R10, R11, R12, R15; Weeks 1–2 | R11 raised to Medium (GEL PLL0); replacement file in R15 | — | GEL line 732 |
| `01` | Abstract latency | "8.8–10.2 / 7.7–9.0 ms" → "8.8 / 7.7 ms" | `latency_check.py` |
| `02` | S15, S19 rows; unverified list (ifft scaling conflict, CPU clock, LED pin-mux/EDMA/DMA port → TRM; SDK not needed) | — | — |
| `03`, `04`, `research/literature_extracts.md` | FIFO wording, LEDs D4–D6 | — | — |
| `calc/latency_check.py` + output | Default relabelled; 1.33 vs 0.67 ms explanation printed | — | — |
| `calc/cpu_check.py` + output | Update 5 section: biquad pole rule (fails for HPF), ifft-scale cost (0), load at 24 MHz bypass (128 % Mode A) | — | S15 p. 4-46 |
| `calc/review_check.py` + output | 6 new checks | 43/43 → **49/49** | — |
| `research/REVIEW.md` | Verdict, issues 23/25 closed, 27–33 new, spec, decisions 13–14, gaps | — | — |
| `papers/DOWNLOAD_LIST.md` | Saved list; blocker table with status | — | — |
| `00_README.md` | Summary, decisions, Update 5 QC, gaps, Claude Code checklist | — | — |

### FIFO figure (your question)

64 words × 1 word per sample period = 64/48 000 s = **1.33 ms**. The pack's figure was right for this board: S19 runs the McASP with **one 32-bit slot per frame** that carries L+R (`Init_McASP0()` RTDM = XTDM = 1, 32-bit slot, lines 658–672; EDMA example "two Int16 read from McASP each time", `ISRs.c` line 17). 0.67 ms applies only if L and R use separate words. The point is now moot for latency, because the Write FIFO is off.

### Core design

**Unchanged.** Only defaults and bring-up details changed.

## 2026-10-04 – Update 4: LCDK schematic, S19 identity, FIFO on by default

### Files added

| File | What |
|---|---|
| `papers/S12_SPRCAF4_LCDK_schematics/` | Unzipped `sprcaf4.zip` (schematic PDF rev A7E, BOM, DSN, release folder A7A) |
| `calc/latency_check.py`, `latency_check_output.txt` | Latency for FIFO off / Read FIFO only / both FIFOs |

### Files changed

| File | Change | Old → new | Basis |
|---|---|---|---|
| `research/hardware_notes.md` §1, §7 | All "NOT FOUND – check schematic" items filled with sheet + net | MCLK 24.576 MHz (Y5, AIC_MCLK); BCLK/WCLK ↔ ACLKX/AFSX, codec master; AXR13 → DIN, DOUT → AXR14; I2C0, 0x18; LINE IN → LINE1L+/R+; MIC IN → MIC3L/R; LINE OUT ← LEFT_LO+/RIGHT_LO+ via 10 µF; HP pins unconnected | S12 sheets 6, 7, 10 |
| `research/hardware_notes.md` §1.3 | Codec register choices | **19/22 = 0x04** (LINE1, not 20/23 LINE2); **82/92 = 0x80, 86/93 = 0x09** (line outputs, not 47/64 HP); 101 = 0x01, 102 = 0x02 (PLL bypass) | S12 sheet 10; S13; S19 |
| `research/hardware_notes.md` §1.4 | Framing follows S19 (DSP mode, codec master, burst, 32-bit slot); **AFIFO ON by default, RNUMEVT = WNUMEVT = 4**; latency table | I2S 2-slot, FIFO off → DSP mode, FIFO on | S14 §2.4.4; S19 |
| `research/hardware_notes.md` §8 (new) | S19 identity and match table | "LCDK support code" → Welch/Wright/Morrow textbook file, no version, matches schematic | rt-dsp.com |
| `05` §1, §3, §7, §9, §11 | I/O = EDMA + AFIFO, 4-sample blocks; MCLK; latency rows | Mode A 8.60 → **10.15 ms** default (8.81 recommended); Mode B 7.46 → **9.00 ms** (7.67); CPU 3–11 % → **2–7 %** @456 MHz | `latency_check.py`, `cpu_check.py` |
| `06` | Start from S19 `DSP_Init_EDMA()` + our AFIFO set-up; register checklist from S12 | — | S12, S19 |
| `07` T5 | Expected latency for each FIFO case | — | `latency_check.py` |
| `08` R3, R14, R15 | R14: High likelihood; headphones need an amp (line drivers into 16–32 Ω via 10 µF cut bass below ≈ 0.5–1 kHz). R15: Low–Medium (schematic and S19 agree) | — | S12 sheet 10 |
| `01` | Abstract latency/CPU sentence; trimmed to 151 words | "8.6/7.5 ms, 3–11 %" → "8.8–10.2 / 7.7–9.0 ms, 2–7 %" | as above |
| `02` | S12 row saved/read; S19 row full identity and links; unverified list (schematic rows closed, header constants open) | — | — |
| `03`, `04`, `research/literature_extracts.md` | Peripherals row and latency wording | — | — |
| `calc/cpu_check.py` + output | Update 4 section: EDMA + AFIFO | Mode A 1.66–6.74 % @456 (2.53–10.24 % @300); Mode B 1.84–3.42 % @456 | S15 formulas; ASSUMPTION ISR costs |
| `calc/review_check.py` + output | 4 FIFO latency checks added | 39/39 → **43/43** pass | — |
| `research/REVIEW.md` | Verdict, issues 15–17 closed, new issues 22–26, spec, decisions 6/10/11/12, gaps | — | — |
| `papers/DOWNLOAD_LIST.md` | S12 saved; new blocker list with direct links | — | — |
| `00_README.md` | Summary lines 2/7/8, decisions, Update 4 QC, gaps | — | — |

### Core design

**Unchanged** (48 kHz, 5 bands, Mode A/B, filter lengths). Only the I/O scheme changed, because the FIFO you asked for is serviced by DMA. **PROPOSED CHANGE – confirm:** Write FIFO off, because with it on Mode A is 10.15 ms (0.15 ms over the 10 ms target).

## 2026-10-03 – Update 3: TI hardware facts and full pack review

### Files added

| File | What |
|---|---|
| `papers/` (7 TI PDFs) | S8 datasheet, S9 CPU guide, S11 LCDK guide, S13 codec, S14 McASP, S15 DSPLIB, S16 DSPLIB examples |
| `research/hardware_notes.md` | Board/codec/McASP/processor/DSPLIB facts with page citations; codec register list; DSPLIB constraints; CPU re-check; NOT FOUND list |
| `research/REVIEW.md` | Verdict, 21-issue table, final one-page spec, open decisions with recommendations, gaps |
| `calc/cpu_check.py`, `cpu_check_output.txt` | CPU load from S15 cycle formulas, with assertions that fail on illegal DSPLIB parameters |
| `calc/review_check.py`, `review_check_output.txt` | Independent recomputation of 39 quoted numbers (39/39 pass) |

### Files changed

| File | Change | Old → new | Basis |
|---|---|---|---|
| `05` §1 | Mode/preset control via buttons S2/S3 and LED D4; single per-sample I/O scheme for both modes | "push button once schematic confirms" → S11 Tables 7–8 | S11, S8 Table 6-6 |
| `05` §2 | Output label | "Line Out → headphones" → "LINE OUT jack, headphones or powered speakers" | S11 §1.1 (LINE OUT only); jack wiring NOT FOUND |
| `05` §3 | 48 kHz basis | Added codec fS equations and Table 10-1 citation; MCLK NOT FOUND | S13 p. 22–24 |
| `05` §7 | McASP FIFO note | Added | S14 §2.4.4 |
| `05` §9 | CPU estimate replaced | Mode A "1934 cycles / 1.27 %" (illegal DSPLIB calls) → **3.0–10.7 % @456 MHz (4.5–16.2 % @300)**. Mode B "7638 / 0.63 %" → 12,746 cycles/frame, **3.2–7.4 % @456 MHz** inside the per-sample ISR | S15 p. 4-41, 4-46; `cpu_check.py` |
| `05` §9 | Clock source | 300 MHz now cited (S11 §3.5) | S11 |
| `05` §11 | Summary loads, I/O and controls rows | As above | — |
| `06` §3.1–3.5 | Codec/McASP checklist; code tree (plain-C Mode A and HPF, background FFT); DSPLIB table with constraints; power-of-2 memory plan (1168 floats); TSCL confirmed; scope pin = LED D6/D7; emulator list | — | S8, S9, S11, S13, S14, S15 |
| `06` §3.4 | Memory | Delay lines 610 floats → 1168 floats (power-of-2 circular); Mode B 10 KB → 8.8 KB (H[k] no longer counted twice; 16-word ifft pad) | S9 §3.9.2; S15 p. 4-33 |
| `07` T6 | CPU expectations | "1.3 % / 0.6–1.3 %" → "3.0–10.7 % / 3.2–7.4 %" | `cpu_check.py` |
| `07` T11 | Benchmark expanded | Added DIT→DIF chain 8271, fir_gen (21, 48) 656, biquad (48) 268 | S15 formulas |
| `07` T4/T9 | Pass thresholds labelled DESIGN CHOICE | — | — |
| `08` | R4 load range; R10 constraints now known; R12 narrowed; **new R14** (LINE OUT vs headphones), **R15** (codec bytes without schematic); Week 2 TSCL task updated | — | S9, S11, S13, S15 |
| `03` | FIR direct form and IIR cascade now plain C; DIF ordering confirmed; circular addressing with power-of-2 sizes; peripherals detailed; **new "Explained" depth**: Harvard, pipelining, MAC hardware, split radix. Counts 24/11/2/0 → 21/10/2/4 | — | S9, S11, S15 |
| `04` §13, §15 | Biquad not from DSPLIB on board; pipeline phases, delay slots, AMR, TSCL, interrupt/EDMA events | — | S8, S9, S15 |
| `01` | Abstract CPU figure | "under 2 %" → "estimated 3–11 %" | `cpu_check.py` |
| `02` | S8, S9, S11–S16 rows marked saved and read with the new facts; S12 marked not supplied; unverified list: TSCL, delay slots and icfftr2 order removed (resolved); ifft scaling added; clock and schematic rows updated | — | — |
| `research/literature_extracts.md` A1 | Wording of N3 gain spread (12.5 dB spread, 5 dB adjacent step) | — | `gain_check.py` |
| `calc/design_check.py` + output | Removed the illegal 16-sample-frame estimate; relabelled partial Mode B and bank-only loads | — | S15 |
| `papers/DOWNLOAD_LIST.md` | 13 saved; still missing S5, S6, S7, S10, S12 | — | — |
| `00_README.md` | Index, summary (CPU, syllabus counts, I/O), Update 3 QC, gaps | — | — |

### Core design

**Unchanged** (48 kHz, 5 bands, Mode A/B, filter lengths, latencies). The TI documents did not show it cannot work. They changed only how it is coded (plain C per sample instead of DSPLIB block calls in Mode A) and the CPU figures.

## 2026-10-03 – Update 2: six PDFs added, audiogram and citations fixed

### Files added

| File | What |
|---|---|
| `papers/` (6 PDFs) | Bisgaard 2010, Venema 2001, Sokolova 2021, Sokolova 2022 (PDF4, identified as the PMC author manuscript of S2), Yang/Liu/Jou 2016, US 12,627,936 B2 |
| `.gitignore` | Excludes `papers/` (licence-restricted PDFs, personal study only) |
| `research/audiogram.md` | Bisgaard N2/N3/S2 thresholds, band mapping with interpolation working, half-gain and ×0.4 gains, accuracy of Mode A/B per case |
| `research/literature_extracts.md` | Yang/Liu/Jou full-text extracts (class-2 limits, eqs. 15–17, delay refs), plus Sokolova 2021/2022 and patent extracts (complementary design, resamplers, alignment, min-phase, WDRC eqs. 1–7), and the WDRC scope decision |
| `calc/audiograms.py` | Bisgaard data and mapping functions |
| `calc/gain_check.py`, `calc/gain_check_output.txt` | Gain tables for 3 audiograms × 2 rules, simulated Mode A/B errors, eq. (15)/(16) cross-check, lengths needed for 60 dB stopband |
| `CHANGES.md` | This log |

### Files changed

| File | Change | Old → new | Basis |
|---|---|---|---|
| `calc/design_check.py` | Placeholder audiogram (20/30/40/50/60/65 dB HL at 250 Hz–8 kHz) replaced by Bisgaard N3 via `audiograms.py` | — | S26 Table 2 |
| `calc/design_check_output.txt` | Re-run | Band gains B5…B1: 30 / 30 / 25 / 20 / 12.5 → **30.00 / 30.00 / 25.36 / 20.36 / 17.50 dB** | Our calculation |
| | | Mode B max error: 1.33 → **0.38 dB** | Our calculation |
| | | Tone-test gains (all 11 frequencies) updated | Our calculation |
| | | Latency, ripple, CPU and memory **unchanged**: they do not depend on gains | — |
| `calc/figs2.py`, `calc/fig_modeA_bands.png` | Composite curve now uses the N3 half-gain table | — | Our calculation |
| `05_system_design.md` §4 | Band-gain column updated | As above | `research/audiogram.md` |
| `05_system_design.md` §5 | Mode B error | 1.33 → 0.38 dB | Our calculation |
| `05_system_design.md` §6 | Rewritten: Bisgaard N3 default, N2/S2 test cases, half-gain [S27] and ×0.4 variant, new tone-test table with targets, steep-loss limitation (**PROPOSED CHANGE – confirm**: scope statement only) | — | S26, S27, `gain_check.py` |
| `05_system_design.md` §6 (WDRC) | One-pole sketch replaced by the AGC loop with patent eqs. (6)–(7); marked **OPTIONAL – confirm** | — | S4, S2 |
| `05_system_design.md` §8 | Added ANSI class-2 comparison (ripple passes; 52 dB stopband below the 60 dB figure; 60 dB would need 27/39 taps → 10.79 ms) and the eq. (17) verdict (not needed) | — | S3 §II-A, eq. 17; `gain_check.py` |
| `05_system_design.md` §9 | Added eq. (16) cross-check (50.62 / 31.00 multiplies per sample vs the conservative 61 ops) and eq. (15) check (375 samples) | Estimates unchanged | S3 eqs. 15–16; `gain_check.py` |
| `05_system_design.md` §10, §11 | Min-phase extra now cites PDF4 numbers and the S3 phase warning; summary rows added | — | S2, S3 |
| `02_sources.md` A1 | S1–S5 and S26 rows rewritten with saved files and full-text status; **S27 (Venema 2001) added**; new A4 table of works cited only via another source (Lybarger, Byrne & Dillon, Stone & Moore, ANSI) | — | PDFs 1–6 |
| `02_sources.md` B | Removed "Bisgaard values" and "half-gain rule" from the unverified list (now sourced); added "exact NAL-R formula" and "full ANSI mask check" | — | — |
| `02_sources.md` C | Step-1 table updated from full texts | See corrections below | PDF3–PDF6 |
| `04_theory_notes.md` | §14: S3 eqs. (15)/(16) and complementary split added. New §16 (gain rules) and §17 (WDRC/AGC). §10: Mode B error 1.33 → 0.38 dB | — | S1, S3, S4, S26, S27 |
| `03_syllabus_mapping.md` | Matched-z row reworded (WDRC now uses the patent AGC loop; the level smoother keeps the matched-z mapping). **Coverage counts unchanged** | — | S4 |
| `01_title_and_abstract.md` | "sample audiogram" → "standard moderate audiogram (Bisgaard N3)"; abstract trimmed to 156 words | — | S26 |
| `07_testing_plan.md` T2 | Run all six gain cases; Bisgaard S2 expected to exceed 3 dB in Mode A | — | `research/audiogram.md` |
| `papers/DOWNLOAD_LIST.md` | Saved vs missing lists; licence notes | — | — |
| `00_README.md` | File index, closed gaps removed, remaining gaps, new quality check, personal-study note | — | — |

### Corrections of earlier errors (found while reading the full texts)

1. **S2 single-rate filter lengths.** The earlier pack said "~64 taps (8 kHz) to ~2048 taps (250 Hz)". PDF4 Table 1 gives **53 to 1232** single-rate taps and **77** multirate. The earlier figures came from an automated web summary.
2. **S2 eleventh band.** The earlier pack assumed the 11th band was 750 Hz. PDF4 Table 1 lists 0.75 **and** 0.375 kHz. The 11 bands are 8, 6, 4, 3, 2, 1.5, 1, 0.75, 0.5, 0.375 and 0.25 kHz. The assumption is removed.
3. **S4 "ANSI S3.22 Class 0".** Wrong standard. The patent's class 0 refers to the half-octave filter specification (ANSI S1.11, as in S1/S2). S3.22 is the standard for attack/release definitions.
4. **S5 authors.** Previously "Garudadri et al. (not confirmed)". Now the full list and pp. 1900–1904, taken from S1's reference [17].
5. **The previous "11-band complexity 13.7×"** is confirmed as 13.67× (PDF4/PDF6 Table 2).

### Not changed (deliberately)

- **Core design:** 48 kHz, 5 octave bands, Mode A/Mode B, G = 21 and F = 31 taps, latency 8.60 / 7.46 ms. No source shows it is wrong.
- **One limitation is now documented:** steep losses in Mode A (`05` §6), handled by a scope statement rather than a redesign.
