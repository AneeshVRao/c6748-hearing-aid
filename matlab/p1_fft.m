%P1_FFT Block 5: own radix-2 DIT/DIF vs fft, op counts, Goertzel, Chirp-Z zoom. Mirror of python/p1_fft.py.
% UNVERIFIED: MATLAB is not installed on the development PC.
P = hearing_aid_params(); fs = P.fs;
for N = [8 16 64 256 1024]
    x = randn(N,1) + 1i*randn(N,1); X = fft(x);
    fprintf('N=%5d: max error DIT %.1e, DIF %.1e\n', N, max(abs(fft_dit_own(x) - X)), max(abs(fft_dif_own(x) - X)));
end
m2 = @(N) N/2*log2(N) - 3*N/2 + 2;          % radix-2 non-trivial complex multiplies
fprintf('radix-2, N=256: %d non-trivial complex multiplies (Python: radix-2 642, radix-4 492, split radix 456)\n', m2(256));

N = 4608; t = (0:N-1)/fs;                   % multiple of 384: all 11 tones on exact bins (correction C10)
for f = P.test_f
    x = 0.1*sin(2*pi*f*t + 0.3) + 0.05*sin(2*pi*(f + fs/N)*t);
    fprintf('Goertzel %5d Hz: %.6f (expect 0.100000)\n', f, goertzel_amp(x, f, fs));
end

imp = [1; zeros(8191, 1)];
h = mode_a(imp, band_gains_db(P.aud.N3, 0.5, P), P);
f1 = 600; f2 = 900; m = 512;
w = exp(-2i*pi*(f2 - f1)/((m - 1)*fs)); a = exp(2i*pi*f1/fs);
Z = czt(h, m, w, a); fz = f1 + (0:m-1)*(f2 - f1)/(m - 1);
fprintf('CZT 600-900 Hz: %.2f to %.2f dB (Python: 18.08 to 20.06)\n', min(20*log10(abs(Z))), max(20*log10(abs(Z))));
figure; plot(fz, 20*log10(abs(Z))); yline(17.5, 'k:'); grid on; xlabel('Hz'); ylabel('dB');
title('Chirp-Z zoom: Mode A gain around the 750 Hz crossover (N3)'); save_fig('p1_fft_czt_zoom');
