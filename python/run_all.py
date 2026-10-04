"""Run every Python check and experiment; exit non-zero if any fails.  python python/run_all.py"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
# p1_multirate writes data/speech_48k.wav, which p1_ola and p1_chain read
scripts = ["dsp_ref.py", "p1_fir.py", "p1_iir.py", "p1_multirate.py", "p1_ola.py", "p1_fft.py", "p1_chain.py"]
scripts += sorted(p.name for p in HERE.glob("p[2-9]_*.py"))
failed = []
for s in scripts:
    t = time.time()
    r = subprocess.run([sys.executable, s], cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    ok = r.returncode == 0
    print(f"{'PASS' if ok else 'FAIL'}  {s:22s} {time.time() - t:6.1f} s")
    if not ok:
        failed.append(s)
        print(r.stdout[-2000:], r.stderr[-2000:])
print(f"\n{len(scripts) - len(failed)}/{len(scripts)} passed")
sys.exit(1 if failed else 0)
