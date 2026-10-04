import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal
exec(open("design_check.py").read().split("# ---------------- simulate")[0].split('print("=== Filter choices ===")')[0])
NG,BG,NF,BF=21,4.5,31,4.5
g=kaiser_lp(NG,0.125,BG); f=kaiser_lp(NF,0.25,BF); f[np.abs(f)<1e-12]=0
fig,ax=plt.subplots(1,2,figsize=(11,4))
for h,lab in ((g,"G: 21-tap band-split LP (cut fs_k/8)"),(f,"F: 31-tap half-band interpolator")):
    w,H=signal.freqz(h,1,8192,fs=1.0); ax[0].plot(w,20*np.log10(np.abs(H)/abs(H[0])+1e-9),label=lab)
ax[0].set_ylim(-90,5);ax[0].set_xlabel("Frequency (fraction of fs_k)");ax[0].set_ylabel("dB");ax[0].grid(alpha=.3);ax[0].legend(fontsize=8);ax[0].set_title("Prototype filters (reused at every level)")
z=np.roots(g); ax[1].plot(z.real,z.imag,'o',mfc='none'); t=np.linspace(0,2*np.pi,400); ax[1].plot(np.cos(t),np.sin(t),'k',lw=.5)
ax[1].set_aspect('equal'); ax[1].set_title("Zeros of G (linear phase: reciprocal pairs)"); ax[1].grid(alpha=.3)
plt.tight_layout(); plt.savefig("fig_prototype_filters.png",dpi=120)
