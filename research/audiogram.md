# Audiograms and Band Gains (replaces the placeholder audiogram)

**Labels:**

- **[Bisgaard T2]** / **[Bisgaard T4]**: value read from Bisgaard, Vlaming & Dahlquist (2010), Table 2 or Table 4 (`papers/2010_Bisgaard_standard_audiograms.pdf`, p. 116–117).
- **interpolated**: our calculation from two table values. The working is shown.
- **our calculation**: computed by `calc/audiograms.py` / `calc/gain_check.py`. Full output is in `calc/gain_check_output.txt`.

> **Naming note.** In this file "S2" means Bisgaard's steep audiogram S2, **not** source [S2] in `02_sources.md`. Source IDs: Bisgaard = [S26], Venema = [S27].

## 1. Source audiograms (dB HL)

| Audiogram | 250 | 375 | 500 | 750 | 1000 | 1500 | 2000 | 3000 | 4000 | 6000 | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **N2** – Mild | 20 | 20 | 20 | 22.5 | 25 | 30 | 35 | 40 | 45 | 50 | [Bisgaard T2] |
| **N3** – Moderate | 35 | 35 | 35 | 35 | 40 | 45 | 50 | 55 | 60 | 65 | [Bisgaard T2] |
| **S2** – Mild, steep sloping | 20 | 20 | 20 | 22.5 | 25 | 35 | 55 | 75 | 95 | 95 | [Bisgaard T4] |

Two points from the paper's own text (p. 117):

- The 375 Hz and 750 Hz columns were themselves added by the authors through interpolation.
- A few values were edited slightly to straighten the curves.

The tables stop at 6 kHz. **There is no 8 kHz value**, and we do not extrapolate one.

**Why these three.**

- N2 and N3 cover the mild and moderate flat/moderately sloping range.
- S2 is a steep high-frequency loss. We use it as a stress test because steep slopes are where wide bands struggle.
- Sokolova et al. 2022 [PDF4, §IV and Fig. 12] tested with the "ISMADHA standard audiograms". Bisgaard et al. describe this set as developed by the ISMADHA working group (p. 113–114), so our test cases match theirs.

## 2. Mapping to our five bands

Our bands are split at 750 Hz, 1.5, 3 and 6 kHz (`05_system_design.md` §4).

**Correction to the request.** 750 Hz, 1.5, 3 and 6 kHz are our **crossover (edge) frequencies**, not band centres. We therefore pick a representative frequency inside each band:

| Band | Representative frequency | How the HL value is obtained | Label |
|---|---|---|---|
| B1 (< 750 Hz) | 250–500 Hz region | Mean of the 250, 375 and 500 Hz table values (the band has no lower edge) | our calculation |
| B2 (750–1500 Hz) | √(750·1500) = **1061 Hz** (geometric centre) | Linear interpolation on log₂(f) between 1000 and 1500 Hz | interpolated |
| B3 (1.5–3 kHz) | √(1500·3000) = **2121 Hz** | Between 2000 and 3000 Hz | interpolated |
| B4 (3–6 kHz) | √(3000·6000) = **4243 Hz** | Between 4000 and 6000 Hz | interpolated |
| B5 (> 6 kHz) | 6000 Hz | Table value at 6000 Hz, the nearest available. The band's audiometric centre (8 kHz) is not in the table | from table |

**Interpolation working (example: N3, B2).**

- The weight for 1061 Hz is t = log₂(1061/1000) / log₂(1500/1000) = 0.0854 / 0.585 = 0.146.
- HL = 40 + 0.146 × (45 − 40) = **40.73 dB**.
- The same t = 0.146 applies to B3 and B4. Each centre is 1.0607× its lower table frequency (1061/1000, 2121/2000, 4243/4000), and each table pair is a 1.5× step, so the weight is identical.

### Band HL values (dB HL)

| Band | N2 | N3 | S2 | Label |
|---|---|---|---|---|
| B1 | 20.00 | 35.00 | 20.00 | our calculation (mean of T2/T4 values) |
| B2 | 25.73 | 40.73 | 26.45 | interpolated |
| B3 | 35.73 | 50.73 | 57.90 | interpolated |
| B4 | 45.73 | 60.73 | 95.00 | interpolated (S2: 4 k and 6 k are both 95) |
| B5 | 50 | 65 | 95 | from Bisgaard T2/T4 (6000 Hz column) |

## 3. Gain rules

| Rule | Formula used here | Source and status |
|---|---|---|
| **Half-gain** | Gain = 0.5 × HL | Half-gain rule attributed to **Lybarger (1944, 1963)**. Cited via Venema (2001), *The NAL-NL1 Fitting Method*, AudiologyOnline (`papers/2001_Venema_NAL-NL1_fitting_method.pdf`, "Fitting Rule History"). **Original not read.** |
| **"Slightly less than half"** (NAL-R-style) | Gain = 0.4 × HL | Venema (2001) describes **NAL-R (Byrne & Dillon, 1986, *Ear & Hearing* 7(4), 257–265)** as giving slightly less than half gain across frequencies. **Byrne & Dillon original not read.** The factor **0.4 is our choice** to illustrate the trend. **It is not the NAL-R formula** |
| Gain cap | min(gain, 30 dB) | DESIGN CHOICE (unchanged): limits feedback and clipping on the bench |

Venema (2001) also notes that NAL-RP adds about 10 dB above half-gain when the 0.5/1/2 kHz average loss exceeds 60 dB. Our three audiograms have averages (from the T2/T4 values) of 26.7 (N2), 41.7 (N3) and 33.3 (S2) dB HL, so this does not apply (our calculation).

### Per-band gains (dB, capped at 30)

| Band | N2 half | N2 ×0.4 | **N3 half (DEFAULT)** | N3 ×0.4 | S2 half | S2 ×0.4 |
|---|---|---|---|---|---|---|
| B1 | 10.00 | 8.00 | **17.50** | 14.00 | 10.00 | 8.00 |
| B2 | 12.86 | 10.29 | **20.36** | 16.29 | 13.23 | 10.58 |
| B3 | 17.86 | 14.29 | **25.36** | 20.29 | 28.95 | 23.16 |
| B4 | 22.86 | 18.29 | **30.00** (cap; 30.36) | 24.29 | 30.00 (cap; 47.5) | 30.00 (cap; 38.0) |
| B5 | 25.00 | 20.00 | **30.00** (cap; 32.5) | 26.00 | 30.00 (cap; 47.5) | 30.00 (cap; 38.0) |

All values are our calculation (factor × band HL from §2, then the cap).

**DEFAULT – confirm with team: N3 with the half-gain rule** becomes the project's main gain table. It replaces the old placeholder. N2 and S2 are extra test cases.

## 4. How well each mode follows the targets (simulated, our calculation)

- **Target** = factor × HL interpolated at each test frequency, capped at 30 dB.
- **Mode A** is simulated with tones at 250 Hz … 8 kHz.
- **Mode B** is checked as a 129-tap frequency-sampling FIR over 250 Hz–8 kHz.

| Case | Mode A max error | Mode A worst spur | Largest step between adjacent bands | Mode B max error |
|---|---|---|---|---|
| N2 half | 1.01 dB | −66.7 dBc | 5.00 dB | 0.22 dB |
| N2 ×0.4 | 0.82 dB | −66.8 dBc | 4.00 dB | 0.18 dB |
| **N3 half** | **1.53 dB** (at 750 Hz) | −66.7 dBc | 5.00 dB | **0.38 dB** |
| N3 ×0.4 | 1.20 dB | −66.8 dBc | 4.00 dB | 0.33 dB |
| S2 half | **6.82 dB** (at 1.5 kHz) | −66.3 dBc | 15.73 dB | 0.49 dB |
| S2 ×0.4 | **5.20 dB** (at 1.5 kHz) | −66.4 dBc | 12.58 dB | 0.45 dB |

**What this means.**

- **N2 and N3:** both modes stay within the 3 dB "just noticeable" limit that Sokolova et al. use (PDF3 §V; PDF4 §IV).
- **S2:** the 15.7 dB jump between B2 and B3 cannot be followed by 5 octave-wide bands. Mode A overshoots by 6.8 dB at 1.5 kHz. Mode B (372 Hz grid) follows within 0.5 dB.

**PROPOSED CHANGE – confirm (scope only, no structural change).**

- State in the report that Mode A (5 octave bands) is intended for flat to moderately sloping losses (Bisgaard N-type).
- Steep losses (S-type) are handled by Mode B.
- The 11-band half-octave layout of S2 would fix this in Mode A but is outside our latency budget with linear-phase filters (`05` §4).

## 5. Where these numbers are used

- `05_system_design.md` §6 (gain table and tone-test results).
- `calc/design_check.py` (default N3 half-gain).
- `calc/fig_modeA_bands.png` (composite curve).
- Test T2 in `07_testing_plan.md`: run all six cases from the table above.
