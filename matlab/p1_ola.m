%P1_OLA Block 4: overlap-add vs direct convolution, overlap-save, time aliasing. Mirror of python/p1_ola.py.
% UNVERIFIED: MATLAB is not installed on the development PC.
P = hearing_aid_params();
[sp, fs] = audioread(fullfile(fileparts(mfilename('fullpath')), '..', 'data', 'speech_48k.wav'));
x = sp(1:3*fs);
fk = (0:64)*fs/129;
h = fs_fir(gain_curve_db(P.aud.N3, fk, 0.5, P), 129);
ref = filter(h, 1, x);
fprintf('max |OLA - direct| = %.2e, max |OLS - direct| = %.2e (Python ~1e-14)\n', ...
    max(abs(ola_filter(x, h, 128, 256) - ref)), max(abs(ols_filter(x, h, 256) - ref)));
fprintf('fftfilt (MATLAB built-in OLA) vs direct: %.2e\n', max(abs(fftfilt(h, x, 256) - ref)));
for N = [224 192 160]                       % N < L+M-1 = 256: circular wrap-around corrupts the output
    H = fft(h(:), N); y = zeros(numel(x) + N, 1);
    for s = 1:128:numel(x)-127
        y(s:s+N-1) = y(s:s+N-1) + real(ifft(fft(x(s:s+127), N).*H));
    end
    fprintf('N = %d: max error %.2e (Python: 2.87e-01, 9.51e+00, 1.89e+01)\n', N, max(abs(y(1:numel(x)) - ref)));
end
