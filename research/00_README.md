# Research Pack – Real-Time Digital Hearing Aid using Multirate Filter Bank and FFT-Based Overlap-Add Processing on TMS320C6748

**Team:**

- Aneesh Venkatesha Rao (24ECB0A03)
- Akula Sahasra (24ECB0A02)
- Adhvay Shrujal (24ECB0A01)

NIT Warangal, ECE, DSP Lab (Batch 1). Pack prepared 3 Oct 2026; **updated 4 Oct 2026 (Update 6: TRM read, replacement board file checked, DSPLIB paths fixed, fallback I/O modes added)**. See `CHANGES.md` and **`research/REVIEW.md`** (verdict, issue list, one-page spec, open decisions).

> **For Claude Code:** start from `research/REVIEW.md` §c (final spec), then `05_system_design.md`, `06_implementation_plan.md` and `research/hardware_notes.md`.

> **Copyright note.** `papers/` holds licence-restricted PDFs: IEEE Xplore copies of S1 and S3, the AudiologyOnline article (S27) and the SAGE article (S26). They are for **personal study only**, and `papers/` is excluded from git by `.gitignore`. The TI documents (S8–S16) are also kept there. Do not share the folder or upload it publicly.

## Files

| File | Contents |
|---|---|
| `00_README.md` | This index, project summary, quality-check results, open gaps |
| `01_title_and_abstract.md` | Final title, 150-word abstract, 5-point syllabus coverage (for faculty approval) |
| `02_sources.md` | 30 verified sources (A1–A3), works cited only via another source (A4), unverified list (B), Step 1 notes on the starting sources (C) |
| `research/audiogram.md` | Bisgaard N2/N3/S2 audiograms, band mapping, half-gain and ×0.4 gain tables, Mode A/B accuracy per case |
| `research/literature_extracts.md` | Full-text extracts: Yang/Liu/Jou (class-2 limits, eqs. 15–17), Sokolova 2021/2022 and the patent (complementary design, resamplers, alignment, WDRC eqs. 1–7); WDRC scope decision |
| `research/hardware_notes.md` | LCDK/AIC3106/McASP/C6748/DSPLIB facts with page, schematic-sheet or file:line citations; codec register values; FIFO/latency table; S19 identity (§8); DSPLIB package checks (§3.2, §3.3 incl. CCS settings); S19 package (§9); board-file diff (§10); I/O modes (§11) |
| `research/REVIEW.md` | Full review: verdict, 37-issue table, final one-page spec, open decisions, gaps |
| `CHANGES.md` | Log of every change (Updates 2–6) |
| `.gitignore` | Keeps `papers/` out of git |
| `03_syllabus_mapping.md` | Every syllabus topic → block / design step / test, with depth (core / comparison / supporting / explained) |
| `04_theory_notes.md` | 17 theory notes: idea, equations, worked example, use in project |
| `05_system_design.md` | Block diagrams (Mermaid), fs, bands, filters, gain table, latency, CPU/MAC calculations |
| `06_implementation_plan.md` | MATLAB → fixed/float check → CCS C code → board; DSPLIB functions, memory map, cycle measurement |
| `07_testing_plan.md` | 16 tests (tones, sweep, noise, speech, latency, CPU), graphs for the report |
| `08_risks_and_timeline.md` | 16 risks with fallbacks; 12-week one-person timeline |
| `calc/design_check.py` + `design_check_output.txt` | Python script that produced every calculated number (filter design, full filter-bank simulation, latency, cycles) |
| `calc/audiograms.py`, `calc/gain_check.py` + `gain_check_output.txt` | Bisgaard data, gain tables, Mode A/B accuracy, S3 eq. (15)/(16) cross-check |
| `calc/cpu_check.py` + output | CPU load from TI cycle formulas, with DSPLIB constraint assertions |
| `calc/review_check.py` + output | Independent re-check of 55 key numbers quoted in the docs (55/55 pass) |
| `calc/latency_check.py` + output | End-to-end latency for FIFO off / Read FIFO only (default) / both FIFOs |
| `calc/fig_*.png` | Prototype filter responses and zero plot; Mode A band responses and composite gain |
| `papers/` | 13 saved PDFs (6 papers + 7 TI documents), the LCDK schematic package (S12), the S19 code package (`code_2017_02_05.zip` + unzipped), the C67x DSPLIB v2.00 (`sprc121.zip` + unzipped; not used, see §3.3), the TRM (`spruh79c.pdf`), `LCDK6748_Support_DSP.c` and `DOWNLOAD_LIST.md` (saved, missing, blockers with links) |

## Project summary (10 lines)

1. **Goal:** a real-time hearing aid on the TI C6748 LCDK that boosts each frequency band by a different amount to match a hearing-loss audiogram.
2. **Audio path:** AIC3106 codec (I2C0, 0x18, MCLK 24.576 MHz, codec master, DSP mode) at 48 kHz → McASP0 (Read FIFO on, Write FIFO off) → EDMA, 4-sample blocks → C6748 (float) → back out → LINE OUT → powered speakers or headphone amp. Button S2 switches mode; S3 switches audiogram.
3. **Input clean-up:** a 4th-order Butterworth 100 Hz high-pass (bilinear transform, 2 cascaded biquads) removes DC and rumble.
4. **Mode A:** 5-band multirate filter bank. Each of 4 levels splits with a 21-tap Kaiser-window lowpass, decimates by 2, then recombines with a 31-tap half-band interpolator. Crossovers are 750 Hz, 1.5, 3 and 6 kHz.
5. **Mode B:** the same gain curve as a 129-tap frequency-sampling FIR, run by FFT-256 overlap-add (block of 128).
6. **Gains:** half-gain rule (Lybarger, cited via Venema 2001) on the Bisgaard N3 moderate standard audiogram, capped at 30 dB: 17.5–30 dB per band. Per-band WDRC with the patent's attack/release equations is OPTIONAL – confirm.
7. **Latency:** 8.81 ms (Mode A) and 7.67 ms (Mode B), both under the 10 ms target.
8. **CPU load:** 2–7 % at 456 MHz (≤ 10.2 % at 300 MHz), from TI cycle formulas with EDMA blocks of 4 ; Mode B uses the C674x DSPLIB (1.7–3.3 %). The GEL sets 300 MHz (confirm on the board). Mode A needs 61 ops/sample, 5.1× fewer than a single-rate design.
9. **Syllabus:** 21 topics are core, 10 are comparison-only studies (e.g., radix-4 timing, lattice forms), 2 are supporting, 4 are explained (with measurement where possible), and none are left out.
10. **Workflow:** verify in MATLAB → plain C plus DSPLIB FFTs in CCS → measure response, gains, latency and cycles on the board.

## Decisions to confirm with the team (marked "DEFAULT – confirm with team")

- Sampling rate 48 kHz.
- 5 bands, 4 levels (6 bands is possible but latency rises to about 17 ms).
- Mode B sizes: M = 129, L = 128, N = 256.
- A 12-week semester.
- Default audiogram is Bisgaard N3 with the half-gain rule; N2 and S2 are test cases (`research/audiogram.md`).
- **PROPOSED CHANGE – confirm (scope only):** Mode A is for flat or moderately sloping losses; steep losses (Bisgaard S2) use Mode B.
- **OPTIONAL – confirm:** per-band WDRC after the core works.
- **DECIDED (Update 5):** Read FIFO on (4 words), Write FIFO off, EDMA with 4-sample blocks for both modes. Fallback: per-sample interrupt, FIFO off.
- **DECIDED (Update 5):** Processor SDK skipped; emulator and powered speakers/HP amp from the lab; CCS installed.
- **DECIDED (Update 6):** LED plan D4 = mode, D5 = clip + preset blink, D6 = CPU-busy scope pin, D7 = AMUTE.
- **PROPOSED CHANGE – confirm (Update 6, forced by the tools):** use the installed **C674x DSPLIB 3.4.0.0**, not the C67x v2.00 (COFF, cannot be linked by the ELF-only CGT 8.1.3).
- **DESIGN CHOICE (Update 6):** I/O modes `IO_LIVE` (default), `IO_STORED_LINEOUT`, `IO_INTERNAL` (`06` §3.6).
- Recommendations for every open item are in `research/REVIEW.md` §d.

## Quality check – Update 6 (4 Oct 2026)

| Check | Result |
|---|---|
| Replacement board file checked | **Yes.** Only `Config_LCDK6748()` + two calls differ; pin-mux/PSC values match TRM p. 166, 220–229 (`hardware_notes` §10) |
| PLL claim re-verified | **Withdrawn.** Not a bug (line 732 = DDR PLL1; PLL0 enabled at line 658); TI's own GEL agrees |
| TRM gaps filled with section + page | **Yes.** LED pin-mux, PLL read-out, EDMA PaRAM, DMA port, RFIFOCTL, KICK |
| Library location and CCS settings | **Yes.** C67x v2.00 at `C:\CCStudio\c6700\dsplib` (COFF, unusable with CGT 8.1.3); C674x DSPLIB 3.4.0.0 at `C:\ti\dsplib_c674x_3_4_0_0` (use this) |
| Fallback I/O modes | **Added** (`hardware_notes` §11, `06` §3.6, T16, R16) |
| Calculations re-run | **Yes.** All five scripts; `review_check.py` **55/55 pass** |
| Team block / papers/ in .gitignore | Unchanged / **Yes** |

## Quality check – Update 5 (4 Oct 2026)

| Check | Result |
|---|---|
| S19 package unzipped and checked line by line | **Yes.** `hardware_notes.md` §9: 48 kHz constants, codec writes, I2C, McASP, EDMA, interrupts, pin-mux, GEL — all cited file : function : line; all match §1 and S12 |
| DSPLIB package checked against S15 | **Yes.** `hardware_notes.md` §3.2: names, arguments, alignment, cycle formulas match; package is C67x v2.00 (not C674x); Rev 2.0 interrupt bug and biquad pole rule recorded; ifft scaling conflict found and tested |
| FIFO latency re-checked | **Yes.** 1.33 ms is correct for this board (1 word = L+R per sample); 0.67 ms applies to 2-word I2S frames. Default now 8.81 / 7.67 ms everywhere |
| Calculations re-run | **Yes.** All five scripts re-run; `review_check.py` **49/49 pass** |
| Team block | Unchanged, as asked |
| papers/ in .gitignore | **Yes** |

## Quality check – Update 4 (4 Oct 2026)

| Check | Result |
|---|---|
| Schematic items filled with sheet + net citations | **Yes.** `research/hardware_notes.md` §1.1 and §7: MCLK, BCLK/WCLK, AXR pins, I2C instance, LINE IN / MIC IN / LINE OUT. Still open: pin-mux values, CPU clock, S19 header constants |
| S19 identified and checked | **Yes.** Welch, Wright & Morrow textbook support file (not TI); no version number; matches the schematic (`hardware_notes.md` §8) |
| FIFO default applied everywhere | **Yes.** `05`, `06`, `07` T5, `08` R3/R15, `01`, `REVIEW.md`, this file; latencies from `calc/latency_check.py` |
| Calculations re-run | **Yes.** All five scripts re-run 4 Oct 2026; `review_check.py` **43/43 pass** |
| Abstract length | 151 words |
| papers/ in .gitignore | **Yes** |

## Quality check – Update 3 (3 Oct 2026)

| Check | Result |
|---|---|
| Hardware facts extracted with citations | **Yes.** `research/hardware_notes.md`: every fact cites document + page/table. Items needing the schematic are marked NOT FOUND |
| Consistency across files, scripts and figures | **Yes, after fixes.** 21 issues found and listed in `research/REVIEW.md` §b; 18 fixed, 3 open (need schematic or board measurement). `calc/review_check.py` recomputes 39 numbers quoted in the docs: **39/39 pass** |
| Calculations re-run | **Yes.** `design_check.py`, `gain_check.py`, `cpu_check.py` and `review_check.py` were re-run on 3 Oct 2026; outputs are in `calc/` |
| Fits the real board | **Yes.** CPU ≤ 16 % worst case; ≈ 15 KB of 256 KB L2; 48 kHz supported. One thin margin (FFT with interrupts off at 300 MHz) is documented with a mitigation |
| Syllabus labels honest | **Yes, after fixes.** Four items relabelled "Explained (+ measured)" |
| papers/ in .gitignore | **Yes**; all 13 PDFs saved in `papers/` |

## Quality check – Update 2 (3 Oct 2026)

| Check | Result |
|---|---|
| All 6 PDFs saved and listed in `02_sources.md` with full citation | **Yes.** Saved in `papers/` under dated names: S26 (PDF1), S27 (PDF2, new), S1 (PDF3), S2 (PDF4), S3 (PDF5), S4 (PDF6). Each row in `02_sources.md` A1/A3 gives the full citation, the saved file name and the read status. PDF4 was identified as the PMC author manuscript of S2 (IEEE Access 10:54301–54312). |
| No placeholder audiogram values remain | **Yes.** A text search of all `.md` and `.py` files for the old values (20/30/40/50/60/65 dB HL, the 12.5 dB B1 gain, the 1.33 dB Mode B error, "sample audiogram") finds none. The only remaining mentions are the word "placeholder" in `research/audiogram.md` and `CHANGES.md`, which record the replacement. `calc/design_check.py` now reads Bisgaard N3 from `calc/audiograms.py`. |
| Every changed number traces to a table, equation or `calc/` script | **Yes.** Audiogram values cite Bisgaard Table 2/4. Gains, errors, eq. (15)/(16) results and the 60 dB lengths come from `calc/gain_check_output.txt` or `calc/design_check_output.txt`. Literature numbers cite PDF + table/equation/section (patent by column). Interpolation and WDRC worked examples show their working. |
| Gain-rule citation | **Fixed.** Half-gain → Lybarger (1944, 1963). NAL-R → Byrne & Dillon (1986), *Ear & Hearing* 7(4):257–265. Both are marked "cited via Venema 2001 [S27], original not read". The ×0.4 variant is labelled our illustration, not the NAL-R formula. |
| Yang/Liu/Jou upgraded to full text | **Yes.** Class-2 limits, delay targets with Stone & Moore refs, eqs. (15)–(17) applied to our design. A printed-factor inconsistency in their worked example (p. 1390) is noted. |
| Core design unchanged | **Yes.** No source shows 48 kHz / 5 bands / Mode A–B is wrong. One limitation (steep loss in Mode A) is documented with a scope-only PROPOSED CHANGE. |
| Earlier errors found and corrected | 4 corrections from the full texts (S2 tap counts, S2 band list, S4 class-0 standard, S5 authors). See `CHANGES.md`. |

### Still in force from the first pack

- Latency and CPU estimates are calculated, not guessed.
- Every syllabus topic is mapped.
- Mermaid diagrams render.

## Gaps that remain, and what to do

The full list is in `research/REVIEW.md` §e.

1. **Nothing left to download** for coding or bring-up.
2. **Confirm:** the DSP library swap to the C674x DSPLIB 3.4.0.0 (PROPOSED CHANGE).
3. **Board checks:** CPU clock (expect 300 MHz), Read FIFO + EDMA with the derived PaRAM values, LEDs, Mode B latency, ifft self-check.
4. **Missing papers (background only):** S5, S6, S7. **Originals not read:** Lybarger, Byrne & Dillon, Stone & Moore, ANSI S1.11/S3.22.
5. **MATLAB not run** (numbers come from Python/SciPy).

## Ready for Claude Code?

**Yes.** Every document, library and board value the code needs is now in the pack with a citation.

Done:

- [x] Design fixed and re-checked (55/55).
- [x] Codec, I2C, McASP values confirmed against the schematic and the S19 code; board file chosen (`LCDK6748_Support_DSP.c`) with swap steps (`hardware_notes` §10).
- [x] I/O: EDMA + Read FIFO (4), Write FIFO off; RFIFOCTL, DMA port, PaRAM values from the TRM.
- [x] LED pin-mux from the TRM; LED plan decided.
- [x] Clock: 300 MHz from the GEL; read-out formula from the TRM.
- [x] DSP library: C674x DSPLIB 3.4.0.0, exact include/link settings.
- [x] Fallback I/O modes for "no external input".

You still must do (on the board / by hand):

1. Confirm the library swap (C674x DSPLIB 3.4.0.0).
2. In CCS 7.2, create the target configuration **LCDK C6748** (TI GEL `C6748_LCDK.gel`) with the lab emulator.
3. After connecting, read PLLC0 registers (`hardware_notes` §1.7) → expect 300 MHz; confirm with TSCL.
4. Run the loopback (`IO_LIVE`, LINE IN → LINE OUT, powered speakers / HP amp); check XSTAT/RSTAT.
5. Turn on the Read FIFO with the TRM settings; if it fails, fall back to `DSP_Init()` per-sample (FIFO off).
6. Check LEDs D4–D6 light with the new pin-mux.
7. Run the ifft self-check once (expected gain 1).
8. If no source or speakers on a given day, use `IO_STORED_LINEOUT` or `IO_INTERNAL`.
