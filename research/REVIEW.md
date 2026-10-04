# REVIEW – Full pack review before handing over to Claude Code (Update 3, 3 Oct 2026; revised in Updates 4, 5 and 6)

> **Update 6 (TRM S10 read; replacement board file saved; PC tool folders inspected).** Changes marked **[U6]**. **Correction:** issue 28 ("GEL PLL0 bug") was my misreading and is withdrawn. New finding: the installed compiler (CGT 8.1.3) is ELF-only, so the C67x v2.00 library (COFF) cannot be linked; the C674x DSPLIB 3.4.0.0, already installed, replaces it. Issues 21, 28–33 closed; issues 34–37 new.

> **Update 5 (S19 package, LCDK GEL and C67x DSPLIB v2.00 read; FIFO decision taken).** Changes are marked **[U5]**. Default I/O is now **Read FIFO ON, Write FIFO OFF** (your decision). Issues 23 and 25 are closed; issues 27–33 are new.

> **Update 4 (schematic S12 read, S19 identified, AFIFO on by default).** Changes are marked **[U4]**. Issues 16 and 15 are now closed by the schematic; issues 22–26 are new.

Reviewed as a strict lab examiner and as the engineer who must build from this pack.

**What was checked.** Every `.md` file, the `calc/` scripts and their outputs, and both figures.

**How it was checked:**

- All calc scripts were re-run.
- An independent script, `calc/review_check.py`, recomputes key numbers from first principles and compares them with the values written in the files. **[U6] 55/55 pass** (6 new: TRM clock formula, RFIFOCTL value, LED pin-mux values, Mode B cycles with the C674x FFTs, T11 fir_gen).
- Both Mermaid diagrams were re-rendered successfully.

---

## a) Verdict

**Yes, with fixes (all fixes listed below are already applied).**

1. The core design is consistent across all files and scripts: 48 kHz, 5 octave bands, 21/31-tap filters, 375-sample bank delay. **[U5]** End-to-end latency with the default (Read FIFO on, Write FIFO off): **Mode A 8.81 ms, Mode B 7.67 ms**, both under 10 ms. (FIFO off: 8.60/7.46 ms; both FIFOs, rejected: 10.15/9.00 ms.)
2. The TI documents show the design **fits** the C6748: **[U4]** with EDMA + AFIFO the worst-case CPU is ≈ 10 % at 300 MHz (1.7–6.7 % at 456 MHz); data ≈ 15 KB against 256 KB of L2.
3. The TI documents did force a correction. The old CPU estimate used two DSPLIB calls outside their legal parameters, and it ignored interrupt overhead. Both are fixed (Update 3: 3–11 % at 456 MHz with per-sample interrupts; **[U4]** 2–7 % with EDMA blocks of 4).
4. Mode A now runs **per sample in plain C**. DSPLIB is used for the Mode B FFTs and for the benchmark experiments.
5. Both modes share **one** I/O scheme. **[U4]** Because the AFIFO is serviced by DMA (S14 §2.4.4), the scheme is now **EDMA3 events 0/1 with 4-sample ping-pong blocks**, not a per-sample interrupt.
6. The syllabus map was over-claiming four items (Harvard architecture, pipelining, MAC hardware, split radix). They are relabelled "Explained (+ measured)".
7. Every number is either cited (document + table/equation/page) or labelled "our calculation" with a script.
8. **[U4] The codec bring-up risk is now lower.** The schematic (S12, rev A7E) gives MCLK 24.576 MHz, I2C0 at 0x18, AXR13 → DIN / DOUT → AXR14, and the jack wiring. S19 matches it on every connection checked. **New hardware fact:** LINE OUT is driven by the codec's line drivers through 10 µF; the headphone drivers are not wired, so **headphones need an amplifier or powered speakers** (R14).
9. Claude Code can start at once on the MATLAB prototype, the C modules and the PC-side tests. Board work starts with the loopback milestone.
10. **[U5→U6]** The S19 package confirms every codec, I2C and McASP value. **[U6]** The TRM fills the last gaps (LED pin-mux, PLL read-out, EDMA PaRAM, DMA port for the FIFO). The Update 5 "CPU stuck at 24 MHz" warning is **withdrawn**: line 732 belongs to the DDR PLL function; PLL0 is enabled at line 658. **New practical blocker found and solved:** use the C674x DSPLIB (ELF) because CGT 8.1.3 cannot link the C67x v2.00 COFF library.
11. Remaining decisions are in section d; none blocks coding. All have a recommended default, so none blocks the start of coding.

---

## b) Issues found

Severity levels:

- **blocker** – would stop the build or fail the viva.
- **major** – wrong number or design gap.
- **minor** – wording, labelling or small inconsistency.

| # | File | Issue | Severity | Fixed? | How |
|---|---|---|---|---|---|
| 1 | `05` §9, `06` §3.3, `calc/design_check.py` | Mode A cycle estimate called `DSPF_sp_fir_gen` with nr = 2 (rule: nr ≥ 4, S15 p. 4-41) and `DSPF_sp_biquad` with nx = 16 (rule: nx multiple of 3, S15 p. 4-46) | major | Yes | Mode A per sample in plain C; DSPLIB FIR/biquad only in benchmarks or the 32-sample option; new `calc/cpu_check.py` asserts the constraints |
| 2 | `05`, `07` T6, `08` R4, `00`, `01` | CPU load quoted as "< 2 %". It ignored per-sample interrupt overhead (2 slots per stereo frame) and left the HPF out of Mode B | major | Yes | Now 3.0–10.7 % (Mode A) and 3.2–7.4 % (Mode B) at 456 MHz; up to 16.2 % at 300 MHz (`cpu_check_output.txt`) |
| 3 | `05`, `06` | Mode A per-sample ISR and Mode B EDMA frames, with no single I/O scheme for run-time switching | major | Yes | DEFAULT: one per-sample McASP ISR for both modes; Mode B fills a software ping-pong buffer, FFT in background loop |
| 4 | `03` | Over-claim: Harvard architecture, pipelining and MAC hardware labelled "Core"; split radix labelled "Comparison" although nothing runs | major (viva) | Yes | New depth level "Explained (+ measured)"; counts now Core 21 / Comparison 10 / Supporting 2 / Explained 4 |
| 5 | `03`, `04` §13 | FIR direct form and IIR cascade said to use `DSPF_sp_fir_gen` / `DSPF_sp_biquad` on the board | minor | Yes | Plain C on board; DSPLIB in benchmark |
| 6 | `06` §3.4 | Delay-line sizes (365 etc.) are not powers of two, so hardware circular addressing cannot be used (S9 §3.9.2) | minor | Yes | Buffers 512/256/128/16 + 32-float G/F lines = 1168 floats (4.7 KB) |
| 7 | `06` §3.4 | H[k] counted twice; ifftSPxSP 16-word pad missing (S15 p. 4-33) | minor | Yes | Corrected memory table (Mode B ≈ 8.8 KB) |
| 8 | `06` §3.5, `08` R12, `02` B | TSCL, `icfftr2_dif` ordering and delay slots marked unverified | minor | Yes | Confirmed: S9 §2.9.14; S15 p. 4-34; S9 Table 3-8 |
| 9 | `05` §1, `06` §3.5 | Mode button and scope pin "to be found in schematic" | minor | Yes | S11 Tables 6–8: S2 = GPIO2[4], S3 = GPIO2[5], LEDs D4–D7 |
| 10 | `05` §9 | 300 MHz labelled a bare ASSUMPTION | minor | Yes | Now cited: S11 §3.5 (AISgen NAND boot at 300 MHz) |
| 11 | `07` T11 | Benchmark list incomplete; no expected values for the FIR/biquad DSPLIB timing | minor | Yes | Added DIT→DIF chain (8271), fir_gen nh21/nr48 (656), biquad nx48 (268) |
| 12 | `07` T4, T9 | Pass thresholds (coherence 0.9, −60 dBc) not labelled | minor | Yes | Labelled DESIGN CHOICE |
| 13 | `research/literature_extracts.md` A1 | "Largest inter-band gain difference 12.5 dB" was ambiguous (12.5 is the max–min spread; adjacent step is 5 dB) | minor | Yes | Reworded |
| 14 | `calc/design_check_output.txt` | Mode B "cycles/frame 7638" printed as if it were the total (it excludes HPF and overhead) | minor | Yes | Relabelled; the full figure is 12,746 in `cpu_check_output.txt` |
| 15 | `05` §2 | "Line Out → headphones": LCDK has LINE OUT only (S11 §1.1); whether the jack is on the codec's headphone or line drivers is NOT FOUND | major (risk) | **Yes [U4]** | S12 sheet 10: jack on LEFT_LO+/RIGHT_LO+ via 10 µF; HP pins unconnected. Output = powered speakers or HP amp (R14 rewritten). "Route DAC to HPLOUT" fallback removed (not wired) |
| 16 | `06` §3.1 | Codec MCLK, master/slave, AXR pins, I2C instance and input pins unknown (schematic S12 not supplied) | major (risk) | **Yes [U4]** | S12 sheets 7/10: MCLK 24.576 MHz (Y5), codec master, I2C0, AXR13/14, LINE1L/R+ input, MIC3L/R mic. Registers 19/22 (not 20/23) and 82/92 + 86/93 (not 47/64) chosen (`hardware_notes.md` §1.3) |
| 17 | `research/hardware_notes.md` §3.1 | FFT calls must run with interrupts off (S15). 2923 cycles = 9.7 µs at 300 MHz, close to the 10.4 µs I2S slot period with the FIFO off | major (risk) | **Yes [U4]** | AFIFO now on by default (threshold 4); the FIFO covers the FFT interrupt-off time. Note: the earlier "+0.02–0.04 ms" cost was only for the Read FIFO; the Write FIFO adds up to 1.33 ms (issue 23) |
| 18 | `02` S16 | S16 cache-penalty data come from a C6713 DSK, not a C6748 | minor | Yes | Noted; the 2× factor kept only as a margin |
| 19 | `calc/` | `__pycache__/` folder in the pack | minor | Yes | Not committed |
| 20 | `05` §7 | Mode B latency model (2L + group delay) is still an assumption | minor | No | Must be measured (T5) |
| 21 | `06` §3.3 | `DSPF_sp_ifftSPxSP` scaling (1/N or not) not stated in the pages read | minor | **Yes [U6]** | Compare with MATLAB `ifft` in Stage 3 |
| 22 | **[U4]** `05`, `06`, `hardware_notes` | Earlier plan used I2S framing (2 slots, DATDLY = 1). S19, proven on this board, uses DSP mode with the codec as master and one 32-bit word per sample | major | Yes | Follow S19 framing (XFMT/RFMT = 0x000080F8, burst, 0-bit delay) |
| 23 | **[U4]** `05` §7, `01`, `00` | AFIFO on by default (as requested). The Write FIFO stays full (S14 p. 52), adding up to 64 samples = 1.33 ms; Mode A becomes **10.15 ms, 0.15 ms over the 10 ms target** | major | **Yes [U5]** – Write FIFO off accepted; 8.81 ms | **PROPOSED CHANGE – confirm:** Write FIFO off, Read FIFO on → 8.81 ms. Default left as requested |
| 24 | **[U4]** `05` §1, `06` | AFIFO raises DMA events, so a per-sample CPU interrupt no longer fits | major | Yes | EDMA3 events 0/1, 4-sample ping-pong, start from S19 `DSP_Init_EDMA()` (S19 does not set the FIFO; our addition) |
| 25 | **[U4]** `hardware_notes` §1.3 | Sample-rate bytes (reg 2/3) and S19 header constants not seen | minor | **Yes [U5]** – `AIC3106.h` lines 128–129: 0x20 / 0x00 | Expected reg 3 = 0x20, reg 2 = 0x00 (our calculation); read `code_2017_02_05.zip` headers |
| 26 | **[U4]** `hardware_notes` §1.5 | Button S2 (GPIO2[4]) shares its pin with EMA_CASn (S12 sheet 6) | minor | No | Set pin-mux to GPIO (TRM S10 or SDK code) |
| 27 | **[U5]** `06` §3.1 | The zip's `LCDK_Support_DSP.c` (2017) has no pin-mux or McASP power-up; only the separate `LCDK6748_Support_DSP.c` has `Config_LCDK6748()` | **blocker** (no audio otherwise) | Documented | Use the replacement file (link in `papers/DOWNLOAD_LIST.md`) |
| 28 | **[U5]** `hardware_notes` §1.7, `08` R11 | ~~Package GEL leaves PLL0 in bypass (line 732)~~ | — | **Withdrawn [U6]** | Line 732 is in `device_PLL1()` (DDR); `device_PLL0()` enables PLL0 at line 658 [TRM §7.2.2.2, p. 136]. My misreading of two concatenated printouts |
| 29 | **[U5]** `hardware_notes` §1.5, `05` §1, `06` §3.5 | LED D7 (GPIO0[9]) is set to AMUTE by S19's pin-mux; LEDs need pin-mux values that are not in any saved document | minor | Yes (plan changed) | Scope pin = D6; preset by blink count on D5; LED pin-mux from TRM |
| 30 | **[U5]** `hardware_notes` §3.2, `06` §3.3 | C67x v2.00 Rev 2.0 interrupt bug | major | **Superseded [U6]** | C674x DSPLIB used instead; its ifft is interrupt-tolerant with no bug listed |
| 31 | **[U5]** `06` §3.3, `07` T11 | `DSPF_sp_biquad` needs \|a1\| < 1 and \|(a2 − a1²)/a1\| < 1 (S15 p. 4-46); our HPF has a1 ≈ −1.98 | minor | Yes | HPF stays plain C; benchmark uses test coefficients |
| 32 | **[U5]** issue 21 | ifftSPxSP scaling conflict | minor | **Yes [U6]** | C674x `_cn.c` scales by 1/N (line 167); gcc round trip = x within 1.5e-7 |
| 33 | **[U5]** `06` §3.1 | RX 4 words per event; DMA port | minor (risk) | **Yes [U6]** | TRM: "Only the DMA port has access to the AFIFO" (Table 23-9 note, p. 1107); AB-sync PaRAM values in `hardware_notes` §1.4 |
| 34 | **[U6]** `06` §3.3, `08` R10 | C67x DSPLIB v2.00 `dsp67x.lib` is TI COFF; the only installed compiler, CGT 8.1.3, is ELF-only (README line 112) → **link would fail** | **blocker** | Yes (PROPOSED CHANGE – confirm) | Use the installed C674x DSPLIB 3.4.0.0 (`dsplib.ae674`); paths and settings in `hardware_notes` §3.3 |
| 35 | **[U6]** `06` §3.3, `07` T11 | C674x `DSPF_sp_fir_gen` needs nh and nr multiples of 4 | minor | Yes | Benchmark G padded to 24 taps (775 cycles) |
| 36 | **[U6]** `06` §3.1 | Read FIFO must be enabled before the McASP leaves reset; S19's `Init_McASP0()` has no FIFO step | major | Documented | Write RFIFOCTL right after `GBLCTL = 0` [TRM p. 1160] |
| 37 | **[U6]** user item 5 | Fallback I/O for "no external input" was not in the pack | minor | Yes | `hardware_notes` §11, `06` §3.6, `07` T16, `08` R16 |

**Traceability scan:**

- Apart from items 12 and 14 (now fixed), no number was found that was neither cited nor labelled.
- Code size (< 64 KB) and cycles-per-op (1–5) remain **labelled ASSUMPTIONS**. They become measurements on the board.

**Correctness re-check** (`calc/review_check_output.txt`). All of these were recomputed independently:

- Mode A delay 375 samples (both the recursion and S3 eq. 15).
- Alignment pads 365/165/65/15.
- Codec delay 0.79 ms and the totals 8.60/9.27/9.94 ms.
- **[U4]** FIFO cases: Mode A 8.81/10.15 ms, Mode B 7.67/9.00 ms.
- **[U5]** 64 Write-FIFO words = 1.33 ms with one word per sample period (0.67 ms only if L and R used separate words); codec 24.576 MHz/(128·4) = 48 000 Hz; GEL PLL settings give 300 and 456 MHz; biquad pole rule fails for our HPF.
- OLA condition L + M − 1 = 256 = N.
- Mode B latency 7.46 ms.
- Ops 61/sample, single-rate 313, saving 5.1×.
- Crossovers 6000/3000/1500/750 Hz.
- Kaiser length 20.5 → 21.
- All 15 half-gain band values (N2, N3, S2).
- 30 dB cap respected.
- WDRC α values 0.0336 and 0.0146.

**Feasibility on the LCDK (Part 1 facts):**

| Item | Status | Source |
|---|---|---|
| 48 kHz on the codec | Supported | S13 p. 1, Table 10-1 |
| 48 kHz on the LCDK | Used by S19 | S19 |
| Audio framing | **[U4]** DSP mode, codec master, McASP slave burst (as S19) | S19; S12 sheets 7, 10 |
| DMA events | **[U4]** EDMA3 events 0 (RX) / 1 (TX); MCASP0_INT (61) for errors | S8 Table 6-12, Table 6-6 |
| Memory | ≈ 15 KB of 256 KB L2 | — |
| CPU | **[U4]** ≤ 10.2 % worst case (300 MHz) | `cpu_check.py` |
| Emulator | External, 14-pin JTAG | S11 |
| Jack wiring / codec clock | **[U4]** Found: LINE OUT on line drivers; MCLK 24.576 MHz | S12 sheet 10 |

---

## c) Final confirmed design spec

| Area | Item | Value | Basis |
|---|---|---|---|
| Hardware | Board / DSP | TI LCDK, TMS320C6748 (C674x, fixed + floating point, 8 units, 2 SP MACs/cycle) | S8 p. 1; S9 Table 2-2 |
| | CPU clock | **[U6] 300 MHz** set by TI's `C6748_LCDK.gel` (and the book GEL); confirm by PLLC0 read-out + TSCL | TRM §7.3; S29 |
| | Codec / interface | **[U4]** AIC3106 on I2C0, address 0x18; MCLK 24.576 MHz, PLL bypassed, Q = 4 → 48 kHz; codec master, DSP mode 16-bit; McASP0 slave, AXR13 TX / AXR14 RX | S12 sheets 7, 10; S13; S19 |
| | Analog I/O | LINE IN → LINE1L+/R+ (regs 19/22 = 0x04); MIC IN → MIC3L/R; LINE OUT ← LEFT_LO+/RIGHT_LO+ (regs 82/92, 86/93); headphones need an amp | S12 sheet 10; S13 |
| | I/O servicing | **[U5]** EDMA3 events 0/1, 4-sample ping-pong; **Read FIFO ON (RNUMEVT 4), Write FIFO OFF** (DECIDED); RX 4 words/event, TX 1 word/event | S14 §2.4.4; S8 Table 6-12 |
| | Board support code | **[U6]** `papers/LCDK6748_Support_DSP.c` (diffed: only adds `Config_LCDK6748()`), S19 common files, TI target `lcdkc6748.xml` / `C6748_LCDK.gel` | `hardware_notes` §10 |
| | DSP library | **[U6] C674x DSPLIB 3.4.0.0**, `C:\ti\dsplib_c674x_3_4_0_0\packages` (include) + `dsplib.ae674` (link) | S28; S30 |
| | I/O modes | **[U6]** `IO_LIVE` (default), `IO_STORED_LINEOUT`, `IO_INTERNAL` | `06` §3.6 |
| | Controls | S2 (GPIO2[4]) = mode; S3 (GPIO2[5]) = audiogram preset; LED D4 = mode; D5 = clip + preset blink; **D6 = CPU-busy scope pin**; D7 = AMUTE (**[U6] decided**); LED pin-mux PINMUX13[15:8] = 88h, PINMUX5[15:12] = 8h (TRM p. 247, 230) | S11 Tables 7–8; S19; DESIGN CHOICE |
| | Debug | External XDS emulator, 14-pin JTAG; cycles via TSCL | S11; S9 §2.9.14 |
| Signal | Sample rate | 48 kHz | DEFAULT |
| | Input HPF | 4th-order Butterworth 100 Hz, bilinear, 2 biquads (plain C, DF-II-T) | Calculated |
| Mode A | Structure | 4-level complementary octave tree, 5 bands | DESIGN CHOICE |
| | Crossovers | 750 Hz, 1.5 kHz, 3 kHz, 6 kHz (fs_k/8) | Calculated |
| | Band rates / decimation | 48/24/12/6/3 kHz; D = 1/2/4/8/16 | Calculated |
| | G | 21-tap Kaiser (β 4.5) lowpass, stopband 52.5 dB | Calculated |
| | F | 31-tap half-band (17 non-zero), stopband 51.1 dB | Calculated |
| | Reconstruction | Ripple +0.020/−0.010 dB with unity gains | Simulated |
| | Delay | 375 samples = 7.81 ms; alignment pads 365/165/65/15 | Calculated; S3 eq. 15 |
| | Latency | **[U5] 8.81 ms** (default); 8.60 ms FIFO off | `latency_check.py`; S13, S14 |
| Mode B | FIR | M = 129 by frequency sampling (372.1 Hz grid) | DESIGN CHOICE |
| | OLA | L = 128, N = 256 (L + M − 1 = 256), `DSPF_sp_fftSPxSP`/`ifftSPxSP` from the **C674x DSPLIB** (1965/1985 cycles; ifft scales 1/N) | S28 |
| | Latency | **[U5] 7.67 ms** (default); 7.46 ms FIFO off (model; to be measured) | `latency_check.py` (ASSUMPTION model) |
| Gains | Audiogram / rule | Bisgaard N3; half-gain (Lybarger via Venema); 30 dB cap | S26 T2; S27 |
| | Band gains B5→B1 | 30.00 / 30.00 / 25.36 / 20.36 / 17.50 dB | Our calculation |
| | Presets | N3 half (default), N2 half, Bisgaard S2 half, bypass | S26 T2/T4 |
| | Accuracy | N3: Mode A 1.53 dB, Mode B 0.38 dB. Bisgaard S2: Mode A 6.82 dB (limitation), Mode B 0.49 dB | Simulated |
| Cost | CPU | Mode A 1.7–6.7 %; **[U6]** Mode B 1.7–3.3 % at 456 MHz (≤ 10.2 % / 5.0 % at 300 MHz) | `cpu_check.py` (Updates 4–6) |
| | Ops | 61 ops/sample bank (S3 eq. 16: 31–51 multiplies); multirate saving 5.1× | Calculated |
| | Memory | ≈ 15 KB internal data (L2); 1.92 MB capture in DDR2 | Calculated; S8 |
| Extras | Optional | WDRC (patent eqs. 1, 6, 7); minimum-phase filters; larger EDMA blocks; DSPLIB benchmarks | — |

---

## d) Open decisions for you

| # | Decision (status) | Recommendation | Why |
|---|---|---|---|
| 1 | fs = 48 kHz (DEFAULT – confirm) | **Accept** | Crossovers land on audiometric frequencies; codec and S19 code support it |
| 2 | 5 bands (DEFAULT – confirm) | **Accept** | 6 bands would push latency to ≈ 16.9 ms with linear phase |
| 3 | Mode B M/L/N = 129/128/256 (DEFAULT – confirm) | **Accept** | Meets the OLA condition exactly, 7.46 ms |
| 4 | Audiogram Bisgaard N3 + half-gain, with N2 and Bisgaard S2 presets (DEFAULT – confirm) | **Accept**; put all presets on button S3 | Standard, citable audiograms |
| 5 | Steep loss handled by Mode B, not Mode A (PROPOSED CHANGE – confirm, scope only) | **Accept** | 5 octave bands cannot follow a 15.7 dB step; Mode B can |
| 6 | EDMA + Read FIFO for both modes, 4-sample blocks | **[U5] Decided** | Fallback = S19 `DSP_Init()` per-sample interrupt with FIFO off (8.60 ms) |
| 7 | WDRC (OPTIONAL – confirm) | **Defer to after Week 8**; build only if T2–T5 pass | Core first; WDRC adds risk but little syllabus |
| 8 | ANSI class 2 (60 dB) stopband | **Keep 52 dB** unless faculty require class 2 | 60 dB costs latency (10.79 ms) |
| 9 | 12-week timeline (DEFAULT – confirm) | Confirm your semester length | Affects buffer weeks |
| 10 | CPU clock | **[U6] Keep the GEL's 300 MHz**; confirm on the board | Worst case 10.2 % at 300 MHz |
| 11 | Write FIFO on or off | **[U5] Decided: off** (Read FIFO on) | 8.81 / 7.67 ms |
| 12 | Listening device | **[U5] Decided: from the lab** – powered speakers or a headphone amplifier on LINE OUT | Headphone drivers are not wired on the LCDK (S12 sheet 10); line drivers into 16–32 Ω through 10 µF cut bass below ≈ 0.5–1 kHz |
| 13 | LED plan | **[U6] Decided:** D4 mode, D5 clip + preset blink, D6 scope pin, D7 AMUTE | — |
| 14 | **[U5]** Processor SDK | **Decided: skip** | Nothing in the plan needs it (`hardware_notes` §9) |
| 15 | **[U6]** DSP library (PROPOSED CHANGE – confirm) | **C674x DSPLIB 3.4.0.0** | The C67x v2.00 cannot be linked by the installed ELF-only compiler |

---

## e) Remaining gaps

1. **[U6] All documents and tools are in hand** (S12, S19 package + replacement file, TRM S10, C674x DSPLIB, CCS 7.2/CGT 8.1.3, emulator and speakers from the lab). Nothing left to download for coding or bring-up.
2. **TRM (S10) not supplied.** It is needed for the PLL, GPIO and pin-mux register details. The S19 or Processor SDK code covers these in practice.
3. **Still to measure on the board:** CPU clock (PLLC0 read-out, expect 300 MHz), Read FIFO + EDMA working with the derived PaRAM values, LEDs with the new pin-mux, Mode B latency model, ifft self-check (expected gain 1).
4. **[U6] Verified:** the C674x DSPLIB is installed; its reference ifft scales by 1/N (gcc test). The optimized assembly is verified by TI's own test driver, not by us.
5. **Missing PDFs:** S5, S6, S7 (papers) and S10 (TI). **[U4]** S12 now saved.
6. **Originals cited but not read:** Lybarger, Byrne & Dillon, Stone & Moore, and the ANSI S1.11/S3.22 standards.
7. **Not run:** MATLAB (numbers come from Python/SciPy). Stage 1 of `06` repeats them in MATLAB.
8. **Viva preparation:** each team member should be able to explain the complementary tree (`05` §2), the delay formula (S3 eq. 15), why DSPLIB is not used per sample, and the steep-loss limitation.
