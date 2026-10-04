function g = gain_curve_db(aud, f, factor, P)
%GAIN_CURVE_DB Per-frequency target: factor x interpolated HL, capped.
g = min(factor*hl_at(aud, max(f, 1), P), P.cap);
end
