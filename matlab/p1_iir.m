%P1_IIR Block 2: HPF by bilinear vs matched-z; impulse invariance on a low-pass. Mirror of python/p1_iir.py.
% UNVERIFIED: MATLAB is not installed on the development PC.
P = hearing_aid_params(); fs = P.fs; T = 1/fs; fc = 100;
f = logspace(1, log10(23999), 2000);
[bs, as] = sos2tf(P.sos);
Hb = freqz(bs, as, f, fs);
H100 = freqz(bs, as, [100 200], fs);                       % MATLAB cannot index a call result directly
fprintf('Bilinear HPF gain at 100 Hz: %.3f dB (expect -3.01)\n', 20*log10(abs(H100(1))));
disp(P.sos)

[zs, ps, ks] = butter(4, 2*pi*fc, 'high', 's');           % analog prototype
bm = real(poly(exp(zs*T))); am = real(poly(exp(ps*T)));   % matched-z: z = e^(sT)
s20 = 1i*2*pi*20000; z20 = exp(s20*T);
bm = bm*abs(ks*prod(s20 - zs)/prod(s20 - ps))/abs(polyval(bm, z20)/polyval(am, z20));
Hm = freqz(bm, am, f, fs);
fprintf('max |matched-z - bilinear| above 50 Hz: %.3f dB (Python: 0.000)\n', ...
    max(abs(20*log10(abs(Hm(f > 50))) - 20*log10(abs(Hb(f > 50))))));
Kt = tan(pi*fc/fs);
fprintf('1st order: bilinear pole %.6f, matched-z pole %.6f (both 0.986995)\n', (1-Kt)/(1+Kt), exp(-2*pi*fc/fs));

[bh, ah] = butter(4, 2*pi*fc, 'high', 's');
figure; semilogx(f, 20*log10(abs(freqs(bh, ah, 2*pi*f))), 'k:', f, 20*log10(abs(Hb)), f, 20*log10(abs(Hm)), '--');
ylim([-80 3]); grid on; legend('analog', 'bilinear (board)', 'matched-z'); xlabel('Hz'); ylabel('dB');
title('4th-order Butterworth HPF 100 Hz'); save_fig('p1_iir_hpf_methods');

% Impulse invariance needs a strictly proper H(s). The analog HPF has equal numerator and
% denominator degree (a direct term: h(t) contains a delta), so it cannot be used for the HPF.
fprintf('Analog HPF: deg(num) = deg(den) = %d -> impulse invariance undefined\n', numel(ah) - 1);
figure; fl = [100 8000];
for i = 1:2
    [bl, al] = butter(4, 2*pi*fl(i), 's');
    [bi, ai] = impinvar(bl, al, fs);
    [bb, ab] = butter(4, fl(i)/(fs/2));
    Hi = freqz(bi, ai, f, fs); Hi = Hi/abs(Hi(1));
    Ha = freqs(bl, al, 2*pi*f);
    subplot(1,2,i);
    semilogx(f, 20*log10(abs(Ha)), f, 20*log10(abs(Hi)), f, 20*log10(abs(freqz(bb, ab, f, fs)) + 1e-12));
    ylim([-120 5]); grid on; legend('analog', 'impulse invariance', 'bilinear'); title(sprintf('LP %d Hz', fl(i)));
    fprintf('LP %d Hz at 24 kHz: analog %.1f dB, impulse invariance %.1f dB (Python 8 kHz: -38.2 / -35.9)\n', ...
        fl(i), 20*log10(abs(Ha(end))), 20*log10(abs(Hi(end))));
end
save_fig('p1_iir_impinv_lowpass');
