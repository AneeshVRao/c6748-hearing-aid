# Board smoke test (day 3–4): connect, read the clock, stock loopback

**Goal:** surface hardware problems in week 1, before any of our code exists. Nothing in this test is ours. It uses TI's board files and the book's stock EDMA example, unchanged.

It takes about 45 minutes. Do the steps in order and **stop at the first step that fails**, then send me what that step asks for.

## What you need

- The LCDK C6748 and its 5 V power supply.
- A JTAG emulator from the lab: XDS100v2, XDS110, XDS200, XDS510 or XDS560. The LCDK has no built-in emulator.
- A PC or phone playing music, with a 3.5 mm cable to **LINE IN** (J10, the upper jack).
- **Powered speakers or a headphone amplifier** on **LINE OUT** (J10, the lower jack). Do not plug plain headphones into LINE OUT: the jack is driven by the codec's line drivers, which are not meant for headphones (research/hardware_notes §1.1).
- CCS 7.2 on this PC.

## Step 1 – Target configuration (uses TI's GEL, which sets the CPU to 300 MHz)

1. Connect the emulator to the LCDK's 14-pin JTAG header and to USB. Then power the board.
2. In CCS: **File → New → Target Configuration File**. Name it `LCDK_C6748.ccxml` and click Finish.
3. **Connection:** pick your emulator, for example *Texas Instruments XDS100v2 USB Debug Probe*.
4. **Board or Device:** type `LCDK` in the filter and tick **LCDK C6748**. This is TI's board file `lcdkc6748.xml`, and it loads `C6748_LCDK.gel` automatically.
   - Do **not** use the book's `LCDK_TargetConfiguration.ccxml`. It targets the OMAP-L138 board.
5. Click **Save**, then **Test Connection**.

**Send:** a screenshot of the Test Connection result. The last lines should say the JTAG scan path test succeeded.

## Step 2 – Connect and record the GEL output

1. **View → Target Configurations**, right-click `LCDK_C6748.ccxml` and choose **Launch Selected Configuration**.
2. In the Debug view, right-click the C674X core and choose **Connect Target**.

**Send:** copy and paste the whole Console text. The GEL prints the PLL and DDR set-up while it runs.

## Step 3 – Read the CPU clock (expect 300 MHz)

1. **View → Memory Browser**. Set the format to *32-Bit Hex – TI Style*.
2. Read the five addresses below and write down each 32-bit value:

| Register | Address | What it holds |
|---|---|---|
| PLLCTL | `0x01C11100` | bit 0 = PLLEN (1 means the PLL is in use) |
| PLLM | `0x01C11110` | bits 4–0 = multiplier − 1 |
| PREDIV | `0x01C11114` | bits 4–0 = divider − 1 |
| PLLDIV1 | `0x01C11118` | bits 4–0 = divider − 1 (bit 15 = enable) |
| POSTDIV | `0x01C11128` | bits 4–0 = divider − 1 (bit 15 = enable) |

The CPU clock is f = 24 MHz × (PLLM + 1) / ((PREDIV + 1)(POSTDIV + 1)(PLLDIV1 + 1)). Expected values: PLLM = 24, POSTDIV = 1, PLLDIV1 = 0, PREDIV = 0, which gives 24 × 25 / 2 = **300 MHz** (research/hardware_notes §1.7).

**Send:** the five hex values, or a screenshot of the memory window.

## Step 4 – Stock loopback (book example `Frame_EDMA_6748`, unmodified)

The files are already on this PC under `research/papers/S19_code_2017_02_05/code/`. This example uses 1024-sample frames, so expect about 64 ms of delay. That is normal for this test. It also changes the levels on purpose: **left × 0.5, right × 2**. If you hear that level difference, the DSP is processing the audio.

1. **File → New → CCS Project.**
   - Target: *C674x Floating-point DSP*, device **LCDK C6748**. If that device isn't listed, choose *TMS320C6748*.
   - Connection: your emulator.
   - Compiler version: **TI v8.1.3**. Output format: **ELF**.
   - Template: **Empty Project** (not "with main.c").
   - Name: `smoke_loopback`.
2. Delete any `.cmd` linker file that CCS created in the project.
3. **Project → Add Files… → Copy files** to add:
   - from `common_code/LCDK/`: `AIC3106.h`, `DSP_Config.h`, `LCDK_Support_DSP.h`, `OMAPL138_defines.h`, `tistdtypes.h`, `link6748e.cmd`, `vectors_EDMA.asm`
   - from `research/papers/`: **`LCDK6748_Support_DSP.c`**. Do **not** use `common_code/LCDK/LCDK_Support_DSP.c`: it has no pin-mux set-up and gives no audio (REVIEW issue 27).
   - from `chapter_06/ccs/Frame_EDMA_6748/`: `main.c`, `ISRs.c`, `frames.h`
4. **Project → Properties → Build → C6000 Compiler → Processor Options:** set the silicon version to **6740**.
5. **Project → Build Project.**
6. **Run → Debug** to load the program, then **Run → Resume**. Start the music.
7. Listen for 30 s. Then **Run → Suspend**.
8. In the Memory Browser, read the McASP status registers: **RSTAT `0x01D00080`** and **XSTAT `0x01D000C0`**.
   - Do not open the XBUF or RBUF addresses: reading them in a memory window disturbs the audio (S14 p. 36).
9. In the Expressions view, add `over_run`.

**Send:**
- the build Console output (warnings and errors)
- does audio come out? Yes/no, and is left quieter than right?
- any clicks or dropouts?
- the RSTAT and XSTAT hex values
- the value of `over_run`

## If something fails

| Symptom | Likely cause | What to send me |
|---|---|---|
| Test Connection fails | cable, emulator driver, board power | full Test Connection text |
| GEL errors on connect | wrong board file chosen | Console text |
| Clock is not 300 MHz | different GEL in use | the five register values |
| Build fails | missing file, or a CCS-generated `.cmd` left in the project | Console text and the project file list |
| Builds and runs but no audio | wrong jack, `LCDK_Support_DSP.c` used instead of the replacement, plain headphones on LINE OUT | RSTAT, XSTAT, a photo of the cable set-up |
| Audio with clicks | buffer overrun | RSTAT, XSTAT, `over_run` |
