function g = band_gains_db(aud, factor, P)
%BAND_GAINS_DB Mode A band gains, order B5 B4 B3 B2 B1, capped at P.cap.
hl = [aud(end), hl_at(aud, sqrt(3000*6000), P), hl_at(aud, sqrt(1500*3000), P), ...
      hl_at(aud, sqrt(750*1500), P), mean(aud(1:3))];
g = min(factor*hl, P.cap);
end
