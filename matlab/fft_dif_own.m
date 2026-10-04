function X = fft_dif_own(x)
%FFT_DIF_OWN Iterative radix-2 decimation-in-frequency FFT (natural input, output reordered).
N = numel(x); X = x(:); sz = N;
while sz >= 2
    half = sz/2;
    for k = 0:half-1
        w = exp(-2i*pi*k/sz);
        for s = 0:sz:N-1
            a = X(s+k+1); b = X(s+k+half+1);
            X(s+k+1) = a + b; X(s+k+half+1) = (a - b)*w;
        end
    end
    sz = sz/2;
end
X = X(bitrevorder(1:N));
end
