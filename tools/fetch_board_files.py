"""Fetch the third-party LCDK board-support files into third_party/rt-dsp/ (git-ignored).

The files come from Welch, Wright & Morrow, "Real-Time Digital Signal Processing from MATLAB to C
with the TMS320C6x DSPs", 3rd ed. (rt-dsp.com). Their licence for redistribution is unclear, so this
public repository does not contain them. Usage:  python tools/fetch_board_files.py
Offline: if research/papers/ holds the same files (the research pack), they are copied from there.
"""
import io
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "third_party" / "rt-dsp"
ZIP_URL = "https://rt-dsp.com/3rd_ed/zips/code_2017_02_05.zip"
SUPPORT_URL = "https://rt-dsp.com/3rd_ed/LCDK6748_Support_DSP.c"
FROM_ZIP = ["AIC3106.h", "DSP_Config.h", "LCDK_Support_DSP.h", "OMAPL138_defines.h", "tistdtypes.h"]
LOCAL = ROOT / "research" / "papers"


def get(url):
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    local_dir = LOCAL / "S19_code_2017_02_05" / "code" / "common_code" / "LCDK"
    if local_dir.is_dir() and (LOCAL / "LCDK6748_Support_DSP.c").is_file():
        for f in FROM_ZIP:
            shutil.copy2(local_dir / f, OUT / f)
        shutil.copy2(LOCAL / "LCDK6748_Support_DSP.c", OUT / "LCDK6748_Support_DSP.c")
        print(f"copied from {LOCAL}")
    else:
        z = zipfile.ZipFile(io.BytesIO(get(ZIP_URL)))
        names = {Path(n).name: n for n in z.namelist() if "common_code/LCDK/" in n.replace("\\", "/")}
        for f in FROM_ZIP:
            (OUT / f).write_bytes(z.read(names[f]))
        (OUT / "LCDK6748_Support_DSP.c").write_bytes(get(SUPPORT_URL))
    missing = [f for f in FROM_ZIP + ["LCDK6748_Support_DSP.c"] if not (OUT / f).is_file()]
    if missing:
        sys.exit(f"missing: {missing}")
    # the replacement file must contain Config_LCDK6748(); the zip's original LCDK_Support_DSP.c does not
    assert b"Config_LCDK6748" in (OUT / "LCDK6748_Support_DSP.c").read_bytes()
    print(f"OK: {len(FROM_ZIP) + 1} files in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
