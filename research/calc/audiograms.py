"""Bisgaard et al. (2010) standard audiograms and band-gain mapping.

Source of threshold values: Bisgaard, Vlaming, Dahlquist, Trends in Amplification 14(2):113-120, 2010
(papers/2010_Bisgaard_standard_audiograms.pdf): Table 2 (N1-N7) and Table 4 (S1-S3).
Everything else in this file is OUR CALCULATION.
"""
import numpy as np

FREQS = np.array([250, 375, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000], float)  # Table 2/4 columns
AUDIOGRAMS = {
    "N2": np.array([20, 20, 20, 22.5, 25, 30, 35, 40, 45, 50]),   # Table 2, Mild
    "N3": np.array([35, 35, 35, 35, 40, 45, 50, 55, 60, 65]),     # Table 2, Moderate
    "S2": np.array([20, 20, 20, 22.5, 25, 35, 55, 75, 95, 95]),   # Table 4, Mild (steep sloping)
}

# Mode A bands (index 0 = highest band, matches analyse_synth gains order)
BAND_NAMES = ["B5 (>6 kHz)", "B4 (3-6 kHz)", "B3 (1.5-3 kHz)", "B2 (0.75-1.5 kHz)", "B1 (<750 Hz)"]
# OUR CHOICE of representative frequency per band:
#   B2..B4: geometric centre of the octave band (log-midpoint of the crossovers)
#   B1: mean of the 250, 375, 500 Hz thresholds (band has no lower edge)
#   B5: the 6000 Hz threshold (Bisgaard tables stop at 6 kHz; no extrapolation)
BAND_CENTRES = {"B4": np.sqrt(3000*6000), "B3": np.sqrt(1500*3000), "B2": np.sqrt(750*1500)}

def hl_at(aud, f):
    """Threshold at frequency f by linear interpolation on log2(frequency). Held flat outside 250-6000 Hz."""
    return float(np.interp(np.log2(f), np.log2(FREQS), aud))

def band_hl(aud):
    """Returns list of (band, HL, how) in the analyse_synth order (B5..B1)."""
    out = [("B5", float(aud[-1]), "Table value at 6000 Hz (nearest; table has no 8 kHz)")]
    for b in ("B4", "B3", "B2"):
        fc = BAND_CENTRES[b]
        out.append((b, hl_at(aud, fc), f"interpolated at {fc:.0f} Hz (log-frequency)"))
    out.append(("B1", float(np.mean(aud[:3])), "mean of 250/375/500 Hz table values"))
    return out

RULES = {
    "half": 0.5,   # half-gain rule (Lybarger 1944/1963, cited via Venema 2001)
    "x0.4": 0.4,   # "slightly less than half gain" (NAL-R description in Venema 2001);
                   # the factor 0.4 is OUR CHOICE, NOT the NAL-R formula (Byrne & Dillon 1986 not read)
}
CAP_DB = 30.0      # DESIGN CHOICE (unchanged from earlier pack)

def band_gains_db(aud, factor, cap=CAP_DB):
    return [min(factor*hl, cap) for _, hl, _ in band_hl(aud)]

def gain_curve_db(aud, f, factor, cap=CAP_DB):
    """Target gain vs frequency for Mode B: factor x interpolated HL, capped."""
    f = np.atleast_1d(np.asarray(f, float))
    hl = np.interp(np.log2(np.maximum(f, 1.0)), np.log2(FREQS), aud)
    return np.minimum(factor*hl, cap)
