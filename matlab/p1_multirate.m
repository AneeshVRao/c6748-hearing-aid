%P1_MULTIRATE Block 3: decimation/interpolation per level and rational I/D 160/147. Mirror of python/p1_multirate.py.
% UNVERIFIED: MATLAB is not installed on the development PC.
P = hearing_aid_params(); n = 2^14;
for k = 0:P.K-1
    fk = P.fs/2^k; fin = round(0.35*n)/n*fk; fal = fk/2 - fin;   % 0.35 fs_k folds onto 0.15 fs_k
    x = sin(2*pi*fin*(0:n-1)/fk);
    gx = filter(P.G, 1, x);
    ref = level_db(x, fin, fk);
    fprintf('level %d (%5d Hz): alias without G %6.1f dB, with G %6.1f dB (Python: 0.0 / -73.4)\n', k, fk, ...
        level_db(x(1:2:end), fal, fk/2) - ref, level_db(gx(1:2:end), fal, fk/2) - ref);
end
for k = 0:P.K-1
    fk = P.fs/2^k; flo = round(0.15*n/2)/(n/2)*fk/2; fim = fk/2 - flo;
    x = sin(2*pi*flo*(0:n/2-1)/(fk/2));
    up = zeros(1, n); up(1:2:end) = x;
    y = 2*filter(P.F, 1, up);
    fprintf('level %d: image with F %6.1f dB (Python: -74.4)\n', k, level_db(y, fim, fk) - level_db(y, flo, fk));
end

t = (0:44099)/44100;
y = resample(0.5*sin(2*pi*1000*t), 160, 147);
seg = y(2401:2400+43200);
fprintf('160/147: length %d (expect 48000), amplitude %.4f (expect ~0.5)\n', numel(y), sqrt(2)*std(seg));
[sp, fsin] = audioread(fullfile(fileparts(mfilename('fullpath')), '..', 'data', 'speech_44k1.wav'));
sp48 = resample(sp, 160, 147);
[p1, f1] = pwelch(sp, 4096, [], [], fsin); [p2, f2] = pwelch(sp48, 4096, [], [], 48000);
figure; semilogx(f1, 10*log10(p1), f2, 10*log10(p2)); grid on;
legend('original 44.1 kHz', 'resampled 48 kHz (160/147)'); xlabel('Hz'); ylabel('dB/Hz');
save_fig('p1_multirate_resample');

function L = level_db(x, f, fs)
% Level of the component at f: Hann-windowed FFT normalised by length, +-2 bins.
X = abs(fft(x(:).*hann(numel(x))))/numel(x);
i = round(f*numel(x)/fs) + 1;
L = 20*log10(sqrt(sum(X(i-2:i+2).^2)) + 1e-15);
end
