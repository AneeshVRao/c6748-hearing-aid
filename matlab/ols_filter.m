function y = ols_filter(x, h, N)
%OLS_FILTER Overlap-save: keep the last N-M+1 outputs of each circular convolution.
x = x(:); M = numel(h); L = N - M + 1; H = fft(h(:), N);
xp = [zeros(M-1,1); x; zeros(L,1)]; y = [];
for s = 1:L:numel(x)
    v = real(ifft(fft(xp(s:s+N-1), N).*H));
    y = [y; v(M:end)]; %#ok<AGROW>
end
y = y(1:numel(x));
end
