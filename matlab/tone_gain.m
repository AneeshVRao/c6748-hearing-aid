function [g, spur] = tone_gain(proc, ft, fs)
%TONE_GAIN Steady-state gain (dB) and residual spurs (dBc) of proc() for a 1 s, 0.01-amplitude tone.
t = (0:fs-1).'/fs; x = 0.01*sin(2*pi*ft*t); y = proc(x);
seg = y(8001:8000+38400); ref = x(1:38400); w = hann(38400);   % symmetric, as numpy.hanning
Y = fft(seg.*w); X = fft(ref.*w); Y = Y(1:19201); X = X(1:19201);
i0 = round(ft*38400/fs) + 1; idx = i0-3:i0+3;
sp = sum(abs(Y(idx)).^2); xp = sum(abs(X(idx)).^2);
g = 10*log10(sp/xp); spur = 10*log10((sum(abs(Y).^2) - sp)/sp);
end
