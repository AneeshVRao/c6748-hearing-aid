function X = fft_dit_own(x)
%FFT_DIT_OWN Iterative radix-2 decimation-in-time FFT (bit-reversed input, natural output).
N = numel(x); x = x(:); X = x(bitrevorder(1:N));
sz = 2;
while sz <= N
    half = sz/2;
    for k = 0:half-1
        w = exp(-2i*pi*k/sz);
        for s = 0:sz:N-1
            a = X(s+k+1); b = w*X(s+k+half+1);
            X(s+k+1) = a + b; X(s+k+half+1) = a - b;
        end
    end
    sz = sz*2;
end
end
