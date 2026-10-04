%P2_FIXED_POINT Data path float32 vs Q15: HPF forms, Mode A/B SNR, headroom. Mirror of python/p2_fixed_point.py.
% UNVERIFIED: MATLAB is not installed on the development PC; Python is the verified reference.
P = hearing_aid_params(); fs = P.fs;
q15 = @(v) min(max(round(v*32768), -32768), 32767)/32768;
snr = @(y, r) 10*log10(sum(r.^2)/sum((double(y) - r).^2));
[sp, ~] = audioread(fullfile(fileparts(mfilename('fullpath')), '..', 'data', 'speech_48k.wav'));
s = sp(1:4*fs)/rms(sp(1:4*fs));

% ---- 1. HPF: DF-II-T in single precision vs DF-I in Q15 ----
x = q15(s(1:2*fs)*10^(-20/20)); ref = sosfilt(P.sos, x);
y32 = single(x);
for i = 1:2
    y32 = filter(single(P.sos(i, 1:3)), single(P.sos(i, 4:6)), y32);   % filter() is DF-II transposed
end
c = round(P.sos*2^14); yq = round(x*32768);
for i = 1:2
    xin = yq; yq = zeros(size(xin)); x1 = 0; x2 = 0; y1 = 0; y2 = 0;
    for n = 1:numel(xin)
        acc = c(i,1)*xin(n) + c(i,2)*x1 + c(i,3)*x2 - c(i,5)*y1 - c(i,6)*y2;
        out = min(max(floor((acc + 2^13)/2^14), -32768), 32767);
        x2 = x1; x1 = xin(n); y2 = y1; y1 = out; yq(n) = out;
    end
end
fprintf('HPF SNR: float32 DF-II-T %.1f dB, Q15 DF-I %.1f dB (Python 85.0 / 12.1)\n', snr(y32, ref), snr(yq/32768, ref));

% ---- 2. Mode A float64 vs Q15 (coefficients Q15, gains Q5.10, data Q15 after each filter) ----
gd = band_gains_db(P.aud.N3, 0.5, P); xa = q15(s*10^(-40/20));
refA = mode_a(xa, gd, P);
PQ = P; PQ.G = q15(P.G); PQ.F = q15(P.F);
yA = q15(mode_a(xa, gd, PQ));                    % simplified: rounding at the output only (Python rounds every stage)
fprintf('Mode A, Q15 coefficients + Q15 output rounding: SNR %.1f dB (Python, rounding at every stage: 42.7 dB)\n', snr(yA, refA));

% ---- 3. headroom: 30 dB gain in a 16-bit path ----
t = (0:fs-1).'/fs;
for lvl = [-20 -30 -40 -50]
    xt = q15(sqrt(2)*10^(lvl/20)*sin(2*pi*4000*t));
    fprintf('%d dBFS 4 kHz tone through N3 (30 dB): %d clipped samples\n', lvl, sum(abs(mode_a(xt, gd, P)) >= 32767/32768));
end
