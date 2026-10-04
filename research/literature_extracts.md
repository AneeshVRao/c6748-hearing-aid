# Literature Extracts – Yang/Liu/Jou 2016, Sokolova 2021/2022, US 12,627,936 B2

**Citation format.** Each number cites the PDF in `papers/` plus a table, equation, figure or section. Quotes are under 15 words. Everything else is paraphrased.

**Comparison numbers.** Numbers for our system are labelled "our calculation" and come from `calc/gain_check_output.txt` or `calc/design_check_output.txt`.

| Tag | PDF in `papers/` |
|---|---|
| **PDF3** | `2021_Sokolova_multirate_audiometric_filter_bank_Asilomar.pdf` |
| **PDF4** | `2022_Sokolova_realtime_multirate_multiband_amplification_IEEEAccess_PMC.pdf` (PMC author manuscript of S2) |
| **PDF5** | `2016_Yang_Liu_Jou_ANSI_S1.11_relaxation_TASLP.pdf` |
| **PDF6** | `2026_US12627936B2_realtime_multirate_multiband_amplification.pdf` |

Mapping to `02_sources.md` IDs: PDF3 = [S1], PDF4 = [S2], PDF5 = [S3], PDF6 = [S4].

> **Scope warning.** PDF3, PDF4 and PDF6 use **32 kHz** processing and **10–11 half-octave** bands. PDF5 uses **24 kHz** and **18 one-third-octave** bands. We use **48 kHz** and **5 octave** bands. Their numbers describe *their* systems. We reuse methods and formulas, not results.

---

## Part A – Yang, Liu & Jou (2016), full text read (PDF5)

### A1. ANSI S1.11 class-2 limits (PDF5 §II-A, p. 1381–1382; §II-B step 5, p. 1387)

| Limit | Value | Location |
|---|---|---|
| Passband ripple of each sub-filter | ±0.5 dB | §II-A, p. 1381 |
| Stopband attenuation | > 60 dB | §II-A, p. 1382 |
| Ripple of the summed output of all bands | ±0.5 dB | §II-B(5), p. 1387 |
| Ripple after their gain equalisation, suggested | within ±0.5 to 1.5 dB | §II-B(5), p. 1387 |
| Allowed maximum gain difference (class 2) | 60 dB | §II-B(2), p. 1386 |

- The authors choose class 2 on purpose, to avoid the long delay of tighter classes. They note its 60 dB stopband suffices for most hearing losses (§II, p. 1381).
- **Our filters compared with class 2 (our calculation):**
  - G stopband 52.5 dB and F 51.1 dB are **below** the 60 dB class-2 figure.
  - Unity-gain summed ripple of +0.020 / −0.010 dB is far **inside** ±0.5 dB.
- **Cost of reaching 60 dB with the same band edges** (our calculation, `gain_check.py`): G needs 27 taps and F needs 39 taps (Kaiser β = 6.0). Mode A delay becomes T0 = 480 samples = 10.00 ms, or 10.79 ms with the codec. That is over the 10 ms target.
- **Decision: keep 52 dB** (DESIGN CHOICE, unchanged). This is the trade PDF5 argues for: relax the spec to meet delay. For N3, the spread between the highest and lowest band gain is 12.5 dB, and the largest step between adjacent bands is 5 dB (our calculation). Both are far below the 52 dB isolation.
- Strictly, ANSI S1.11 defines limits for octave and fractional-octave filters relative to each band's mid-band frequency (§II-A). Our complementary octave bands were **not** checked against the full 19-break-point mask (Fig. 1). We only compare headline numbers.

### A2. Delay target and its references

- PDF5 §I (p. 1381): octave filter-bank delay was considered acceptable only up to 10–20 ms. It cites Stone & Moore 1999 [12] and 2002 [13].
- PDF5 §I and §II-B: Liu et al. [15] relaxed the spec to meet a **10 ms** delay. PDF5's delay-oriented designs use the same 10 ms constraint (§IV-A, p. 1388).
- PDF5 §IV-C (p. 1390): more severe hearing loss tolerates more delay, citing Stone & Moore 2005 [27]. For that reason their patient designs use 10 ms and 20 ms limits.
- PDF5 conclusion of §IV-D (p. 1391): recommends latency within 10 ms.
- PDF3 §III-C (p. 1439) and PDF6 (cols. 7–8) give the same ~10 ms limit, citing Stone & Moore 1999 (PDF3 ref. [16]).
- **Status:** the Stone & Moore papers are cited via PDF3 and PDF5. The originals were not read.

### A3. Delay formula, eq. (15), applied to Mode A

PDF5 eq. (15), p. 1386:

d_n = Σ_i ((N_i − 1)/2) · (fs / fs_i)

- d_n is in samples at the input rate fs.
- The sum runs over all K filters (odd length N_i) in band n's path, where filter i runs at rate fs_i.

**Our deepest path (band B1)** passes through G at 48, 24, 12 and 6 kHz, then F at 6, 12, 24 and 48 kHz (our calculation):

d = 10·(1 + 2 + 4 + 8) + 15·(1 + 2 + 4 + 8) = 150 + 225 = **375 samples = 7.81 ms**

This is identical to the `design_check.py` recursion T_k = 25 + 2T_{k+1} and to the simulated impulse peak.

**Bands before alignment** (eq. (15) on each path, our calculation):

| Level | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Delay (samples) | 10 | 45 | 115 | 255 |

The residual B1 path is 375. The alignment delays in our design pad every band up to 375.

**Note on PDF5's own worked example (p. 1390).** It prints the F22 delay as (48/2)(1/2) + (96/2)(4) + (48/2)(1/2) = 240 samples. With the printed factors the sum is 12 + 192 + 12 = 216. With factors of 1 (anti-aliasing filters running at fs) it is 24 + 192 + 24 = 240, which matches their stated 10 ms at 24 kHz. We follow eq. (15) as written and do not rely on the worked example.

### A4. Complexity formula, eq. (16), applied to Mode A

PDF5 eq. (16), p. 1386:

c_n = Σ_i ((N_i + 1)/2) · (fs_i / fs)

This counts multiplies per input sample, assuming a symmetric odd-length FIR needs (N + 1)/2 multiplies per output.

| Counting method | Mult. per input sample | Source |
|---|---|---|
| eq. (16), G and F treated as full symmetric FIRs at fs_k, shared tree counted once | **50.62** | our calculation |
| eq. (16) for G + half-band/polyphase F (9 unique multiplies per 2 outputs) | 29.06 | our calculation |
| … + band gain multiplies (1 + ½ + ¼ + ⅛ + 1/16) | **31.00** | our calculation |
| `design_check.py` count: G without symmetry (21), F polyphase (8.5), +3 gain/add ops per level sample | 61.0 ops | our calculation (earlier pack) |

**Conclusion.** The earlier "61 ops/sample" was a deliberately conservative count that includes adds and ignores symmetry. With PDF5's convention, the real multiply count is about **31–51 per sample**, depending on whether half-band zeros are exploited. The CPU-load estimates in `05` §9 are therefore on the safe side, and we leave them unchanged.

### A5. Gain equalisation, eq. (17) – do we need it?

PDF5 eq. (17), p. 1387:

ΔP(n) = 10·log10(10^(0.1·g(n)) + Σ_i 10^(−0.1·A(n,i)))

- It estimates the level at each mid-band frequency from the band's own gain g(n) plus leakage A(n, i) from neighbours.
- g(n) is then optimised (e.g., MATLAB `fmincon`) so that the summed response is flat. This is needed because relaxed, overlapping 1/3-octave filters raise the ripple.
- Example in the paper: g(24) = 2.94 dB makes ΔP(24) = 0 (Fig. 8a, p. 1387).

**For us: not needed.** Our bands are complementary by construction. Each high band is "input minus lowpass", so with equal gains the sum is the delayed input. The simulated ripple is +0.020/−0.010 dB (our calculation, `05` §8), against PDF5's ±0.5 dB target.

The related idea in PDF5 eq. (18)–(20) adjusts band gains so that the *combined* response hits the prescription despite leakage. That **would** help the S2 steep-loss case (`research/audiogram.md` §4). It is listed as an optional extra and was not implemented.

### A6. Other useful points

- PDF5 argues for linear-phase FIR in hearing aids: phase distortion harms harmonicity and binaural cues (§I, p. 1380). This supports our linear-phase choice, and is a reason to treat minimum phase only as an optional extra.
- **Rational vs integer rate conversion** (§III-A, Table II): multi-stage fractional SRCs cut multiplies (192 MPY/S) but cost delay (13.58 ms). The 10 ms designs use 226 MPY/S. We use only ↓2/↑2, so no fractional SRC delay arises.

---

## Part B – Sokolova 2021 (PDF3), Sokolova 2022 (PDF4), patent (PDF6)

### B1. Complementary filters for perfect reconstruction

- **Method.** Design one high-pass edge. Its complement is the all-pass (an impulse) minus that filter. Each band-pass is built by convolving a high-pass with the complementary low-pass of its neighbour. Adjacent band edges are therefore exact complements and the bands sum to an all-pass (PDF3 §II-C; PDF6 cols. 3–4; PDF4 §II).
- **Stated accuracy:**
  - PDF3 reports perfect reconstruction within ±0.01 dB (§I, §VI) and composite ripple within ±0.15 dB (§II-B).
  - PDF6 (cols. 3–4) states reconstruction within ±0.15 dB.
- **Our design** uses the same principle in a tree form: band = delayed input − G·input (`05` §2). Simulated ripple is +0.020/−0.010 dB (our calculation).

### B2. Cascaded 2:1 resamplers vs single stage, and polyphase half-band filters

Workload figures (all for **their** 32-sample frames at 32 kHz):

| Item | Value | Source |
|---|---|---|
| Single-stage 1:8 upsampler | ~261-tap filter → 8352 MAC per 32-sample output frame | PDF3 §III-A, Fig. 4; PDF4 §II-C; PDF6 cols. 5–6 |
| Cascade of three 1:2 half-band upsamplers | 680 MAC (~12× less) | Same |
| Conventional 2:1 downsampler | 1120 MAC per 32-sample input frame | PDF3 §III-A, Fig. 5 |
| Polyphase 2:1 half-band downsampler | 304 MAC | PDF3 §III-A, Fig. 5 |
| Polyphase saving | ≈ factor M (resampling ratio) | PDF4 §II-C; PDF6 |

**Totals:**

| System | Single-rate | Multirate | Saving | Source |
|---|---|---|---|---|
| 10-band bank (PDF3) | 4278 ops/sample | 469.6 | 9.1× | PDF3 Table II; filters 93 taps each in multirate form, Table I |
| 11-band bank (PDF4/PDF6) | 5982 | 437.69 | 13.67× | PDF4 Table 2; PDF6 Table 2 (cols. 6–7) |
| 11-band bank, single-rate taps | 53 (8 kHz) … 1232 (250–500 Hz) | 77 each | | PDF4 Table 1 |

**Use in our design.** Our F is a polyphase half-band (17 non-zero taps of 31). Our tree uses only 2:1 stages, the same strategy. Our multirate saving is 5.1× (our calculation, `05` §9). It is smaller because we have only 4 levels and short filters.

### B3. Delay alignment and linear vs minimum phase

- **Alignment.** Bands at lower rates arrive later. Delays are inserted on the faster bands so all bands line up. Without alignment the composite response is distorted, and some listeners hear this as echo or timbre change (PDF3 §III-C, Figs. 6–7; PDF4 §II-E; PDF6).
  - PDF3: high bands ~1.5 ms, 3–4 kHz bands ~4 ms unaligned, ~18 ms aligned.
- **Latency figures:**

| System | Linear phase (aligned) | Minimum phase | Source |
|---|---|---|---|
| PDF3 (10 bands) | ~18 ms | < 5 ms (preliminary) | PDF3 §III-C |
| PDF4/PDF6 (11 bands) | ~32 ms | 5.4 ms | PDF4 §II-E; PDF6 |
| PDF4/PDF6, compared with Kates | 5.43 ms (11 bands) vs 4.03 ms (Kates, 6 bands) | | PDF4 Table 4; PDF6 Table 4 |

- **Minimum phase method:** reflect the zeros outside the unit circle to the inside. The magnitude is unchanged and the delay drops (PDF4 §II-E; PDF6 cols. 7–8).
- **Our design:** linear phase with alignment delays (365/165/65/15 samples), 8.60 ms total with the codec and FIFO off; **8.81 ms with the default (Read FIFO on, Write FIFO off)** (our calculation, `calc/latency_check.py`). Minimum phase stays an optional extra (`05` §10). PDF5 §I warns about phase distortion (A6 above).

### B4. WDRC: envelope, AGC loop, attack/release

- **Envelope.** A Hilbert filter gives a 90°-shifted copy. The envelope is |real + j·imag|. Doing this at each band's reduced rate keeps low bands away from the Hilbert filter's transition near DC (PDF4 §III-B; PDF6 FIG. 1 and cols. 7–8).
- **AGC loop** (PDF4 eq. (1); PDF6 eq. (1), col. 9), all in dB, per sample:

  A[n+1] = A[n] + α·(R[n] − Y[n]),  where Y[n] = X[n] + A[n]

  - A is the gain, X the input level, and R the target output from the WDRC input/output curve.
  - α sets the speed. There is one α for attack and one for release.
- **Closed form** (PDF6 eqs. (2)–(5), cols. 9–10; same as PDF4). Assume a step in X from 55 to 90 dB, with G0 = A1 − 55 and G∞ = A2 − 90. Then A[n] = (G0 − G∞)(1 − α)^n + G∞.
- **Attack/release coefficients:**
  - **PDF6 eq. (6):** α_attack = 1 − (3/(G0 − G∞))^(1/AT) = 1 − (3/(A1 − A2 + 35))^(1/AT)
  - **PDF6 eq. (7):** α_release = 1 − (4/(G0 − G∞))^(1/RT) = 1 − (4/(A1 − A2 + 35))^(1/RT)
  - AT and RT are in **samples at the band's own rate**. The 3 dB and 4 dB settling margins come from the ANSI S3.22 definitions as described in PDF4 §III-C and PDF6 (FIG. 10).
- **Reported accuracy:**
  - Target 10/20 ms at CR 3:1 → measured 10.2/20.5 ms.
  - Kates system: 4.4/37.3 ms.
  - Steady-state error ≤ 3 dB over 847 test points.
  - Sources: PDF4 §IV and Table 3; PDF6.

**Worked example (our calculation, illustration only).** Take a band at 6 kHz rate with CR = 3:1 above the knee, both 55 and 90 dB inputs above the knee, and no MPO limit.

- The output rises by 35/3 = 11.67 dB, so A2 − A1 = 11.67 and A1 − A2 + 35 = 23.33 dB.
- AT = 10 ms × 6000 = 60 samples → α_attack = 1 − (3/23.33)^(1/60) = **0.0336**.
- RT = 20 ms × 6000 = 120 samples → α_release = 1 − (4/23.33)^(1/120) = **0.0146**.

These α's are the loop gain in A[n+1] = A[n] + α(·). They are *not* the same quantity as the one-pole smoother α = e^(−1/(τ·fs)) proposed earlier in `05` §6.

### B5. Does simple WDRC fit our scope? – OPTIONAL – confirm

**Proposal (OPTIONAL – confirm with team):** after the core (Mode A + Mode B with static gains) passes its tests, add per-band WDRC to Mode A:

1. **Level detector.** Use the rectified band signal smoothed per band, rather than a Hilbert filter. This is simpler and adds no filter delay. The Hilbert detector from PDF4 can be a later step.
2. **Static curve.** Below the knee use the linear gain from `research/audiogram.md`; above the knee (−40 dBFS, DESIGN CHOICE) use one compression ratio per band (e.g., 2:1 or 3:1).
3. **AGC loop** from PDF6 eq. (1), with α_attack / α_release from PDF6 eqs. (6)–(7). Compute them offline in MATLAB from AT, RT, CR and each band's rate.
4. **Cost** (our estimate): about 6 ops per band sample (log/level, compare, loop update, gain). That is under 1 % extra CPU at the rates in `05` §9.
5. **Test** with the step-response method of PDF4 §III-C (test T15 in `07`).

**Not included:** feedback cancellation, the MPO controller from PDF3/PDF4 (we keep a simple limiter), and NAL-NL2 targets.
