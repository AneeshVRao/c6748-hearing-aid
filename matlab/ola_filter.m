function y = ola_filter(x, h, L, N)
%OLA_FILTER Overlap-add fast convolution, block by block. Output length = input length.
assert(L + numel(h) - 1 <= N, 'N too small: time aliasing');
x = x(:); H = fft(h(:), N); nb = ceil(numel(x)/L);
xp = [x; zeros(nb*L - numel(x), 1)]; y = zeros(nb*L + N, 1);
for b = 0:nb-1
    seg = real(ifft(fft(xp(b*L+1:(b+1)*L), N).*H));
    y(b*L+1:b*L+N) = y(b*L+1:b*L+N) + seg;
end
y = y(1:numel(x));
end
