%P2_STRUCTURES FIR/IIR structures and 16-bit coefficient quantisation. Mirror of python/p2_structures.py.
% UNVERIFIED: MATLAB is not installed on the development PC; Python is the verified reference.
P = hearing_aid_params(); fs = P.fs; x = randn(4000, 1);
[b, a] = sos2tf(P.sos);
fk = (0:64)*fs/129; hB = fs_fir(gain_curve_db(P.aud.N3, fk, 0.5, P), 129);

% ---- structures vs filter() ----
sosG = tf2sos(P.G, 1);                                   % FIR cascade of second-order sections
fprintf('FIR cascade vs direct: %.1e\n', max(abs(sosfilt(sosG, x) - filter(P.G, 1, x))));
% lattice needs every zero strictly inside the circle: min-phase Mode B FIR (cepstrum), not G (correction C12)
nfft = 2^14; c = real(ifft(log(abs(fft(hB, nfft)))));
fold = [c(1), 2*c(2:nfft/2), c(nfft/2+1), zeros(1, nfft/2-1)];
hm = real(ifft(exp(fft(fold)))); hm = hm(1:129);
kF = tf2latc(hm/hm(1));
fprintf('FIR lattice (min-phase Mode B) vs direct: %.1e, max |K| %.4f\n', ...
    max(abs(hm(1)*latcfilt(kF, x) - filter(hm, 1, x))), max(abs(kF)));
fprintf('linear-phase G: last reflection coefficient would be %.3f (= +-1 -> no lattice)\n', P.G(end)/P.G(1));
% frequency-sampling structure: comb (1 - z^-M) then M complex resonators
M = 129; Hk = fft(hB); cmb = filter([1 zeros(1, M-1) -1], 1, x); y = zeros(size(x));
for k = 0:M-1
    y = y + Hk(k+1)*filter(1, [1 -exp(2i*pi*k/M)], cmb);
end
fprintf('FIR frequency-sampling structure vs direct: %.1e\n', max(abs(real(y)/M - filter(hB, 1, x))));
% IIR forms
fprintf('IIR cascade (board) vs 4th-order direct: %.1e\n', max(abs(sosfilt(P.sos, x) - filter(b, a, x))));
[r, p, kd] = residuez(b, a);                             % parallel form
yp = kd*x;
for i = 1:2:numel(p)                                     % residuez returns conjugate pairs adjacently
    yp = yp + real(filter(r(i), [1 -p(i)], x) + filter(r(i+1), [1 -p(i+1)], x));
end
fprintf('IIR parallel vs direct: %.1e\n', max(abs(yp - filter(b, a, x))));
[K, V] = tf2latc(b, a);                                  % lattice-ladder
fprintf('IIR lattice-ladder vs direct: %.1e; K = %s\n', max(abs(latcfilt(K, V, x) - filter(b, a, x))), mat2str(K.', 6));

% ---- 16-bit coefficient words: smallest integer part that fits ----
q16 = @(c) round(c*2^(15 - max(0, ceil(log2(max(abs(c(:))) + 2^-15)))))/2^(15 - max(0, ceil(log2(max(abs(c(:))) + 2^-15))));
f = logspace(log10(20), log10(23999), 3000); Href = freqz(b, a, f, fs);
show = @(name, H, poles) fprintf('%-28s max pole radius %.6f, passband err (>=200 Hz) %.4f dB, gain @20 Hz %.1f dB\n', ...
    name, max(abs(poles)), max(abs(20*log10(abs(H(f >= 200))) - 20*log10(abs(Href(f >= 200))))), 20*log10(abs(H(1))));
bq = q16(b); aq = q16(a); show('direct form, 4th order', freqz(bq, aq, f, fs), roots(aq));
sq = P.sos; sq(:, 1:3) = q16(P.sos(:, 1:3)); sq(:, 4:6) = q16(P.sos(:, 4:6));
[bs, as] = sos2tf(sq); show('cascade (board)', freqz(bs, as, f, fs), [roots(sq(1, 4:6)); roots(sq(2, 4:6))]);
Kq = q16(K); Vq = q16(V); [bl, al] = latc2tf(Kq, Vq); show('lattice-ladder', freqz(bl, al, f, fs), roots(al));
fprintf('Python: direct 1.000000 / 51.96 dB; cascade 0.995013 / 0.159 dB; parallel loses the DC zeros (-2.3 dB @20 Hz); lattice -3 dB at 130 Hz\n');
figure; semilogx(f, 20*log10(abs(Href)), 'k', f, 20*log10(abs(freqz(bq, aq, f, fs))), f, 20*log10(abs(freqz(bs, as, f, fs))), '--');
ylim([-80 40]); grid on; legend('exact', 'direct form 16-bit', 'cascade 16-bit'); xlabel('Hz'); ylabel('dB');
title('HPF with 16-bit coefficients'); save_fig('p2_iir_quantisation');
