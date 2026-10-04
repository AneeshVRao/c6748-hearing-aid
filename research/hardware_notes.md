# Hardware Notes – TMS320C6748 LCDK, AIC3106 codec, McASP, DSPLIB

**How to read the citations.** Each fact cites a document ID (from `02_sources.md`) plus a page, section or table.

- Page numbers are the PDF page. For TI user guides they match the printed page.
- For S15 (DSPLIB) the printed page label, such as "p. 4-41", is given.
- **NOT FOUND – check on board** means the attached documents do not contain the fact.

**Update 4 (4 Oct 2026):** the LCDK schematic **S12** (`papers/sprcaf4.zip`, unzipped to `papers/S12_SPRCAF4_LCDK_schematics/`) is now read. It contains the schematic PDF `C6748 LC DEV KIT VER  A7E.pdf` (12 sheets, title "OMAP-L138/C6748 LC Dev Kit", Rev A7E, dated 18 May 2015), the BOM and layout files. Citations below give **S12 sheet number + net name**. The board-wiring gaps from Update 3 are now closed. S11 Table 15 lists A7A as the active board revision; the schematic says A7E. Check the revision printed on your board.

**Update 5 (4 Oct 2026):** the S19 code package (`papers/code_2017_02_05.zip`, unzipped to `papers/S19_code_2017_02_05/`) and the DSPLIB package (`papers/sprc121.zip`, unzipped to `papers/DSPLIB_sprc121/`) are now read. Package citations give **file + function + line** (paths relative to `papers/S19_code_2017_02_05/code/`). Findings are in **§9** (S19 package) and **§3.2** (DSPLIB package). The McASP default is now **Read FIFO ON, Write FIFO OFF** (your decision).

**Update 6 (4 Oct 2026):** the TRM **S10** (`papers/spruh79c.pdf`, SPRUH79C, Sept 2016) and the replacement board file (`papers/LCDK6748_Support_DSP.c`) are now read, and the PC's tool folders were inspected (`C:\CCStudio`, `C:\ti`). TRM citations give **section + PDF page** (printed page = PDF page). **Correction:** the Update 5 "GEL PLL0 bug" was wrong — see §1.7. New sections: §3.3 (library locations and CCS settings), §10 (board-file comparison), §11 (I/O modes).

**Documents read (all saved in `papers/`):**

| ID | Document |
|---|---|
| S8 | SPRS590G – C6748 datasheet |
| S9 | SPRUFE8B – C674x CPU and instruction set guide |
| S11 | SPRUIL2A – LCDK user's guide |
| S13 | SLAS509G – AIC3106 codec datasheet |
| S14 | SPRUFM1 – McASP user's guide |
| S15 | SPRU657C – C67x DSPLIB reference |
| S16 | SPRA947A – DSPLIB examples |
| S12 | SPRCAF4 – LCDK schematic, rev A7E (Update 4) |
| S19 pkg | `code_2017_02_05.zip` – Welch/Wright/Morrow book code: `common_code/LCDK/*`, LCDK GEL file, EDMA example (Update 5) |
| DSPLIB pkg | `sprc121.zip` → `C67xDSPLIB_v200.exe` – **C67x** DSPLIB **v2.00** (2005), with SPRU657B and headers (Update 5) |

**Jargon used below.**

| Term | Meaning |
|---|---|
| McASP | The C6748's audio serial port |
| I2S | The standard two-channel (left/right) audio serial format |
| I2C | A two-wire control bus used to write the codec's settings |
| EDMA | A DMA engine that moves samples without the CPU |
| MCLK | The codec's master clock |
| fS | The audio sample rate |
| Delay slots | Extra cycles before an instruction's result is ready |

---

## 1. Board and audio path

### 1.1 How the codec connects (now from the schematic, S12)

| Fact | Value | Source |
|---|---|---|
| Codec part | **U22 = TLV320AIC3106IRGZ** | S12 sheet 10 ("STEREO AUDIO CODEC") |
| Codec ↔ DSP data link | McASP0 | S12 sheets 7 and 10; S11 Fig. 1 |
| Serial data DSP → codec | Net **AXR13** → codec **DIN** (pin 40). DSP ball B3 = AXR13 | S12 sheet 10 (net AXR13), sheet 7; S8 p. 47 (ball B3) |
| Serial data codec → DSP | Codec **DOUT** (pin 41) → net **AXR14**. DSP ball B4 = AXR14 | S12 sheet 10 (net AXR14), sheet 7; S8 p. 47 |
| Bit clock | Codec **BCLK** (pin 38) ↔ net **AIC_BCLK** ↔ 33 Ω R95 ↔ DSP ball B1 = **ACLKX** | S12 sheets 7, 10; S8 p. 47 (B1 = ACLKX, McASP0 transmit bit clock) |
| Word clock (frame sync) | Codec **WCLK** (pin 39) ↔ net **AIC_WCLK** ↔ 33 Ω R94 ↔ DSP ball B2 = **AFSX** | S12 sheets 7, 10; S8 p. 47 (B2 = AFSX) |
| Codec master clock | Oscillator **Y5, CB3LV-3I-24M5760 (24.576 MHz)** → 33 Ω R164 → net **AIC_MCLK** → codec **MCLK** (pin 37) **and** DSP **AHCLKX** (ball A3) | S12 sheet 10 (Y5, net AIC_MCLK), sheet 7; S8 p. 47 (A3 = AHCLKX) |
| Codec control bus | **I2C0**: nets **SPI1_SCSn_6/I2C0_SDA** → codec SDA (pin 2) and **SPI1_SCSn_7/I2C0_SCL** → codec SCL (pin 1). DSP pins listed in S8 p. 35 | S12 sheets 7, 10; S8 p. 35 |
| Control mode pin | Codec SELECT (pin 43) pulled low (R162 2 kΩ to ground; pull-up R160 not populated) → **I2C mode** | S12 sheet 10; S13 pin table (SELECT: 1 = SPI, 0 = I2C) |
| I2C address | MFP0 (pin 45) and MFP1 (pin 46) pulled to ground (R159, R158, 2 kΩ) → address **0011000b = 0x18** | S12 sheet 10; S13 Table 10-7, p. 44 |
| Codec reset | Codec RESET (pin 33) ← net **PHP_RSTn** | S12 sheet 10 |
| **LINE IN** jack | **J10 upper** (`AUDIO_IN`, stacked 3.5 mm CK3.5-1230-08). Ring → R152 (0 Ω) → C172 (0.1 µF) → **LINE1L+** (pin 3). Tip → R154 (0 Ω) → C176 (0.1 µF) → **LINE1R+** (pin 5). LINE1L−, LINE1R− and all LINE2 pins are not connected → **single-ended LINE1** | S12 sheet 10 (J10, nets as listed) |
| **LINE OUT** jack | **J10 lower** (`AUDIO_OUT`). Net **AUDIO_LEFT** ← C178 (10 µF) ← **LEFT_LO+** (pin 29). Net **AUDIO_RIGHT** ← C179 (10 µF) ← **RIGHT_LO+** (pin 31). 20 kΩ to ground on each (R156/R157). LEFT_LO−/RIGHT_LO− not connected → **single-ended line outputs** | S12 sheet 10 |
| Headphone drivers | **HPLOUT, HPLCOM, HPROUT, HPRCOM and MONO_LO± are not connected** (marked no-connect) | S12 sheet 10 |
| **MIC IN** jack | **J11** (`MIC_IN`). Nets **MIC_LEFT** → **MIC3L** (pin 11), **MIC_RIGHT** → **MIC3R** (pin 14), **MIC_DET** → MICDET (pin 12), **MIC_BIAS** ← MICBIAS (pin 13) | S12 sheet 10 |

**Effect on our design (line out vs headphones).**

- The LINE OUT jack is driven by the codec's **line drivers**. These are specified for a **10 kΩ load** (S13 p. 6).
- The headphone drivers (16 Ω capable, S13 p. 6) are **not wired** to any jack.
- Plugging 16–32 Ω headphones into LINE OUT therefore overloads the line driver. The 10 µF coupling capacitor also forms a high-pass filter with the headphone: f_c = 1/(2π·R·C) ≈ **497 Hz for 32 Ω** and **995 Hz for 16 Ω** (our calculation). That would remove most of our B1/B2 bands.
- **Use powered speakers or a headphone amplifier on LINE OUT** (now required, see R14).

### 1.2 Sample rate and codec clock

| Fact | Value | Source |
|---|---|---|
| Codec sample rates | 8 kHz to 96 kHz (ADC and DAC) | S13 p. 1, p. 3 |
| Rate equation without the codec PLL | fS(ref) = CLKDIV_IN / (128 × Q), Q = 2…17 | S13 eq. (1), p. 22 |
| Rate equation with the PLL | fS(ref) = (PLLCLK_IN × K × R) / (2048 × P) | S13 eq. (2), p. 23 |
| **MCLK on the LCDK** | **24.576 MHz** (oscillator Y5) | S12 sheet 10 |
| **48 kHz setting** | PLL **off**, CLKDIV_IN = MCLK, **Q = 4**: 24.576 MHz / (128 × 4) = **48 000 Hz exactly** | Our calculation from S13 eq. (1). S19 also bypasses the PLL (reg 101 = 0x01 → CODEC_CLKIN = CLKDIV_OUT; reg 102 = 0x02 → CLKDIV_IN = MCLK) |
| Who drives BCLK/WCLK | **The schematic allows either.** The pins are bidirectional on both ends. **S19 makes the codec the master** (reg 8 = 0xF0: BCLK and WCLK are outputs) and leaves the McASP clocks external (ACLKXCTL = AHCLKXCTL = AFSXCTL = 0; PDIR makes only AXR13 an output) | S12 sheets 7, 10; S19 code; S13 T10-16 |
| Anti-alias filter inside the codec | ADC decimation filter −3 dB bandwidth 0.45 fS (21.6 kHz at 48 kHz) | S13 p. 25 |
| Codec group delay | ADC 17/fS, DAC 21/fS (0.79 ms at 48 kHz) | S13 p. 8–9, p. 25, p. 29 |

### 1.3 Codec registers for line-in → ADC → DAC → line-out (Page 0)

**Value sources.** "S19 value" is copied from `LCDK6748_Support_DSP.c` (§8). **Update 5:** every value in this table was re-checked line by line against `common_code/LCDK/LCDK_Support_DSP.c`, `Init_AIC3106()`, lines 430–524 (line-input branch lines 442–454); all match (§9). Each value was checked against the bit meanings in S13. "Our value" is derived by us from S13 and S12. Choices are now fixed by the schematic.

| Reg | Name (S13 table, page) | Value to use | Basis |
|---|---|---|---|
| 0 | Page Select (T10-8, p. 46) | 0x00 | S19 value |
| 1 | Software Reset (T10-9, p. 46) | 0x80 | S19 value |
| 2 | Codec Sample Rate Select (T10-10, p. 46–47) | **0x00** (ADC and DAC at fS(ref)/1) | **Confirmed (Update 5):** `REG_CODEC_SAMPLE_RATE_48KHZ 0x00` (`common_code/LCDK/AIC3106.h` line 129), written by `SetSampleRate_AIC3106()` (`LCDK_Support_DSP.c` lines 620–625) |
| 3 | PLL Programming A (T10-11, p. 47) | **0x20** (PLL off, Q = 4) | **Confirmed (Update 5):** `REG_PLL_A_48KHZ 0x20 // PLL disabled, Q = 4` (`AIC3106.h` line 128); header comment states MCLK 24.576 MHz and Fs(ref) = MCLK/(128·Q) (lines 123–124). 48 kHz is selected in `DSP_Config.h` (`SampleRateSetting AIC3106Fs48kHz`) |
| 7 | Codec Datapath Setup (T10-15, p. 48) | 0x0A (fS(ref) = 48 kHz; left DAC = left, right DAC = right) | S19 value; matches S13 bits |
| 8 | Serial Interface Control A (T10-16, p. 49) | **0xF0** (codec drives BCLK and WCLK; DOUT tri-state when idle; clocks keep running) | S19 value |
| 9 | Serial Interface Control B (T10-17, p. 49) | **0x40** (**DSP mode**, 16-bit words) | S19 value. **Replaces the pack's earlier "I2S" plan** |
| 10 | Serial Interface Control C (T10-18, p. 50) | 0x00 (no offset) | S19 value |
| 15 / 16 | Left / Right ADC PGA (T10-23/24, p. 52) | 0x00 (un-muted, 0 dB) for line input | S19 value (line branch) |
| **19 / 22** | **LINE1L→Left ADC / LINE1R→Right ADC** (T10-27/30, p. 54–55) | **0x04** (single-ended, 0 dB, connected, ADC powered) | S19 value (line branch). **Chosen over regs 20/23 because the jack is wired to LINE1 (S12 sheet 10)** |
| 17 / 18 | MIC3L/R→Left/Right ADC (T10-25/26, p. 53) | 0xFF (MIC3 disconnected) for line input. For the MIC IN jack, S19 uses 0x0F / 0xF0 with regs 19/22 = 0x7C and MICBIAS (reg 25) = 0x80 | S19 values |
| 37 | DAC Power / Output Driver (T10-45, p. 61) | 0xE0 (both DACs on; HPLCOM single-ended) | S19 value |
| 43 / 44 | Left / Right DAC Volume (T10-51/52, p. 63) | 0x00 (un-muted, 0 dB) | S19 value |
| **82 / 92** | **DAC_L1→LEFT_LOP / DAC_R1→RIGHT_LOP** (T10-91/101, p. 72–73) | **0x80** (routed, 0 dB) | S19 value. **Required: the LINE OUT jack is on LEFT_LO+/RIGHT_LO+ (S12 sheet 10)** |
| **86 / 93** | LEFT_LOP / RIGHT_LOP Output Level (T10-95/102, p. 72–74) | **0x09** (0 dB, un-muted, D0 = 1 is a read-only status bit) | S19 value |
| 47 / 64, 51 / 65 | DAC→HPLOUT/HPROUT and HP levels | S19 writes 0x80 / 0x09. **Harmless but unused**: HP drivers are not wired (S12 sheet 10). Can be left out | S19 value; S12 |
| 101 | Additional GPIO Control B (T10-110, p. 78) | 0x01 (CODEC_CLKIN = CLKDIV_OUT, i.e. PLL bypassed) | S19 value |
| 102 | Clock Generation Control (T10-111, p. 78) | 0x02 (CLKDIV_IN = MCLK) | S19 value |

### 1.4 McASP setup (framing from S19; Read FIFO ON, Write FIFO OFF by default)

| Step / fact | Detail | Source |
|---|---|---|
| Framing on the LCDK (as S19 does it) | Codec = master in DSP mode, 16-bit. McASP = slave: clocks and frame sync external, **burst mode**, 32-bit slot, MSB first, **0-bit delay** (XFMT = RFMT = 0x000080F8; AFSXCTL = AFSRCTL = 0). SRCTL13 = transmit, SRCTL14 = receive. RINTCTL = 0x01 (overrun interrupt), XINTCTL = 0x20 (data interrupt) | S19 code |
| What one McASP word holds | With 16-bit DSP-mode data and a 32-bit slot, **one 32-bit word carries left + right**, i.e. one McASP transfer per sample period | Our reading of S19 settings + S13 DSP mode |
| Earlier pack plan (I2S, 2 slots, DATDLY = 1) | Still valid in principle (S14 §1.5.1.2, p. 17, p. 30), but **we now follow S19** because it is proven on this board | DESIGN CHOICE |
| Mandatory init order | Same 10 steps as before: GBLCTL = 0 → **configure AFIFO (WFIFOCTL/RFIFOCTL)** → receive regs → transmit regs → SRCTLn → PFUNC/PDIR… → release clocks → start DMA → clear status, release serializers → release state machines → release frame sync. Read back GBLCTL after each step | S14 §2.4.1.2, p. 35–37; §2.4.1.4 |
| **AFIFO (DEFAULT, decided in Update 5)** | **Read FIFO ON:** RNUMDMA = 1 word (one serializer), **RNUMEVT = 4 words**; set RNUMDMA/RNUMEVT before RENA (S14 §3.46 note, p. 122). **Write FIFO OFF:** WFIFOCTL.WENA = 0, so transmit DMA requests pass straight through to EDMA (S14 §2.4.4.1, p. 51) | S14 §2.4.4, §3.44–3.47; DECIDED |
| AFIFO servicing | The AFIFO issues **DMA requests** to the host or DMA controller. It is meant to be serviced by **EDMA**, not per-sample CPU interrupts | S14 §2.4.4.1–2.4.4.2, p. 51–52 |
| Resulting I/O scheme | **EDMA3 events 0 (McASP0 RX) and 1 (McASP0 TX)**, ping-pong buffers of **4 samples**, one EDMA completion interrupt per block (S19 `DSP_Init_EDMA()` uses EDMA3_CC0_INT1). S19's EDMA path does not enable the AFIFO (no FIFOCTL writes found), so the FIFO set-up is ours | S8 Table 6-12, p. 101; S19 |
| **EDMA parameters (Update 6, from the TRM)** | Each Read-FIFO request is for RNUMEVT = 4 words (TRM §23, p. 1090). In an **AB-synchronised** transfer one event moves BCNT arrays of ACNT bytes (TRM §16.2.2.2, p. 555; OPT.SYNCDIM bit 2 = 1, Table 16-15, p. 612). **RX PaRAM (per 4-sample block):** OPT = TCINTEN (bit 20, p. 611) + TCC 0 + SYNCDIM 1 = **0x0010 0004**; SRC = **0x01D0 2000** (DMA port); ACNT = 4, BCNT = 4 (word +8h = 0x0004 0004); DST = ping/pong buffer; SRCBIDX = 0, DSTBIDX = 4 (word +10h = 0x0004 0000); CCNT = 1; LINK = the other buffer's PaRAM set. **TX PaRAM (Write FIFO off, A-synchronised, one word per event as in S19 `ISRs.c` line 36):** OPT = TCC 1, no interrupt = **0x0000 1000**; SRC = buffer, DST = 0x01D0 2000; ACNT = 4, BCNT = 4, SRCBIDX = 4, DSTBIDX = 0, CCNT = 1; linked. Use increment mode with BIDX = 0 for the port, not SAM/DAM constant mode: no C674x peripheral supports constant mode (Table 16-15 note, p. 612). PaRAM layout: TRM Figure 16-7, p. 556. Events 0 = AREVT0, 1 = AXEVT0 (TRM Table 23-6, p. 1103) | TRM S10; values are our derivation from those pages (DESIGN CHOICE) |
| **Data port (confirmed in Update 6)** | "The AFIFO cannot be used with the peripheral configuration port. Only the DMA port has access to the AFIFO" (TRM Table 23-9 note, p. 1107). DMA-port RBUF/XBUF at offset 2000h; reads/writes go through it only when RBUSEL/XBUSEL = 0 (TRM Table 23-8, p. 1107; RBUSEL = RFMT bit 3, p. 1130). So with the Read FIFO on, **RFMT = XFMT = 0x0000 80F0** and EDMA uses **0x01D0 2000**; S19's 0x0000 80F8 (CFG bus) cannot work with the FIFO | TRM S10 §23 |
| **RFIFOCTL (Update 6)** | Address 0x01D0 1018 (AFIFO base 0x01D0 1000 + 18h; TRM Table 23-9, p. 1107; S8 memory map). Write **0x0000 0401** (RNUMEVT = 4, RNUMDMA = 1), then **0x0001 0401** (RENA = 1). RNUMDMA must equal the number of receive serializers (1); RNUMEVT a multiple of it; both set before RENA; **the Read FIFO must be enabled before the McASP is taken out of reset** (TRM Table 23-49, p. 1160). WFIFOCTL (0x01D0 1010) left at reset, WENA = 0 | TRM S10 |
| Write-FIFO latency cost (why it is off) | The Write FIFO "attempts to stay filled" (S14 p. 52). It holds up to **64 words** (256 bytes = 64 words with one data pin, S14 p. 12). **With S19 framing one word = one sample period (L+R packed)**, so 64 words = **64/48 000 s = 1.33 ms**, whatever the threshold. The "0.67 ms" figure is correct only for I2S with L and R in separate words (2 words per sample period); that is not how S19 runs the LCDK (§9 item 6). The Read FIFO tries to stay empty, so it adds ≤ RNUMEVT = 4 samples | S14 p. 12, p. 52; our calculation |
| Benefit | Long tolerance to service delays (up to ~60 sample periods). The FFT interrupt-off time (≤ 9.7 µs) is no longer a risk | S14 p. 12; our calculation |
| Error flags | Transmit underrun / receive overrun in XSTAT/RSTAT | S14 §2.4.7, p. 59 |
| Debug caution | Do not open XBUF/RBUF in a CCS memory window | S14 p. 36 |

**Latency effect of the FIFO** (`calc/latency_check.py`):

| Configuration | Extra I/O delay | Mode A total | Mode B total |
|---|---|---|---|
| FIFO off, per-sample interrupt (Update 3 default) | 0 | 8.60 ms | 7.46 ms |
| **Read FIFO on (4) + EDMA blocks of 4, Write FIFO off — DEFAULT (Update 5)** | 10 samples = 0.21 ms | **8.81 ms** | **7.67 ms** |
| Read + Write FIFO on (threshold 4) + EDMA blocks of 4 (Update 4 default, rejected) | 74 samples = 1.54 ms | 10.15 ms (over the 10 ms target) | 9.00 ms |

The model is an ASSUMPTION: input ≤ 4 samples (RFIFO wait = one block fill, because RNUMEVT = B = 4), processing ≤ 1 block, Write FIFO ≤ 64 when on, XBUF/shift ≈ 2.

**Decision (Update 5).** You accepted the proposed change: **Read FIFO ON (threshold 4), Write FIFO OFF** is the default everywhere. Both modes meet the 10 ms target (8.81 / 7.67 ms). The Read FIFO still gives about 60 sample periods of input tolerance (64 − 4 words).

### 1.5 Buttons, switches and LEDs (S11, confirmed in S12)

| Item | Signal | Behaviour | Use in our project (DESIGN CHOICE) | Source |
|---|---|---|---|---|
| Push button S2 | GPIO2[4] | Pulled low when pressed | **Toggle Mode A / Mode B** | S11 Table 7, §3.1.1, p. 7 |
| Push button S3 | GPIO2[5] | Pulled low when pressed | **Step through audiogram presets** (N3 → N2 → Bisgaard S2 → bypass) | S11 Table 7, p. 7 |
| S1 | Reset | — | (do not use) | S11 Table 7 |
| DIP SW1 switches 5–8 | GPIO0[1]–GPIO0[4] | ON = low, OFF = high | Alternative static selection: 2 bits mode, 2 bits audiogram | S11 Table 6, §3.1, p. 6 |
| DIP SW1 switches 1–4 | Boot mode | UART2 / NAND16 / MMC-SD | Leave as set for your boot method | S11 Table 5, p. 6 |
| LED D4 | GPIO6[13] | Lit when high | Mode indicator (on = Mode B) | S11 Table 8, p. 7 |
| LED D5 | GPIO6[12] | Lit when high | Clip/limiter indicator; preset shown by blink count (Update 5) | S11 Table 8 |
| LED D6 | GPIO2[12] | Lit when high | **CPU-busy pin for the scope test (T6)** (Update 5) | S11 Table 8 |
| LED D7 | GPIO0[9] | Lit when high | **Not used**: S19's pin-mux selects AMUTE on this pin (Update 5) | S11 Table 8; `Config_LCDK6748()` |

**Schematic check (S12):**

- Push buttons S2/S3 sit on sheet 4 (nets **GPIO2-4**, **GPIO2-5**).
- GPIO2[4] shares its DSP pin with **EMA_CASn** (sheet 6, `EMA_CASn/GPIO2[4]`), so the pin-mux must select GPIO.
- LED nets **GPIO2-12** (pin `SPI1_ENAn/GPIO2[12]`) and **GPIO0-9** (pin `AMUTE/UART2_RTSn/GPIO0[9]`) are on sheets 7 and 12.

**Pin-mux after Update 5:**

- **Buttons need no pin-mux.** "The PINMUX registers have no effect on input from a pin" (S8 §3.6, PDF p. 26). So S2/S3 (GPIO2[4]/[5]) can be read even though GPIO2[4] shares its pin with EMA_CASn.
- **LEDs do need pin-mux** (default "none", output tri-stated; S8 §3.6, p. 26). **Values now found (Update 6, TRM):**
  - D4 = GP6[13]: **PINMUX13 bits 11–8 = 8h** (TRM Table 10-35, p. 247).
  - D5 = GP6[12]: **PINMUX13 bits 15–12 = 8h** (p. 247).
  - D6 = GP2[12]: **PINMUX5 bits 15–12 = 8h** (TRM Table 10-27, p. 230).
  - Code: `PINMUX13 = (PINMUX13 & ~0x0000FF00) | 0x00008800;` and `PINMUX5 = (PINMUX5 & ~0x0000F000) | 0x00008000;` (PINMUX13 at 0x01C1 4154, PINMUX5 at 0x01C1 4134; TRM SYSCFG register table, p. 207). Those pins' other functions (UHPI_HINT/HRDY, SPI1_ENA) are unused.
  - The GPIO module needs PSC1 LPSC 3 enabled (TRM Table 8-2, p. 166). Both GELs do this in `PSC_All_On()`; code that runs without a GEL must do it itself.
  - Then S19's `InitLEDs()`/`WriteLEDs()` work unchanged (DIR67 at GPIO base + 88h, SET_DATA67 + 90h; `OMAPL138_defines.h` lines 163–165 match the TRM GPIO register table, p. 902, and §19.3.3–19.3.5, p. 904–908).
- **LED D7 (DECIDED in Update 6).** `Config_LCDK6748()` in S19 sets PINMUX0 bits 24–27 to **AMUTE** (`LCDK6748_Support_DSP.c`, comment "Bits 24:27 - Select Amute"). That hands GPIO0[9] (LED D7) to the McASP. So D7 is not usable as a GPIO with S19's set-up. New LED plan: **D4 = mode, D5 = clip, D6 (GPIO2[12]) = CPU-busy scope pin; preset shown by blink count on D5** (DESIGN CHOICE). D7 unused. TRM Table 10-22 (p. 220) confirms PINMUX0 bits 27–24 = 1h selects AMUTE, 8h would select GP0[9].

### 1.6 Debug and emulator

- The **LCDK has no on-board emulator.** An external one is required (S11 §1.1 p. 3, note on p. 4).
- The connection is a **14-pin JTAG header** (S11 §1.1). It is drawn on S12 sheet 6 ("DSP MEMORY IF & JTAG", signals EMU0/EMU1).
- S11 Table 2 (p. 5) lists emulators: XDS100, XDS200, XDS510, XDS560, and XDS110 ("supported on C6748 LCDK only").
- CCS includes the LCDK GEL/XML files from CCSv6 onwards (S11 §6.3). GEL files are CCS start-up scripts that, among other things, set up the DDR memory.

### 1.7 CPU clock on the LCDK

| Fact | Source |
|---|---|
| LCDK features list a 456-MHz C674x DSP | S11 §1.1 |
| The TI AISgen config for NAND boot runs the CPU at **300 MHz** (DDR2 at 150 MHz) | S11 §3.5, p. 10 |
| Device grades: 375 and 456 MHz | S8 p. 1 |
| GEL default (S19 package `target_configuration/LCDK/OMAP-L138_LCDK.gel`) | `OnTargetConnect()` calls `Core_300MHz_mDDR_150MHz()` (line 246) → `Set_Core_300MHz()` = `device_PLL0(0,24,1,0,1,11,5)`, printed as "Core:300MHz" (lines 403–405). A 456 MHz menu entry also exists (`Set_Core_456MHz()`, `device_PLL0(0,18,0,…)`, lines 399–401) |
| DSP reference clock | ASE-24.000MHZ oscillator at OSCIN (S12 sheet 6) |
| **How the clock is set (TRM, Update 6)** | DSP clock = PLL0_SYSCLK1, ratio 1:1 (TRM Table 6-1, p. 118). PLLM: "Multiplier Value = PLLM + 1" (TRM Table 7-12, p. 145); PREDIV, PLLDIVn, POSTDIV: "Divider Value = RATIO + 1" (p. 145, 151–152). So **f_CPU = OSCIN × (PLLM+1) / ((PREDIV+1)·(POSTDIV+1)·(PLLDIV1+1))**. With the GEL's 300 MHz call (PLLM 24, POSTDIV 1, PLLDIV1 0, PREDIV left at 0): 24 × 25 / 2 = **300 MHz**; 456 MHz call: 24 × 19 = 456 MHz (our calculation). In bypass (PLLEN = 0) the system runs from OSCIN (TRM §7.2, p. 132) |
| **GEL "bug" from Update 5: RETRACTED (Update 6)** | Wrong. Line 732 (`PLL1_PLLCTL \|= 0x1;`) is the last line of **`device_PLL1()`** (starts line 667, "DDR PLL1 init"), where PLL1 is correct (PLL1 feeds DDR2/mDDR, TRM §7.2, p. 132). **`device_PLL0()`** (starts line 585) ends with `PLL0_PLLCTL \|= 0x1;` at **line 658**, which removes PLL0 from bypass as TRM §7.2.2.2 step 9 requires (p. 136). TI's own CCS 7.2 GEL `C:\ti\ccsv7\ccs_base\emulation\boards\lcdkc6748\gel\C6748_LCDK.gel` has the same structure (PLL0 enable line 645, PLL1 line 719) and the same default (`OnTargetConnect()` → `PSC_All_On()` + `Core_300MHz_mDDR_150MHz()`, lines 237–246). **Verdict: not a bug; no fix needed.** My Update 5 error came from reading two separate printouts (lines 574–632 and 730–746) as one function |
| How to read the actual clock (board check, Update 6) | In a CCS memory window read PLLC0 registers (TRM §7.3, p. 137): **PLLCTL 0x01C1 1100** (bit 0 PLLEN = 1 means PLL on; Table 7-8, p. 141), **PLLM 0x01C1 1110**, **PREDIV 0x01C1 1114**, **PLLDIV1 0x01C1 1118**, **POSTDIV 0x01C1 1128** (RATIO = bits 4–0). Put them in the formula above. Cross-check with TSCL: cycles counted over 48 000 audio samples = f_CPU. Expected: **300 MHz** with either GEL |
| Which GEL to use | **TI's `C6748_LCDK.gel`** (via the CCS 7.2 board file `ccs_base\common\targetdb\boards\lcdkc6748.xml` line 8). The book's `OMAP-L138_LCDK.gel` is written for the OMAP-L138 LCDK (it also wakes the DSP from the ARM side, `Wake_DSP()`, line 248). Both set 300 MHz |

The pack therefore keeps both 456 MHz and 300 MHz in every load estimate.

---

## 2. Processor facts and the syllabus

| Syllabus item | Fact | Source | Where it shows up in our project |
|---|---|---|---|
| **DSP architecture (VLIW)** | 8 functional units in 2 groups: .L, .S, .M, .D on each side. All 8 can be used every cycle. 64 general-purpose 32-bit registers (A0–A31, B0–B31) | S9 §2.3 and Table 2-2, p. 29; §2.2, p. 26; S8 p. 1 | Report chapter. The compiler packs up to 8 instructions per cycle |
| Unit roles | .L: arithmetic, compare, logic, conversions. .S: arithmetic, shifts, branches, SP/DP add/subtract. .M: multiplies. .D: loads/stores and address arithmetic | S9 Table 2-2, p. 29–30 | Explains why loads (.D) and MACs (.M) overlap in FIR loops |
| **Instruction packets** | Fetch packet = 8 instructions (32-bit words). Execute packet = 1–8 instructions issued in the same cycle | S9 §4.1.1–4.1.2, p. 577–578 | VLIW explanation |
| **Pipelining** | Fetch: PG, PS, PW, PR. Decode: DP, DC. Execute: E1–E5 | S9 §4.1, p. 577–579 | Report figure; `-o0` vs `-o3` cycle test (T6) |
| **Delay slots** | Single-cycle 0; 16×16 MPY 1; MPYSP/ADDSP 3; load (LDW) 4; branch (B) 5; ADDDP 6; MPYDP 9 | S9 Table 3-8, p. 73; MPY p. 316; MPYSP p. 350; ADDSP p. 130; LDW p. 299; B p. 151 | Explains why loops need unrolling and software pipelining (SPLOOP, S9 Ch. 7, p. 667) |
| **MAC hardware** | Two multiply units. Up to 2 SP×SP→SP per clock; four 16×16 or two 32×32 fixed multiplies per clock | S8 p. 1 | DSPLIB FIR cost ≈ nh·nr/2 cycles (S15 p. 4-41/4-43), i.e. 2 MACs/cycle |
| **Fixed vs floating point** | Supports 32-bit integer, IEEE single and double precision; superset of the C67x+ and C64x+ instruction sets | S8 p. 1 | Float build; Q15 compared in MATLAB |
| **Harvard architecture** | Separate program cache L1P (32 KB, direct mapped) and data cache L1D (32 KB, 2-way set-associative). L2 is unified (program + data) | S8 p. 3, p. 13 | Explained in report (the C674x is Harvard at L1, unified at L2) |
| **Memory** | L1P 32 KB and L1D 32 KB, each RAM or cache. L2 256 KB, split between RAM and cache. 128 KB shared RAM. DDR2 up to 256 MB address space (LCDK fits 128 MB) | S8 p. 1, p. 3; S11 §1.1 | Our data ≈ 15 KB (§6), fits in L2 RAM |
| Memory map | L2 0x0080 0000 (local) / 0x1180 0000 (global). Shared RAM 0x8000 0000. DDR2 0xC000 0000 | S8 Table 3-4, p. 20–22 (also quoted earlier in `04` §15) | Linker command file |
| Cache control registers | L2CFG 0x0184 0000, L1PCFG 0x0184 0020, L1DCFG 0x0184 0040 | S8 Table 3-2, p. 13 | Cache set-up |
| **Addressing modes** | Linear (default) or circular for registers A4–A7, B4–B7, set in the AMR register. Block size = 2^(N+1) **bytes** (BK0/BK1 fields) | S9 §2.8.3, p. 36; §3.9.2, p. 88 | Circular buffers must be a **power-of-two size and aligned**: G/F delay lines 32 floats, alignment lines 512/256/128/16 floats (§6) |
| Circular FIR in DSPLIB | `DSPF_sp_fircirc` reads a circular input buffer of 2^(csize+1) bytes, aligned to that size | S15 p. 4-43/4-44 | Optional demo of circular addressing (frame-based option) |
| **On-chip peripherals** | McASP (1), EDMA3 (64 channels), 2 I2C, 64-bit timers, GPIO, UART | S8 p. 1 | Audio I/O, codec control, buttons/LEDs, timing |
| Cycle counter | **TSCL/TSCH**: free-running 64-bit CPU-clock counter. Disabled after reset; **any write to TSCL starts it**. Read TSCL first (this latches TSCH) | S9 §2.9.14, p. 55–56 | Cycle measurement (06 §3.5). **Closes the earlier "TSCL unverified" gap** |

---

## 3. DSPLIB functions (S15 = C67x DSPLIB, SPRU657C)

Common rule for all functions below: little-endian; arrays of floats; **double-word (8-byte) alignment** where stated (use `#pragma DATA_ALIGN(x, 8)`).

| Function (S15 page) | What it does | Constraints | Cycles |
|---|---|---|---|
| `DSPF_sp_fir_gen(x, h, r, nh, nr)` (p. 4-40/4-41) | Real FIR, block form | x and h double-word aligned. **nh ≥ 4, nr ≥ 4.** **Coefficients in reverse order.** x holds nh−1 history samples before the block. Not interruptible (library Rev ≤ 2.0 bug), so **disable interrupts around the call** | (4·⌊(nh−1)/2⌋ + 14)·⌈nr/4⌉ + 8 |
| `DSPF_sp_fir_r2` (p. 4-42/4-43) | Real FIR, faster | **nh even ≥ 8, nr even ≥ 2.** Arrays padded with 4 words. Reverse-order coefficients. Disable interrupts around the call | nh·nr/2 + 34 (nr multiple of 4) |
| `DSPF_sp_fircirc` (p. 4-43…4-45) | FIR on a circular buffer | Buffer of 2^(csize+1) bytes aligned to that size. **nh even ≥ 4, nr multiple of 4** | (2·nh + 10)·nr/4 + 18 |
| `DSPF_sp_biquad(x, b, a, delay, r, nx)` (p. 4-46/4-47) | One second-order IIR section | Coefficients double-word aligned. **nx a multiple of 3** | 4·nx + 76 |
| `DSPF_sp_iir` (p. 4-48) | General IIR | nr even; \|h1[1]\| < 1 | 6·nr + 59 |
| `DSPF_sp_dotprod(x, y, nx)` (p. 4-53/4-54) | Dot product | x, y double-word aligned; pad 4 bytes if nx is odd; nx > 0 | nx/2 + 25 |
| `DSPF_sp_cfftr2_dit(x, w, n)` (p. 4-13…4-16) | Radix-2 DIT complex FFT | 32 ≤ n ≤ 32K, power of 2. **Input normal order, output bit-reversed.** Twiddles in bit-reversed order (`gen_twiddle` / `tw_r2fft`). Double-word aligned | 2·n·log2 n + 42 |
| `DSPF_sp_icfftr2_dif(x, w, n)` (p. 4-34…4-38) | Radix-2 DIF **inverse** FFT | **Input bit-reversed, output normal order.** Bit-reversed twiddles. Pad x with 4 words; n > 8. **This closes the earlier "ordering unverified" gap:** cfftr2_dit output can feed icfftr2_dif directly, with no bit-reversal step. The C reference code multiplies by inv (1/n scaling; confirm on board) | 2·n·log2 n + 37 |
| `DSPF_sp_cfftr4_dif(x, w, n)` (p. 4-9…4-12) | Radix-4 DIF FFT | n a power of 4 (256 = 4⁴ OK). Input normal order, **output digit-reversed**. Twiddles from `tw_r4fft` | (14·n/4 + 23)·log4 n + 20 |
| `DSPF_sp_fftSPxSP(N, x, w, y, brev, n_min, offset, n_max)` (p. 4-17…4-25) | Mixed-radix forward FFT | 8 ≤ N ≤ 8192, power of 2. x and w double-word aligned; real parts in even words, imaginary in odd. Twiddles from `tw_fftSPxSP_C67` (`tw_gen` listing in S15). `brev` table from `brev_table.h`. **Output in normal order** in a separate buffer y. n_min = 4 when N is a power of 4 (our N = 256), else 2 | 3·⌈log4 N − 1⌉·N + 21·⌈log4 N − 1⌉ + 2N + 44 → **2923 at N = 256** |
| `DSPF_sp_ifftSPxSP(...)` (p. 4-26…4-33) | Mixed-radix inverse FFT | Same as the forward FFT, plus **x padded with 16 words**. Disable interrupts around the call (Rev ≤ 2.0 bug). Scaling not stated in what we read: **check against MATLAB `ifft`** | Same formula → 2923 at N = 256 |
| `DSPF_sp_bitrev_cplx(x, index, nx)` (p. 4-5…4-8) | Bit reversal | nx a power of 2 | 2.5·nx + 26 |

**Version caution.** S15 is the C67x library. The C674x executes the C67x+ instruction set (S8 p. 1), so these functions should run. **Update 5:** the package you added (`sprc121.zip`) is the **C67x DSPLIB v2.00** (installer `C67xDSPLIB_v200.exe`, 2005), **not** TI's separate C674x DSPLIB (SPRC265). It matches S15 for everything we use, but carries the Rev 2.0 bugs listed in §3.2. **Update 6: the C674x DSPLIB 3.4.0.0 is already installed on your PC (`C:\ti\dsplib_c674x_3_4_0_0`) and must be used instead — see §3.3.**

**Benchmark caution.** S16's measurements were taken on a **C6713 DSK**, which has a 4 KB L1 and 64 KB L2 (S16 p. 3–4). The "2× slower than formula" single-pass FFT result (S16 Table 7, p. 16: 28,444 vs 14,464 cycles, 1024-point) comes from that smaller cache. On the C6748 (32 KB L1D) the penalty should be smaller. We keep 2× as a safety margin (ASSUMPTION).

### 3.1 What these constraints change in our design

| Pack item | Problem found | Fix |
|---|---|---|
| `05` §9 Mode A estimate (16-sample frames) used `DSPF_sp_fir_gen` with nr = 2 at level 3 | Violates **nr ≥ 4** (S15 p. 4-41) | Mode A runs **per sample in plain C** (DEFAULT). The 32-sample-frame option is valid: every level gets ≥ 4 samples |
| `05` §9 / `06` HPF used `DSPF_sp_biquad` with nx = 16 (and nx = 1 per-sample) | Violates **nx multiple of 3** (S15 p. 4-46) | HPF in **plain C** (DF-II transposed). `DSPF_sp_biquad` is used only in the benchmark experiment with nx = 48 |
| Mode A per-sample design | DSPLIB block functions cannot be called with 1 sample | Plain-C filters with power-of-two circular buffers. DSPLIB FIR appears in the comparison benchmark (T11/T6) |
| `06` said "confirm icfftr2 order" | Resolved: bit-reversed input, normal output | DIT → DIF chain without bit reversal (comparison experiment) |
| `06` said "confirm TSCL" | Resolved (S9 §2.9.14) | Use TSCL |
| Mode B FFT buffers | ifftSPxSP needs a 16-word pad; alignment | Allocate (2·256 + 16) floats, aligned to 8 bytes |
| Interrupt safety | fir_gen, fir_r2 and ifftSPxSP must not be interrupted (fftSPxSP has only a 1-cycle interruptible window) [S15 p. 4-25, 4-33] | Call the FFTs in the background loop with interrupts disabled (≈ 6.4 µs at 456 MHz, 9.7 µs at 300 MHz). **With the AFIFO enabled (Update 4 default) this is safe**: the Read FIFO can absorb ~60 sample periods before overrun (S14 p. 12) |

### 3.2 Check of the DSPLIB package against S15 (Update 5)

Package: `papers/DSPLIB_sprc121/C67xDSPLIB_v200.exe`, unpacked in the session workspace with 7-Zip (files `c6700/dsplib/include/*.h`, `lib/dsp67x.lib`, `support/fft/*`, `docs/pdf/SPRU657B.pdf`). Header line numbers refer to `c6700/dsplib/include/`.

| Item | Package (v2.00, SPRU657B + headers) | S15 (SPRU657C, Jan 2010) | Effect on us |
|---|---|---|---|
| Function names | `DSPF_sp_fftSPxSP`, `DSPF_sp_ifftSPxSP`, `DSPF_sp_fir_gen`, `DSPF_sp_biquad`, `DSPF_sp_cfftr2_dit`, `DSPF_sp_icfftr2_dif`, `DSPF_sp_fircirc`, `DSPF_sp_bitrev_cplx` all present | Same | None |
| fft/ifftSPxSP arguments | `(int N, float *ptr_x, float *ptr_w, float *ptr_y, unsigned char *brev, int n_min, int offset, int n_max)` (`DSPF_sp_fftSPxSP.h` lines 13–21) | Same | None |
| fir_gen arguments | `(x, h, r, nh, nr)`, coefficients reversed (`DSPF_sp_fir_gen.h` lines 10–30) | Same (S15 p. 4-40) | None |
| biquad arguments | `(x, b, a, delay, r, nx)`, DF-II transposed (`DSPF_sp_biquad.h` lines 11–20) | Same (S15 p. 4-45) | None |
| Alignment | fft/ifft: x and w double-word aligned (`DSPF_sp_fftSPxSP.h` line 230; `DSPF_sp_ifftSPxSP.h` line 232); icfftr2_dif: x, w double-word, pad 4 words, n > 8 (lines 75–78) | Same | None |
| ifft pad | 16 words (`DSPF_sp_ifftSPxSP.h` line 242) | 16 words (S15 p. 4-33) | None |
| Cycle formulas | fftSPxSP/ifftSPxSP: 3·⌈log4N−1⌉·N + 21·⌈log4N−1⌉ + 2N + 44, **2923 at N = 256** (`DSPF_sp_fftSPxSP.h` lines 439–442; `DSPF_sp_ifftSPxSP.h` lines 443–446); icfftr2_dif 2n·log2n + 37 (line 199) | Same (S15 p. 4-25, 4-33, 4-38) | `cpu_check.py` unchanged |
| fir_gen / biquad cycles | Same text in SPRU657B (p. 4-41, 4-45) | (4·⌊(nh−1)/2⌋+14)·⌈nr/4⌉+8; 4·nx+76 | Unchanged (656 and 268 in T11) |
| **biquad constraint** | SPRU657B: "nx ≥ 4" | **nx a multiple of 3**, and the loop unrolling adds two poles, so **\|a1\| < 1 and \|(a2 − a1²)/a1\| < 1 are required** (S15 p. 4-46) | **Our 100 Hz HPF fails this** (a1 ≈ −1.98; `cpu_check.py` Update 5). DSPF_sp_biquad must **not** be used for the HPF. Plain C stays; the T11 benchmark uses it only for timing with test coefficients that satisfy the rule |
| **Interrupt bug** | v2.00 is "Rev 2.0" | Known issue as of Rev 2.0: **disable interrupts around `DSPF_sp_ifftSPxSP`, `DSPF_sp_fir_gen`, `DSPF_sp_fir_r2`, `DSPF_sp_dotprod`, `DSPF_sp_maxval`, `DSPF_sp_minval`**, otherwise stack or register corruption (S15 Appendix B.3, p. B-2; also p. 4-33, 4-41) | **Applies to your package.** Wrap the ifft (and any fir_gen benchmark) in `_disable_interrupts()` / `_restore_interrupts()`. With the Read FIFO on, ≤ 9.7 µs off is safe |
| **ifftSPxSP scaling** | Header text: output "scaled by a scaling factor of 1/N" (`DSPF_sp_ifftSPxSP.h` line 110). **But the header's reference C code has no 1/N.** We compiled that reference C with gcc: fft output matched a direct DFT (error ≤ 2.2e-6); ifft(fft(x)) returned **N·x** for N = 128 and 512 (radix-2 path). For N = 256 (radix-4 path) the reference C is also wrong (its last stage is copied from the forward FFT) | Text says 1/N (p. 4-27); its reference C divides by n (`y0[k] = yt0/n_max`, p. 4-32) | Unresolved for the v2.00 assembly. **Update 6: moot** — the project uses the C674x DSPLIB, whose ifft scales by 1/N (§3.3). The start-up self-check stays as a guard (0 cycles per frame) |
| Max N | Header: N ≤ 16384 | N ≤ 8192 | None (N = 256) |

**C674x DSPLIB (SPRC265).** Superseded in Update 6: it is installed and required (§3.3).

---

### 3.3 Library locations and CCS settings (Update 6)

**What is on the PC** (inspected read-only):

| Item | Path | Notes |
|---|---|---|
| CCS | `C:\ti\ccsv7` (CCS 7.2.0) | — |
| C6000 compiler | `C:\ti\ccsv7\tools\compiler\ti-cgt-c6000_8.1.3` | **The only C6000 compiler installed.** Its README (line 112): "v8.1 no longer supports the COFF object file format. Only ELF is supported." |
| C67x DSPLIB v2.00 (your installer) | `C:\CCStudio\c6700\dsplib\` → `lib\dsp67x.lib`, `include\DSPF_sp_*.h` (one header per function), `support\fft\brev_table.h`, `tw_fftSPxSP_C67.c`, `bin\tw_fftSPxSP_c67.exe`; manual `C:\CCStudio\docs\pdf\SPRU657B.pdf` | `dsp67x.lib` objects are **TI COFF** (header bytes 00 C2, checked). **They cannot be linked by CGT 8.1.3.** |
| **C674x DSPLIB 3.4.0.0** (already installed) | `C:\ti\dsplib_c674x_3_4_0_0\packages\ti\dsplib\` → `dsplib.h`, `lib\dsplib.ae674` (ELF, built `-mv6740 --abi=eabi`, `dsplib.ae674.mk` line 18), `lib\dsplib.a674` (COFF), `lib\dsplib.lib` (index library), `src\DSPF_sp_*\c674\` (headers, natural-C `_cn.c`, test drivers `_d.c` with `tw_gen()` and `brev[]`) | ELF — **matches CGT 8.1.3 and the book's ELF linker file** (`link6748e.cmd` line 4: "EABI ELF", `rts6740_elf.lib`) |

**Decision needed (PROPOSED CHANGE – confirm, forced by the tools):** use the **C674x DSPLIB 3.4.0.0** in the project, not the C67x v2.00 you installed. Same function names and arguments for fftSPxSP/ifftSPxSP/fir_gen/biquad (C674x headers), so no code change except the include line.

**CCS project settings (C674x DSPLIB, ELF):**

- Build → C6000 Compiler → Include Options → add **`C:\ti\dsplib_c674x_3_4_0_0\packages`**. In code: `#include <ti/dsplib/dsplib.h>` (it includes each function header, e.g. `dsplib.h` lines 44, 52, 55, 58).
- Build → C6000 Linker → File Search Path → library search path **`C:\ti\dsplib_c674x_3_4_0_0\packages\ti\dsplib\lib`**; include library **`dsplib.ae674`**.
- Processor options: `-mv6740`, output format ELF (the only option in CGT 8.1.3).
- Twiddles and `brev[]`: copy `tw_gen()` and `brev[64]` from `src\DSPF_sp_fftSPxSP\c674\DSPF_sp_fftSPxSP_d.c` (the same table and generator serve the inverse, `DSPF_sp_ifftSPxSP_d.c`).

**For completeness, C67x v2.00 settings** (only usable with a COFF-capable compiler such as CGT 7.4.x, which is not installed): include `C:\CCStudio\c6700\dsplib\include`, `#include "DSPF_sp_fftSPxSP.h"` etc., library `C:\CCStudio\c6700\dsplib\lib\dsp67x.lib`.

**C674x DSPLIB 3.4.0.0 vs the C67x figures used so far:**

| Function | C674x header (Assumptions / Interruptibility) | C674x cycles (`docs\DSPLIB_C674x_TestReport.html`) | Change for us |
|---|---|---|---|
| `DSPF_sp_fftSPxSP` | N power of 2, 8 ≤ N ≤ 131072; x, w, y double-word aligned, no overlap; "interrupt-tolerant but not interruptible" | **1965** (N = 256) vs 2923 (S15) | Faster; Mode B frame 12,746 → 10,850 cycles (`cpu_check.py` Update 6) |
| `DSPF_sp_ifftSPxSP` | Same; **no Rev 2.0 interrupt bug listed**; natural C scales by **1/n_max** (`DSPF_sp_ifftSPxSP_cn.c` line 167) | **1985** (N = 256) | **Scaling resolved:** we compiled TI's `_cn.c` reference with gcc: ifft(fft(x)) = x within 1.5e-7 for N = 64, 128, 256, 512. TI's test driver checks the optimized routine against `_cn` (`_d.c` lines 175–180). Keep the start-up self-check as a guard |
| `DSPF_sp_fir_gen` | **nh and nr multiples of 4, ≥ 4**; x, h, r double-word aligned; interruptible | 10/16·Nr·Nh + 55 | Benchmark G padded 21 → 24 taps (zeros): 775 cycles at nr = 48 |
| `DSPF_sp_biquad` | nx ≥ 2; interruptible | 8·Nx + 72 | No pole rule stated in the C674x header; still plain C for the HPF (DESIGN CHOICE, per-sample) |


## 4. CPU estimate re-check with the TI formulas

Source: `calc/cpu_check.py`, output in `calc/cpu_check_output.txt`. Assumptions are listed in the script. **Update 4:** I/O is now EDMA with 4-sample blocks (AFIFO on). The per-sample-interrupt figures are kept for comparison.

| Case | Load @ 456 MHz | Load @ 300 MHz |
|---|---|---|
| **Mode A, EDMA + Read FIFO, 4-sample blocks (DEFAULT; Write FIFO off does not change CPU)**. 83 ops/sample at 1–5 cycles/op, plus a block ISR of 300–900 cycles shared by 4 samples | **1.7 – 6.7 %** | 2.5 – 10.2 % |
| **Mode B, EDMA + Read FIFO** (12,746 cycles per 128-sample frame + block ISR) | **1.8 – 3.4 %** | 2.8 – 5.2 % |
| **Mode B with the C674x DSPLIB (Update 6 default library)**: 10,850 cycles per frame + block ISR | **1.7 – 3.3 %** | 2.6 – 5.0 % |
| Mode A, per-sample ISR (Update 3 default; now with S19 framing, one event per sample, the old 2-event figure was pessimistic) | 3.0 – 10.7 % | 4.5 – 16.2 % |
| Mode A, 32-sample frames with `DSPF_sp_fir_gen` | 1.27 % | 1.94 % |

**Budget:** 9500 cycles per sample at 456 MHz. The worst case is about 10 % at 300 MHz, so the design fits easily (both GELs set 300 MHz; confirm on the board, §1.7).

## 5. Latency facts

- Codec 17/fS + 21/fS = 0.79 ms (S13).
- Filter bank 375 samples = 7.81 ms (Mode A); Mode B 2L + (M−1)/2 = 320 samples.
- **Read FIFO only + EDMA (DEFAULT, Update 5):** +10 samples → **Mode A 8.81 ms, Mode B 7.67 ms.**
- Both FIFOs (Update 4, rejected): +74 samples → 10.15 / 9.00 ms. The Write FIFO adds 64 words = 64 sample periods = 1.33 ms because one word holds L+R (§1.4).
- All values come from `calc/latency_check.py`.

## 6. Memory needed (our calculation, `calc/review_check.py` and `cpu_check.py`)

| Item | Size | Placement |
|---|---|---|
| Mode A circular buffers (power of 2): alignment 512 + 256 + 128 + 16 floats, plus 4 levels × (32 + 32) floats for G/F lines | 1168 floats = 4.7 KB | L2 RAM |
| Coefficients (G 21, F 31, HPF 10, H[k] 256 complex) | ≈ 2.3 KB | L2 |
| Mode B: x (512 + 16 pad), y (512), overlap (128), twiddles (2·256), brev (64 B) | ≈ 6.8 KB | L2 |
| Code | NOT FOUND until built (estimate < 64 KB, ASSUMPTION) | L2 |
| 10 s capture buffer | 1.92 MB | DDR2 |

The total internal data is about 15 KB, compared with 256 KB of L2 [S8]. **It fits**, even if half of L2 is set as cache.

---

## 7. Status of the former "NOT FOUND" items (Updates 4 and 5)

| # | Item | Status | Answer and source |
|---|---|---|---|
| 1 | Codec MCLK frequency | **Found** | 24.576 MHz oscillator Y5 → net AIC_MCLK → codec MCLK and DSP AHCLKX (S12 sheet 10, sheet 7) |
| 1b | Who drives BCLK/WCLK | **Found (board allows both; firmware decides)** | Nets AIC_BCLK ↔ ACLKX, AIC_WCLK ↔ AFSX (S12 sheets 7, 10). S19 sets the codec as master (reg 8 = 0xF0). We follow S19 |
| 2 | McASP serializer pins | **Found** | AXR13 → codec DIN, codec DOUT → AXR14 (S12 sheet 10) |
| 2b | I2C instance | **Found** | I2C0 (nets SPI1_SCSn_6/I2C0_SDA, SPI1_SCSn_7/I2C0_SCL; S12 sheets 7, 10). Address 0x18 (MFP0/MFP1 pulled low) |
| 3 | Jack wiring | **Found** | LINE IN → LINE1L+/LINE1R+ single-ended (regs 19/22). MIC IN (J11) → MIC3L/MIC3R (regs 17/18). LINE OUT ← LEFT_LO+/RIGHT_LO+ via 10 µF (regs 82/92, 86/93). HP drivers not connected (S12 sheet 10) |
| 4a | Pin-mux for McASP0 and I2C0 | **Found (Update 5)** | `Config_LCDK6748()` in `LCDK6748_Support_DSP.c`: PINMUX4 bits 8–15 → 0x22 (I2C0 SDA/SCL); PINMUX0 bits 0–27 → 0x1111111 (ACLKR, ACLKX, AFSR, AFSX, AHCLKR, AHCLKX, AMUTE); PINMUX1 bits 4–11 → 0x11 (AXR14, AXR13); PSC1 module 7 (McASP0) enabled. Called first in `DSP_Init()` / `DSP_Init_EDMA()` |
| 4b | Pin-mux for buttons S2/S3 | **Not needed** | Pin-mux does not affect inputs (S8 §3.6, p. 26) |
| 4c | Pin-mux for LEDs D4–D6 | **Found (Update 6)** | PINMUX13[11:8] = 8h (D4, GP6[13]), PINMUX13[15:12] = 8h (D5, GP6[12]), PINMUX5[15:12] = 8h (D6, GP2[12]) — TRM p. 247, 230 (§1.5) |
| 5 | CPU clock after the GEL script | **Found (Update 6)** | 300 MHz requested by both GELs; Update 5 "PLL0 bug" retracted. Read-out procedure in §1.7 (TRM §7.3) |
| 6 | S19 header constants (`REG_PLL_A_*`, `REG_CODEC_SAMPLE_RATE_*`) | **Found (Update 5)** | `AIC3106.h` lines 128–129: 48 kHz → reg 3 = **0x20**, reg 2 = **0x00**. Equal to our calculated values |
| 7 | KICK unlock before PINMUX writes | **Closed (Update 6)** | "The Kick registers are disabled in silicon revision 2 and later. The SYSCFG registers are always unlocked" (TRM §10.2.2, p. 204). No unlock needed unless the board has an older silicon revision |
| 8 | EDMA PaRAM for 4-word Read-FIFO events; DMA-port requirement | **Found (Update 6)** | §1.4 (TRM p. 555, 556, 612, 1090, 1103, 1107, 1160) |

---

## 8. What "S19" is, and whether it matches the schematic

| Field | Value |
|---|---|
| File | `LCDK6748_Support_DSP.c`: a third-party (not TI) board-support C file for the **C6748 LCDK** |
| What it is | A drop-in **replacement for `LCDK_Support_DSP.c`** from the code package of the textbook *Real-Time Digital Signal Processing from MATLAB to C with the TMS320C6x DSPs*, 3rd ed. (CRC Press, 2017, ISBN 978-1498781015). The replacement exists because the original file assumed the OMAP-L138 board (which has an ARM core); this is stated on the book's software page |
| Authors | Thad B. Welch, Cameron H. G. Wright, Michael G. Morrow (book authors; file header comment reads "Welch, Wright, & Morrow, Real-time Digital Signal Processing, 2018") |
| Version | **No version number in the file.** Header year 2018. The main code package is dated **2017-02-05** (`code_2017_02_05.zip`) |
| Direct links | File: https://rt-dsp.com/3rd_ed/LCDK6748_Support_DSP.c · Code package (projects + headers): https://rt-dsp.com/3rd_ed/zips/code_2017_02_05.zip · Software page: https://rt-dsp.com/3rd_ed/3e_software.html |
| Functions | `DSP_Init()` (per-sample McASP interrupt), `DSP_Init_EDMA()` (EDMA, EDMA3_CC0_INT1), `Init_AIC3106()`, `SetSampleRate_AIC3106()` (8–96 kHz), I2C helpers |

**Match against the schematic (S12):**

| S19 setting | Schematic | Match? |
|---|---|---|
| I2C instance `I2C0_Base`, address 0x18 | Codec SDA/SCL on I2C0 nets; MFP0/MFP1 low → 0x18 | **Yes** |
| SRCTL13 = transmit, SRCTL14 = receive | AXR13 → DIN, DOUT → AXR14 | **Yes** |
| Codec master (reg 8 = 0xF0), McASP clocks external | BCLK/WCLK wired to ACLKX/AFSX (bidirectional) | **Yes** (consistent) |
| PLL bypassed (reg 101 = 0x01), CLKDIV_IN = MCLK (reg 102 = 0x02) | 24.576 MHz oscillator on MCLK; with Q = 4 gives exactly 48 kHz | **Yes** (the 48 kHz `pll_a` constant itself not seen) |
| AHCLKX external (AHCLKXCTL = 0) | AIC_MCLK also reaches AHCLKX | **Yes** |
| Line input via LINE1L/LINE1R = 0x04 (single-ended) | J10 upper → LINE1L+/LINE1R+, minus pins unconnected | **Yes** |
| Mic input via MIC3L/MIC3R + MICBIAS | J11 → MIC3L/MIC3R, MIC_BIAS net | **Yes** |
| Output to LEFT_LOP/RIGHT_LOP (regs 82/86/92/93) **and** HPLOUT/HPROUT (regs 47/51/64/65) | Only LEFT_LO+/RIGHT_LO+ reach the jack; HP pins unconnected | **Yes** for the line path; the HP writes are harmless and unused |

**Verdict.** S19 agrees with the schematic on every connection checked. Use it as the board bring-up base.

---

## 9. S19 code package check (Update 5)

Package: `papers/code_2017_02_05.zip` → `papers/S19_code_2017_02_05/code/` (611 entries). Board files: `common_code/LCDK/` (`AIC3106.h`, `DSP_Config.h`, `LCDK_Support_DSP.c/.h`, `OMAPL138_defines.h`, `link6748e.cmd`, `main.c`, `vectors*.asm`), GEL and target file in `target_configuration/LCDK/`, EDMA example in `chapter_06/ccs/Frame_EDMA_6748/`.

**Important:** the package contains the **original** `LCDK_Support_DSP.c` (header year 2017). It has **no `Config_LCDK6748()`**, so it does no pin-mux or McASP power-up. The book's page says to replace it with `LCDK6748_Support_DSP.c` (header year 2018), which adds `Config_LCDK6748()` and calls it first in `DSP_Init()` and `DSP_Init_EDMA()`. The replacement file is **not inside the zip**. **Update 6:** you saved it as `papers/LCDK6748_Support_DSP.c`; comparison in §10. Apart from `Config_LCDK6748()` the two files define the same functions.

| # | Item | Found in (file : function : line) | Value | Matches `hardware_notes` and S12? |
|---|---|---|---|---|
| 1 | 48 kHz constants | `common_code/LCDK/AIC3106.h` lines 123–129 | `REG_PLL_A_48KHZ 0x20` (PLL off, Q = 4), `REG_CODEC_SAMPLE_RATE_48KHZ 0x00`; comment "based on 24.576MHz MCLK, not using PLL" | **Yes** – §1.2/§1.3; MCLK 24.576 MHz = S12 sheet 10 (Y5) |
| 2 | Rate selection | `common_code/LCDK/DSP_Config.h` line 19; `LCDK_Support_DSP.c` : `SetSampleRate_AIC3106()` : lines 572–627 | `SampleRateSetting AIC3106Fs48kHz`; writes reg 2 then reg 3 (lines 625, 627) | **Yes** |
| 3 | Input selection | `DSP_Config.h` line 28 | `CodecType LCDK_LineInput` (mic options commented out) | **Yes** – LINE IN = LINE1 (S12 sheet 10) |
| 4 | Codec register writes | `LCDK_Support_DSP.c` : `Init_AIC3106()` : lines 432–524 | reg 7 = 0x0A (432), 8 = 0xF0 codec master (434), 9 = 0x40 DSP 16-bit (436), 10 = 0x00 (438), line branch 15/16 = 0x00, 19/22 = 0x04, 17/18 = 0xFF, 25 = 0x00 (442–454), 26/29 = 0x00 AGC off (490–492), 37 = 0xE0 (494), 38 = 0x10 (496), 43/44 = 0x00 (498–500), HP routing 47/51/58/64/65/72 (502–512), **82 = 0x80, 86 = 0x09, 92 = 0x80, 93 = 0x09** (514–520), **101 = 0x01, 102 = 0x02** (522–524) | **Yes, all** – §1.3 table. Reg 38 = 0x10 (HPRCOM single-ended) was not in §1.3; harmless (HP pins unwired) |
| 5 | I2C | `LCDK_Support_DSP.c` : `Init_I2C()` : lines 282–302; address line 529 | `I2C0_Base` (0x01C2 2000, `OMAPL138_defines.h` line 228), psc = 7, clkl = clkh = 37 ("100kHz", comment assumes 300 MHz/4 input); `AIC3106_I2C_ADDR 0x18` | **Yes** – I2C0 nets, MFP0/1 low → 0x18 (S12 sheets 7, 10) |
| 6 | McASP set-up | `LCDK_Support_DSP.c` : `Init_McASP0()` : lines 632–720 | RFMT = XFMT = 0x000080F8 (32-bit slot, 0 delay, CFG bus; 658, 668); AFSRCTL = AFSXCTL = 0 (burst, external FS); ACLK/AHCLK CTL = 0 (external); RTDM = XTDM = 1 (one slot); RINTCTL = 0x01, XINTCTL = 0x20; SRCTL13 = 0x0D (TX), SRCTL14 = 0x0E (RX); PDIR = 0x2000 (only AXR13 output); start order: clocks → clear status → serializers → state machines → `xbuf[13] = 0` → frame syncs. **No FIFOCTL writes** | **Yes** – §1.4 and S12 (AXR13 → DIN, DOUT → AXR14, BCLK/WCLK from codec). One slot of 32 bits per frame confirms **one word = one sample period (L+R)** |
| 7 | EDMA example | `chapter_06/ccs/Frame_EDMA_6748/ISRs.c` lines 16–45, `EDMA_Init()` lines 47–157; `main.c` lines 19–23 | Events 0 (RX) / 1 (TX), 4-byte transfers, "two Int16 read from McASP each time" (line 17), 3 linked buffers, `EDMA_Init()` then `DSP_Init_EDMA()` | **Yes** – basis for our codec_io.c; we change block size to 4 and add the Read FIFO |
| 8 | Interrupts | `LCDK_Support_DSP.c` : `Init_Interrupts()` lines 187–205 (McASP0 event 61 → INT12, ISTP = 0x1180 0000); `EnableInterrupts_EDMA()` lines 242–258 (EDMA3_CC0_INT1 on INT8, IER 0x0102) | — | **Yes** – S8 Table 6-6 (event 61) |
| 9 | Pin-mux + PSC | `LCDK6748_Support_DSP.c` (replacement file) : `Config_LCDK6748()` | See §7 item 4a | **Yes** – the pins it selects (ACLKX, AFSX, AHCLKX, AXR13, AXR14, I2C0) are exactly the S12 nets |
| 10 | PLL / clocks / DDR / PSC | `target_configuration/LCDK/OMAP-L138_LCDK.gel` : `OnTargetConnect()` lines 237–249 | `PSC_All_On()` (lines 508–558, includes LPSC_MCASP0 and EDMA), `Core_300MHz_mDDR_150MHz()`, `Wake_DSP()` | **Yes** – PLL0 enabled at line 658, PLL1 at line 732 (§1.7; Update 5 claim retracted) |
| 11 | LEDs | `LCDK_Support_DSP.c` : `InitLEDs()` / `WriteLEDs()` lines 79–133 | GP6[13] = LED1, GP6[12] = LED2, GP2[12] = LED3, GP0[9] = LED4 | Same GPIOs as S11 Table 8 (D4–D7). No pin-mux (§1.5) |

**Processor SDK not needed.** Everything we planned to take from it is in the S19 package: the LCDK GEL file (item 10), register addresses (`OMAPL138_defines.h`: PINMUX0–19, GPIO, I2C, McASP, EDMA3 PaRAM; lines 73–92, 103–119, 228, 347, 364–381), a linker file and interrupt vector tables. Nothing in our plan requires the SDK.

---

## 10. `LCDK6748_Support_DSP.c` vs the zip's `LCDK_Support_DSP.c` (Update 6)

Method: line-by-line `diff` (carriage returns removed). Line numbers are in `papers/LCDK6748_Support_DSP.c` (27,656 bytes).

| Area | Difference | Check against TRM / schematic / `hardware_notes` |
|---|---|---|
| Header | Year 2017 → 2018; comment that the 6748 LCDK has no ARM, so `Config_LCDK6748()` sets PINMUX and PSC (lines 1–13) | — |
| New defines (lines 46–53) | `SOC_PSC_1_REGS 0x01E27000`, `PSC_PTCMD 0x120`, `PSC_PTSTAT 0x128`, MDCTL/MDSTAT masks | PSC1 base 0x01E2 7000 (same as GEL `PSC1_BASE`); MDCTL at +A00h, MDSTAT at +800h, as in the GEL (lines 77–85) |
| **New `Config_LCDK6748()` (lines 67–114)** | PINMUX4 bits 15–8 → 0x22 (line 74); PINMUX0 bits 27–0 → 0x1111111 (line 86); PINMUX1 bits 11–4 → 0x11 (line 92); PSC1 MDCTL[7] = 3 (enable), PTCMD = 1, wait GOSTAT, wait MDSTAT[7] = 3; stall if timeout | PINMUX4[15:12] 2h = I2C0_SDA, [11:8] 2h = I2C0_SCL (TRM p. 229). PINMUX0 1h = ACLKR, ACLKX, AFSR, AFSX, AHCLKR, AHCLKX, AMUTE (TRM p. 220–221). PINMUX1[11:8] 1h = AXR13, [7:4] 1h = AXR14 (p. 223). PSC1 LPSC 7 = McASP0 (+ FIFO), default SwRstDisable (TRM Table 8-2, p. 166). **All correct** and they match the S12 nets |
| `DSP_Init()` (line 127) / `DSP_Init_EDMA()` (line 151) | Both now call `Config_LCDK6748()` first (lines 129, 153); the rest is whitespace only | — |
| Codec init, I2C, McASP, EDMA/interrupt helpers, UART | **Identical** (no diff lines) | Same values as §1.3, §9 |
| Not done by either file | GPIO and EDMA power-up (PSC1 LPSC 3; PSC0 LPSC 0–2), LED pin-mux, AFIFO | GEL `PSC_All_On()` powers GPIO/EDMA; LED pin-mux and Read FIFO are **our additions** (§1.4, §1.5) |

**Which file the project uses:** `LCDK6748_Support_DSP.c`.

**How to swap it in:**

1. Copy `common_code/LCDK/*` from the S19 package into the project (`AIC3106.h`, `DSP_Config.h`, `LCDK_Support_DSP.h`, `OMAPL138_defines.h`, `link6748e.cmd`, `vectors_EDMA.asm`; leave out `LCDK_Support_DSP.c` and `vectors.asm`).
2. Add `papers/LCDK6748_Support_DSP.c` instead. Keep `#include "DSP_Config.h"` (it pulls in `LCDK_Support_DSP.h`, unchanged).
3. Copy `chapter_06/ccs/Frame_EDMA_6748/ISRs.c` and `main.c` as the starting `codec_io.c` / `main.c`.
4. Make sure only one of the two support files is in the build; both define the same functions.

---

## 11. I/O modes, including "no external input" fallbacks (Update 6)

Live audio stays the **default**. Two fallbacks let the team test and demonstrate without a signal source (and, for mode C, without the codec at all). Selected with one compile-time switch (DESIGN CHOICE): `#define IO_MODE IO_LIVE | IO_STORED_LINEOUT | IO_INTERNAL`.

| Mode | Input | Output | What still runs | Proof it works in real time | Limits |
|---|---|---|---|---|---|
| **A. `IO_LIVE` (default)** | LINE IN → codec ADC → McASP Read FIFO → EDMA | EDMA → McASP → codec DAC → LINE OUT → powered speakers / HP amp | Everything (§1.4) | Clean audio; no RSTAT/XSTAT errors; T5 latency; TSCL cycles | Needs a source (PC/phone) and speakers |
| **B. `IO_STORED_LINEOUT`** | Test signal stored on the board: MATLAB-exported tones/speech, 16-bit, placed in DDR2 (10 s mono 16-bit = 0.96 MB; 10 s as L+R 32-bit words = 1.92 MB; inside the 128 MB at 0xC000 0000, S8/S11) or loaded with CCS *Load Memory* | Same as A: codec DAC → LINE OUT | Codec, McASP, EDMA TX at 48 kHz paced by the codec clock; the RX EDMA still runs but its data are replaced by the stored samples in the block ISR | Same audible result; no underruns (XSTAT); TSCL cycles per block < budget | No microphone/line path, so no acoustic latency test (T5 can still use a marker sample in the stored signal and a scope on LINE OUT) |
| **C. `IO_INTERNAL`** | Stored test vector in DDR2 (same files as B) | Output array in DDR2; viewed with the CCS graph tool (time and FFT-magnitude views) and saved with *Save Memory* for comparison with MATLAB | Only the DSP code (HPF, Mode A/B); **no McASP, no codec, no EDMA**; a loop feeds 4-sample blocks | **Cycle-count proof:** worst-case TSCL cycles per 4-sample block must stay below 4/48 000 s × f_CPU (25 000 cycles at 300 MHz; 6250 per sample). Output must match MATLAB (T4.5 gate < 1e-4) | Not real time by construction; demonstrates correctness + timing margin only |

Notes:

- Modes B and C use the same processing code as A, so cycle counts are comparable.
- Stored signals come from Stage 1.9 (`06`) exports; the gain tests T2/T3 can run in mode C before the board audio works.
- The CCS menu names are from CCS 7 (not cited from a TI document).

