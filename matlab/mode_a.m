function y = mode_a(x, gdb, P)
%MODE_A 5-band multirate octave filter bank (vectorised). gdb order B5..B1.
g = 10.^(gdb/20); x = x(:); xk = x; bands = cell(1, P.K);
for k = 1:P.K
    gx = filter(P.G, 1, xk);
    bands{k} = [zeros(P.dG,1); xk(1:end-P.dG)] - gx;    % complementary high band
    xk = gx(1:2:end);                                 % decimate by 2
end
y = g(P.K+1)*xk;
for k = P.K:-1:1
    up = zeros(numel(bands{k}), 1); up(1:2:end) = y;  % up-sample by 2
    yi = 2*filter(P.F, 1, up);
    b = bands{k}; d = P.align(k);
    y = g(k)*[zeros(d,1); b(1:end-d)] + yi;
end
end
