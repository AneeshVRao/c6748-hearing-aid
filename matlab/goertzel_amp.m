function a = goertzel_amp(x, f, fs)
%GOERTZEL_AMP Tone amplitude at f by the Goertzel recursion. f*N/fs must be an integer.
N = numel(x); k = f*N/fs; assert(k == round(k), 'tone not on a bin');
c = 2*cos(2*pi*k/N); s1 = 0; s2 = 0;
for n = 1:N
    s0 = x(n) + c*s1 - s2; s2 = s1; s1 = s0;
end
a = 2*sqrt(s1^2 + s2^2 - c*s1*s2)/N;
end
