function hl = hl_at(aud, f, P)
%HL_AT Threshold by linear interpolation on log2(f), held flat outside 250-6000 Hz.
f = min(max(f, P.freqs(1)), P.freqs(end));
hl = interp1(log2(P.freqs), aud, log2(f));
end
