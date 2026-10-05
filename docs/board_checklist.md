# Board checklist (days 6–8): bring-up, tests and what to send back

Work through the steps in order. Each step names the program file to load, what to do, and what to send. **If a step fails, stop and send its "Send" items.** I fix the code and you continue from that step.

Every number I ask for is read in CCS. The ISRs and the processing code are the same in every build; only the switches in `ccs/hearing_aid/config.h` change.

## 0. Before you start (on this PC)

1. Fetch the third-party board files (not in git because of their licence):

```bash
python tools/fetch_board_files.py
```

2. Build all 12 board programs:

```bash
ccs\hearing_aid\build.bat
```

   Each program lands in `ccs\build\<name>\<name>.out`. The table at the end of this file lists them.
3. Optional: to edit and debug inside CCS instead, use **Project → Import CCS Projects** and pick `ccs/hearing_aid`. The project links the repository's source files rather than copying them.
4. Connect the board as in `docs/board_smoke_test.md` (target **LCDK C6748**, TI GEL, 300 MHz). Finish the smoke test first.

**How to load a program.** Connect to the target, then **Run → Load → Load Program…**, choose the `.out`, then **Run → Resume (F8)**. To read results, use **Run → Suspend**, then **View → Expressions**, type the variable name and expand it.

**Variables you will read**

| Variable | Meaning |
|---|---|
| `g_prof` | `isr_max`/`isr_count`/`isr_sum`: cycles per audio interrupt. `bg_*`: cycles per Mode B FFT block. `cpu_hz_est`: CPU clock measured over 48 000 samples. `rstat`/`xstat`: McASP error flags |
| `g_ha` | `mode` (0 = A, 1 = B), `preset` (0 N3, 1 N2, 2 S2, 3 bypass), `clips` (samples limited), `overruns` (Mode B deadline misses) |
| `g_ifft_gain` | start-up check of the inverse FFT scaling |
| `g_int[0]`, `g_int[1]` | `IO_INTERNAL` results for Mode A and Mode B |
| `g_lab` | lab experiment results |

## 1. CPU clock (expect 300 MHz)

1. If you did the smoke test, you already have the five PLL register values (step 3 there). Otherwise read them now with the Memory Browser: PLLCTL `0x01C11100`, PLLM `0x01C11110`, PREDIV `0x01C11114`, PLLDIV1 `0x01C11118`, POSTDIV `0x01C11128`.
2. The second, independent check comes in step 3: `g_prof.cpu_hz_est` counts TSCL cycles during exactly 1 s of audio (48 000 codec samples).

**Send:** the five values, and later `g_prof.cpu_hz_est`. Expected: 300 000 000 ± 0.01 %. The codec's 24.576 MHz crystal is independent of the CPU's 24 MHz crystal, so the agreement checks both.

## 2. Pure loopback with our I/O code, FIFO off (`loop_fallback.out`)

Input is copied to output with no processing. This tests our build, vector table and interrupt routing using the book's proven per-sample McASP path.

1. Load `ccs\build\loop_fallback\loop_fallback.out`. Play music into LINE IN and listen on LINE OUT (powered speakers or a headphone amplifier).
2. After 30 s, Suspend.

**Send:**
- audio yes/no, and any clicks
- `g_prof.isr_max`, `g_prof.isr_count`, `g_prof.cpu_hz_est`
- `g_prof.rstat`, `g_prof.xstat`

## 3. Pure loopback, EDMA + Read FIFO on (`loop_fifo.out`)

This is the decided I/O scheme: Read FIFO 4 words, Write FIFO off, EDMA 4-sample ping-pong. It is the first time our own McASP/EDMA set-up runs, so this is the step most likely to need a fix.

1. Load `loop_fifo.out` and play music for 30 s, then Suspend.

**Send:**
- audio yes/no, and any clicks
- `g_prof.isr_max`, `g_prof.isr_count` (≈ 12 000 per second of running), `g_prof.cpu_hz_est`, `g_prof.rstat`, `g_prof.xstat`
- In the Memory Browser: `0x01D01018` (RFIFOCTL, expect `0x00010401`) and `0x01D0101C` (RFIFOSTS, the number of words in the FIFO, 0–4)

**If there is no audio:**
- Send RSTAT, XSTAT and RFIFOCTL.
- Read the EDMA registers: ER `0x01C01000`, EER `0x01C01020`, IPR `0x01C01068`, and the RX PaRAM at `0x01C04000` (8 words).
- Then go to step 9 (fallback). Everything else can run on the fallback while I fix the FIFO path.

## 4. Input channel and LEDs (`live.out`)

`live.out` is the full hearing aid. It starts in Mode A with preset N3.

1. **Channel.** Play `data/board/tone1k_left_only.wav` from the PC, then `tone1k_right_only.wav`.
   - The build processes the codec channel wired to the jack's **tip** (`INPUT_SEL 0`). On the LCDK the tip goes to the codec's right input (schematic S12), and on a standard cable the tip carries the source's **left** channel.
   - Expected: you hear the left-only file and not the right-only one.
   - If it is the other way round, the two 16-bit halves are swapped. Tell me; it is a one-line change (`INPUT_SEL 1`).
2. **Buttons and LEDs.**
   - Press **S2**: LED **D4** toggles (lit = Mode B).
   - Press **S3**: **D5** blinks preset + 1 times (N2 = 2 blinks, S2 = 3, bypass = 4, N3 = 1).
   - Play something loud: **D5** lights when the limiter acts.
3. **Scope (if available).** Probe the **D6** LED signal: it is high while the audio interrupt runs.
   - EDMA build: one pulse every 83.3 µs (4 samples).
   - Its duty cycle is the interrupt CPU load.

**Send:**
- which tone file is heard
- whether D4/D5 behave as described
- a scope photo of D6 with the time base showing a few pulses
- `g_ha.mode` and `g_ha.preset` after a few presses

## 5. ifft scaling check (any build)

Read `g_ifft_gain`. Expected **1.0**: the C674x `DSPF_sp_ifftSPxSP` scales by 1/N. A value of 256 would mean no scaling, and Mode B would be 48 dB too loud.

**Send:** the value.

## 6. Arithmetic test without audio (`internal.out`) — also the "no external input" proof

The DSP runs both modes over the stored test signal (11 tones at −40 dBFS, then noise), with no codec involved, and measures each tone with the Goertzel meter.

1. Load `internal.out`, Resume, wait 5 s, Suspend.
2. Read `g_int[0]` (Mode A) and `g_int[1]` (Mode B), expanded, including `gain_db[0..10]`.
3. **Save Memory** for the output arrays:
   - Memory Browser → right-click → Save Memory.
   - Start address `&g_out[0][0]`, length 96000 words, format TI Data, 32-bit hex. Save as `out_modeA.dat`.
   - Repeat with `&g_out[1][0]` → `out_modeB.dat`.
   - Repeat with `&g_stored[0]` → `g_stored.dat`. This is the board's actual input; the analysis uses it as the reference.
   - I analyse the dumps with `python python/board_compare.py internal out_modeA.dat out_modeB.dat g_stored.dat`.
4. Repeat steps 1–2 with `internal_o0.out` (no optimisation) for the pipelining comparison.

**Expected tone gains** (`results/phase3/board_expected.txt`; pass if within 0.05 dB):

| Hz | 250 | 375 | 500 | 750 | 1 k | 1.5 k | 2 k | 3 k | 4 k | 6 k | 8 k |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Mode A `g_int[0].gain_db` | 17.40 | 17.41 | 17.65 | 19.03 | 20.66 | 23.33 | 25.60 | 28.02 | 29.66 | 30.00 | 30.00 |
| Mode B `g_int[1].gain_db` | 17.59 | 17.50 | 17.27 | 17.53 | 19.67 | 22.50 | 25.00 | 27.50 | 29.89 | 29.99 | 30.02 |

**Real-time criteria** (at 300 MHz):
- Mode A: `g_int[0].max` < 25 000 cycles per 4-sample block.
- Mode B: `g_int[1].bg_max` + 32 × `g_int[1].avg` < 800 000 cycles per 128-sample block.

**Send:** `g_int[0]`, `g_int[1]`, the three `.dat` files, and the `-O0` values of `g_int[0..1].max/avg/bg_max/bg_avg`.

## 7. Each mode live (`live.out`) — tests T2–T5

**Set-up.**
- Use the PC sound card or an audio interface at **48 kHz, 16-bit, stereo**.
- Record: **channel 1 (left) = board LINE OUT**, **channel 2 (right) = the PC's own output**, split off with a 3.5 mm Y-cable.
- Play the exact files in `data/board/`. Each one starts with 0.5 s of silence, a click (alignment marker) and another 0.5 s of silence, so the analysis lines everything up automatically.
- The files are at −40 dBFS. Set the PC playback volume to 100 % and leave it there for every recording.
- If you have no Y-cable, record LINE OUT only, and also make one recording of `T5_clicks.wav` with a cable straight from PC out to PC in. The analysis subtracts the sound card's own delay using that recording.
- **Calibration first.** Press S3 until the preset is **bypass** (D5 blinks 4 times) and record `T2_tones.wav`. This measures the codec + sound-card path, so the band gains can be separated from it.

| Test | File to play | Mode / preset | Send | I run |
|---|---|---|---|---|
| calibration | `T2_tones.wav` | bypass | `rec_bypass.wav` | — |
| T2 band gains | `T2_tones.wav` | A/N3, then B/N3 | `rec_T2_A.wav`, `rec_T2_B.wav` | `board_compare.py rec T2 rec_T2_A.wav --cal rec_bypass.wav --mode A` |
| T3/T4 response | `T4_noise.wav` | A/N3, then B/N3 | `rec_T4_A.wav`, `rec_T4_B.wav` | `board_compare.py rec T4 …` |
| T5 latency | `T5_clicks.wav` | A/N3, then B/N3 (+ loopback cable if no Y-cable) | `rec_T5_A.wav`, `rec_T5_B.wav` (`rec_loop.wav`) | `board_compare.py rec T5 … [--loop rec_loop.wav]`. Expected: Mode A ≈ 8.81 ms, Mode B ≈ 7.67 ms (estimated, `research/calc/latency_check.py`) |
| T6 CPU load | any speech, 60 s | A, then B | `g_prof` (all fields) per mode; D6 scope photo | — |
| T9 crossover spurs | `T9_spur_tones.wav` | A/N3 | `rec_T9_A.wav` | `board_compare.py rec T9 …` (largest single spur ≤ −60 dBc) |
| T10 limiter | `T10_level_steps.wav` (−40 → 0 dBFS in 5 dB steps) | A/N3 | `rec_T10_A.wav`, `g_ha.clips` | `board_compare.py rec T10 …` |

The analysis was tested on fabricated recordings with a known delay and gain (`python python/board_compare.py selftest`): it recovered the gains within 0.1 dB, the latency within 0.05 ms, the coherence and the spur levels.

**Before each mode's run, reset the counters:** in Expressions set `g_prof.isr_max`, `g_prof.bg_max`, `g_ha.overruns` and `g_ha.clips` to 0.

**Also send** `g_ha.overruns` after each run. It must stay 0: a non-zero value means the Mode B FFT missed its 2.67 ms deadline.

## 8. Lab experiments (`lab_*.out`)

For each program: load, Resume, wait 2 s, Suspend, wait for **D5** to light, then expand `g_lab`.

| Program | Read | Expected (from the PC check, `results/phase3/lab_check.txt`) |
|---|---|---|
| `lab_arith.out` | `arith_cycles[0..3]`, `arith_result[0..3]` | int16, int32 and double results equal (−1 782 181 120); float32 slightly off (24-bit mantissa) |
| `lab_conv.out` | `conv_linear`, `conv_circ4`, `conv_circ6` | 1 3 6 9 7 4 / 8 7 6 9 / 1 3 6 9 7 4 |
| `lab_dft.out` | `dft_cycles[0..2]`, `dft_err[0..1]` | errors ≈ 4e-6 |
| `lab_bench.out` | `bench[0..15]`, `bench_err[0..15]`, `icfftr2_gain` | errors < 1e-5; `icfftr2_gain` = 256 |
| `lab_bench_o0.out` | `bench[0..15]` | same, slower (the `-O0` vs `-O3` comparison) |

The order of `bench[]` is: fir_gen, plain-C FIR, DSPLIB biquad, plain-C biquad, own FFT, cfftr2_dit, C bit reversal, icfftr2_dif, cfftr4_dif, fftSPxSP, ifftSPxSP, HPF × 48 samples, Mode A × 48 samples, Mode B block, ha_process(4) in Mode A, ha_process(4) in Mode B.

**Send:** a screenshot of each expanded `g_lab`, or the values typed out.

## 9. Fallback I/O (`fallback.out`) and stored-signal output (`stored.out`)

1. **`fallback.out`** is the full hearing aid on the per-sample path with the FIFO off (8.60 / 7.46 ms expected). Run it for 30 s and check the audio and `g_ha.overruns`.
   **Send:** audio yes/no, `g_prof.isr_max`.
2. **`stored.out`** plays the stored signal (no source needed) through the hearing aid to LINE OUT.
   - Default: the 11 tones and noise, looping every 2 s.
   - For speech: after Load Program, stay halted at `main`. Use **Tools → Load Memory**, file `data/board/speech_stored.dat`, start address `0xC0000000`. In Expressions set `g_stored_loaded = 1`, then Resume.
   - If CCS rejects the `.dat` header, choose the raw binary option and load `speech_stored.bin` at the same address.

   **Send:** audio yes/no, `g_prof.xstat` (0 = no underrun), `g_prof.isr_max`.

## Programs built by `build.bat`

| Program | IO_MODE | I/O | Purpose |
|---|---|---|---|
| `loop_fallback` | live | per-sample, FIFO off | step 2: I/O only, no processing |
| `loop_fifo` | live | EDMA + Read FIFO | step 3: I/O only, no processing |
| `live` | live | EDMA + Read FIFO | the hearing aid (default) |
| `fallback` | live | per-sample, FIFO off | hearing aid on the fallback I/O |
| `stored` | stored → LINE OUT | EDMA + Read FIFO | no signal source needed |
| `internal`, `internal_o0` | internal | none | no codec needed; correctness and cycles, `-O3`/`-O0` |
| `lab_arith`, `lab_conv`, `lab_dft`, `lab_bench`, `lab_bench_o0` | — | none | lab experiments |

## Summary of what to send back

| Step | Items |
|---|---|
| 1 | 5 PLL register values; `g_prof.cpu_hz_est` |
| 2–3 | audio yes/no, clicks, `g_prof` (`isr_max`, `isr_count`, `cpu_hz_est`, `rstat`, `xstat`), RFIFOCTL/RFIFOSTS |
| 4 | which tone file is heard, LED behaviour, D6 scope photo |
| 5 | `g_ifft_gain` |
| 6 | `g_int[0]`, `g_int[1]` (`-O3` and `-O0`), `out_modeA.dat`, `out_modeB.dat`, `g_stored.dat` |
| 7 | `rec_bypass.wav` and the T2, T4, T5, T9, T10 recordings (stereo: LINE OUT left, source right); `g_prof` and `g_ha.overruns` per mode |
| 8 | `g_lab` for the five lab programs |
| 9 | fallback and stored: audio yes/no, `xstat`, `isr_max` |
