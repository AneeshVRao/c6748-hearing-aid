function h = fs_fir(Hdb, M)
%FS_FIR Type I linear-phase FIR by frequency sampling. Hdb: (M+1)/2 gains in dB at k*fs/M.
Hk = 10.^(Hdb(:).'/20);
a = (M-1)/2; n = (0:M-1).'; k = 1:numel(Hk)-1;
h = (Hk(1) + 2*sum(Hk(2:end).*cos(2*pi*k.*(n-a)/M), 2)).'/M;
end
