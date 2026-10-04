%P1_CHAIN Block 6: gain presets and full chains vs targets. Mirror of python/p1_chain.py.
% UNVERIFIED: MATLAB is not installed on the development PC.
P = hearing_aid_params(); fs = P.fs; names = {'N2', 'N3', 'S2'};
fk = (0:64)*fs/129;
for i = 1:3
    for fac = [0.5 0.4]
        aud = P.aud.(names{i}); gd = band_gains_db(aud, fac, P); e = 0;
        for f = P.test_f
            e = max(e, abs(tone_gain(@(x) mode_a(x, gd, P), f, fs) - gain_curve_db(aud, f, fac, P)));
        end
        h = fs_fir(gain_curve_db(aud, fk, fac, P), 129);
        [H, w] = freqz(h, 1, 8192, fs); sel = w >= 250 & w <= 8000;
        eb = max(abs(20*log10(abs(H(sel))) - gain_curve_db(aud, w(sel).', fac, P).'));
        fprintf('%s x%.1f: Mode A max error %.2f dB, Mode B %.2f dB\n', names{i}, fac, e, eb);
    end
end
fprintf('Pack/Python: N2 1.01/0.22, 0.82/0.18; N3 1.53/0.38, 1.20/0.33; S2 6.82/0.49, 5.20/0.45\n');

gd = band_gains_db(P.aud.N3, 0.5, P);
h = fs_fir(gain_curve_db(P.aud.N3, fk, 0.5, P), 129);
chainA = @(x) min(max(mode_a(sosfilt(P.sos, x), gd, P), -P.limit), P.limit);
chainB = @(x) min(max(ola_filter(sosfilt(P.sos, x), h, 128, 256), -P.limit), P.limit);
gA = arrayfun(@(f) tone_gain(chainA, f, fs), P.test_f);
gB = arrayfun(@(f) tone_gain(chainB, f, fs), P.test_f);
tg = gain_curve_db(P.aud.N3, P.test_f, 0.5, P);
disp(table(P.test_f.', tg.', gA.', gB.', 'VariableNames', {'Hz', 'target', 'ModeA', 'ModeB'}))
figure; bar([tg; gA; gB].'); set(gca, 'XTickLabel', string(P.test_f));
legend('target', 'Mode A', 'Mode B', 'Location', 'northwest'); ylabel('gain, dB'); xlabel('Hz');
title('Simulated full-chain gain, N3 half-gain'); save_fig('p1_chain_tone_gains');

imp = [1; zeros(4095, 1)];
[~, d] = max(abs(mode_a(imp, zeros(1, 5), P)));
fprintf('Mode A impulse peak at sample %d (expect 375)\n', d - 1);

[sp, ~] = audioread(fullfile(fileparts(mfilename('fullpath')), '..', 'data', 'speech_48k.wav'));
s = sp/rms(sp)*10^(-40/20);                 % -40 dBFS RMS
figure;
subplot(3,1,1); spectrogram(s, 1024, 768, 1024, fs, 'yaxis'); ylim([0 12]); title('input');
subplot(3,1,2); spectrogram(chainA(s), 1024, 768, 1024, fs, 'yaxis'); ylim([0 12]); title('Mode A');
subplot(3,1,3); spectrogram(chainB(s), 1024, 768, 1024, fs, 'yaxis'); ylim([0 12]); title('Mode B');
save_fig('p1_chain_spectrograms');
