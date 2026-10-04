%P1_FIR Block 1: FIR by windowing (Kaiser) vs frequency sampling. Mirror of python/p1_fir.py.
% UNVERIFIED: MATLAB is not installed on the development PC; Python is the verified reference.
P = hearing_aid_params(); fs = P.fs;
att = @(h, fstop) -20*log10(max(abs(freqz(h, 1, linspace(fstop, 0.5, 2000), 1))) / abs(sum(h)));

k = 0:10; fk = k/21;
hd = -300*ones(1, 11); hd(fk < 0.125) = 0;              % ideal lowpass samples (dB)
hdt = hd; hdt(find(fk > 0.125, 1)) = 20*log10(0.4);      % one transition sample
names = {'rectangular', 'Hamming', 'Kaiser b=4.5', 'freq. sampling', 'freq. sampling + transition'};
H = {fir1(20, 0.25, rectwin(21)), fir1(20, 0.25, hamming(21)), P.G, fs_fir(hd, 21), fs_fir(hdt, 21)};
figure; hold on;
for i = 1:5
    a = att(H{i}, 0.20);
    fprintf('%-28s %6.1f dB   (Python: 24.2 38.6 52.5 19.6 41.0)\n', names{i}, a);
    [Hf, f] = freqz(H{i}, 1, 4096, fs);
    plot(f, 20*log10(abs(Hf) + 1e-9), 'DisplayName', sprintf('%s (%.0f dB)', names{i}, a));
end
assert(att(P.G, 0.20) > 52)
xline(0.2*fs, ':', 'HandleVisibility', 'off'); ylim([-90 5]); grid on; legend; xlabel('Hz'); ylabel('dB');
title('21-tap lowpass G: window method vs frequency sampling'); save_fig('p1_fir_G_methods');

% Mode B 129-tap N3 FIR: frequency sampling vs Kaiser-windowed fir2
fk = (0:64)*fs/129;
h_fs = fs_fir(gain_curve_db(P.aud.N3, fk, 0.5, P), 129);
fg = linspace(0, fs/2, 513);
h_w = fir2(128, fg/(fs/2), 10.^(gain_curve_db(P.aud.N3, fg, 0.5, P)/20), kaiser(129, 4.5));
[Hfs, w] = freqz(h_fs, 1, 8192, fs); Hw = freqz(h_w, 1, 8192, fs);
sel = w >= 250 & w <= 8000; tgt = gain_curve_db(P.aud.N3, w(sel).', 0.5, P).';
e_fs = max(abs(20*log10(abs(Hfs(sel))) - tgt)); e_w = max(abs(20*log10(abs(Hw(sel))) - tgt));
fprintf('Mode B N3: frequency sampling %.2f dB, Kaiser window %.2f dB (Python: 0.38 / 1.00)\n', e_fs, e_w);
figure; semilogx(w, 20*log10(abs(Hfs)), w, 20*log10(abs(Hw)), '--', w, gain_curve_db(P.aud.N3, w.', 0.5, P), 'k:');
xlim([100 24000]); ylim([10 35]); grid on; legend('frequency sampling', 'Kaiser window (fir2)', 'target');
xlabel('Hz'); ylabel('dB'); title('Mode B 129-tap FIR'); save_fig('p1_fir_modeB_methods');

figure; subplot(1,2,1); zplane(P.G, 1); title('zeros of G');
subplot(1,2,2); zplane(P.F, 1); title('zeros of F (half-band)'); save_fig('p1_fir_zeros');
