function P = hearing_aid_params()
%HEARING_AID_PARAMS Design constants (mirror of python/dsp_ref.py). UNVERIFIED: MATLAB not run.
P.fs = 48000; P.K = 4;
P.G = fir1(20, 0.25, kaiser(21, 4.5));          % 21-tap Kaiser lowpass, cutoff fs/8
P.F = fir1(30, 0.5, kaiser(31, 4.5));           % 31-tap half-band
P.F(abs(P.F) < 1e-12) = 0;
[z, p, k] = butter(4, 100/(P.fs/2), 'high');    % bilinear, pre-warped
P.sos = zp2sos(z, p, k);
P.dG = 10; P.dF = 15;
P.align = [365 165 65 15];                      % T_k - dG, T_0 = 375
P.M = 129; P.L = 128; P.N = 256;
P.limit = 10^(-1/20);
% Bisgaard et al. 2010, Table 2 (N2, N3) and Table 4 (S2)
P.freqs = [250 375 500 750 1000 1500 2000 3000 4000 6000];
P.aud.N2 = [20 20 20 22.5 25 30 35 40 45 50];
P.aud.N3 = [35 35 35 35 40 45 50 55 60 65];
P.aud.S2 = [20 20 20 22.5 25 35 55 75 95 95];
P.cap = 30;
P.test_f = [P.freqs 8000];
end
