import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal
src=open("design_check.py").read().split("N = 1 << 14")[0].replace('print(','(lambda *a,**k:None)(')
exec(src)
N=1<<15; imp=np.zeros(N); imp[0]=1
fig,ax=plt.subplots(figsize=(9,4.5))
names=["B5 (6 kHz+)","B4 (3-6k)","B3 (1.5-3k)","B2 (0.75-1.5k)","B1 (<750)"]
for b in range(K+1):
    gg=[0]*(K+1); gg[b]=1; y,_=analyse_synth(imp,gg)
    w,H=signal.freqz(y,1,8192,fs=fs0); ax.semilogx(w[1:],20*np.log10(np.abs(H[1:])+1e-9),lw=1,label=names[b])
from audiograms import AUDIOGRAMS, band_gains_db
gdb=np.array(band_gains_db(AUDIOGRAMS["N3"],0.5)); y,_=analyse_synth(imp,list(10**(gdb/20)))
w,H=signal.freqz(y,1,8192,fs=fs0); ax.semilogx(w[1:],20*np.log10(np.abs(H[1:])),'k',lw=2,label="Composite, N3 half-gain table")
ax.set_xlim(100,20000); ax.set_ylim(-60,35); ax.grid(alpha=.3,which='both'); ax.set_xlabel("Hz"); ax.set_ylabel("dB")
ax.set_title("Mode A: 5-band multirate bank (fs=48 kHz) - individual bands and composite"); ax.legend(fontsize=8,loc='lower right')
plt.tight_layout(); plt.savefig("fig_modeA_bands.png",dpi=120)
