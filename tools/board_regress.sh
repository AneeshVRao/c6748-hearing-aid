#!/usr/bin/env bash
# Re-run every board check that needs no audio input, headless (CCS 7 DSS), and save the readouts.
# Usage (Git Bash, board connected, CCS IDE not connected to the target):
#   tools/board_regress.sh [out_dir]          default out_dir: results/phase4/board
# Then: python python/board_compare.py internal ... / nr ...   (printed at the end)
set -u
cd "$(dirname "$0")/.."
DSS=/c/ti/ccsv7/ccs_base/scripting/bin/dss.bat
CCXML="${CCXML:-C:/Users/$USERNAME/ti/CCSTargetConfigurations/LCDK_C6748.ccxml}"
OUT="${1:-results/phase4/board}"
TMP="$(cygpath -m "${TMPDIR:-/tmp}")/ha_dss"   # dss.bat splits arguments at spaces: keep dumps on a path without them
mkdir -p "$OUT/speech_nr" "$TMP"

run() {   # run <program> <dss_run.js arguments...>; retries a transient "cable break" up to 3 times
    local prog=$1; shift
    for try in 1 2 3; do
        timeout 2400 "$DSS" tools/dss_run.js "$CCXML" "ccs/build/$prog/$prog.out" "$@" > "$TMP/log.txt" 2>&1
        grep -q "cable break" "$TMP/log.txt" || break
    done
    grep -E " = |^-- |ERROR"  "$TMP/log.txt"
}

st=(); for k in 0 1 2 3; do st+=(g_int[$k].done g_int[$k].max g_int[$k].avg g_int[$k].bg_max g_int[$k].bg_avg); done
gd=(); for k in 0 1; do for t in $(seq 0 10); do gd+=(g_int[$k].gain_db[$t]); done; done
bn=(); for i in $(seq 0 19); do bn+=(g_lab.bench[$i] g_lab.bench_err[$i]); done
rd=(g_samples g_prof.isr_max g_prof.isr_count g_prof.cpu_hz_est g_prof.rstat g_prof.xstat g_ha.overruns)

echo "== internal (tones)";   run internal 20 "${st[@]}" "${gd[@]}" g_ifft_gain \
    "SAVE:g_out:384000:$TMP/g_out.dat" "SAVE:g_stored:96000:$TMP/g_stored.dat" | tee "$OUT/internal_readout.txt"
echo "== internal_o0";        run internal_o0 60 "${st[@]}"                 | tee "$OUT/internal_o0_readout.txt"
echo "== internal_speech 5 dB"; run internal_speech 0 "SET:g_stored_snr_db:5" @20 "${st[@]}" \
    "SAVE:g_out:384000:$TMP/sp_out.dat" "SAVE:g_stored:96000:$TMP/sp_stored.dat" | tee "$OUT/speech_nr/readout.txt"
run internal_speech 3 "SAVE:g_stored:96000:$TMP/sp_clean.dat" > /dev/null
echo "== lab_arith";  run lab_arith 5 g_lab.done $(for i in 0 1 2 3; do echo g_lab.arith_cycles[$i] g_lab.arith_result[$i]; done) | tee "$OUT/lab_arith.txt"
echo "== lab_conv";   run lab_conv 5 g_lab.done $(for i in 0 1 2 3 4 5; do echo g_lab.conv_linear[$i] g_lab.conv_circ6[$i]; done) \
    $(for i in 0 1 2 3; do echo g_lab.conv_circ4[$i]; done) | tee "$OUT/lab_conv.txt"
echo "== lab_dft";    run lab_dft 5 g_lab.done g_lab.dft_cycles[0] g_lab.dft_cycles[1] g_lab.dft_cycles[2] g_lab.dft_err[0] g_lab.dft_err[1] | tee "$OUT/lab_dft.txt"
echo "== lab_bench";  run lab_bench 8 g_lab.done g_lab.icfftr2_gain "${bn[@]}" > "$OUT/lab_bench.txt"
echo "== lab_bench_o0"; run lab_bench_o0 15 g_lab.done $(for i in $(seq 0 19); do echo g_lab.bench[$i]; done) > "$OUT/lab_bench_o0.txt"
echo "== loop_fifo";  run loop_fifo 6 "${rd[@]}" | tee "$OUT/loop_fifo.txt"
echo "== fallback";   run fallback 15 "${rd[@]}" | tee "$OUT/fallback.txt"
echo "== stored";     run stored 15 "${rd[@]}" g_ha.clips | tee "$OUT/stored.txt"
echo "== notch: speech only, 12 s"; run stored_speech 0 @1 "SET:g_req[3]:1" @12 g_ha.nt.n g_ha.hd.f[0] g_prof.xstat | tee "$OUT/notch_stored_speech_only.txt"
echo "== notch: speech + 2500 Hz"; run stored_speech 0 "SET:g_stored_tone_hz:2500" @1 "SET:g_req[3]:1" @0.5 g_ha.nt.n @3 \
    g_ha.nt.n g_ha.hd.f[0] g_ha.hd.f[1] g_prof.xstat g_ha.overruns | tee "$OUT/notch_stored_tone.txt"
rs=("SET:g_prof.isr_max:0" "SET:g_prof.isr_sum:0" "SET:g_prof.isr_count:0" "SET:g_prof.bg_max:0" "SET:g_prof.bg_sum:0" "SET:g_prof.bg_count:0" "SET:g_ha.overruns:0" "SET:g_ha.clips:0")
pr=(g_ha.mode g_prof.isr_max g_prof.isr_sum g_prof.isr_count g_prof.bg_max g_prof.bg_sum g_prof.bg_count g_ha.overruns g_ha.clips g_prof.rstat g_prof.xstat)
echo "== T6 CPU load, live, 60 s per mode"; run live 3 "${rs[@]}" @60 "${pr[@]}" "SET:g_req[0]:1" @2 "${rs[@]}" @60 "${pr[@]}" | tee "$OUT/T6_live.txt"

# split the 4 IO_INTERNAL output runs into one dump each (board_compare.py reads TI data files)
python - "$TMP" "$OUT" <<'EOF'
import sys, pathlib
tmp, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
for src, d, stored in (("g_out.dat", out, "g_stored.dat"), ("sp_out.dat", out / "speech_nr", "sp_stored.dat")):
    lines = (tmp / src).read_text().split("\n")
    base, w = int(lines[0].split()[2], 16), [x for x in lines[1:] if x.strip()]
    for k, n in enumerate(["out_modeA", "out_modeB", "out_modeA_nr", "out_modeB_nr"]):
        (d / f"{n}.dat").write_text(f"1651 1 {base + 384000 * k:x} 0 17700\n" + "\n".join(w[k * 96000:(k + 1) * 96000]) + "\n")
    (d / stored).write_text((tmp / stored).read_text())
(out / "speech_nr" / "sp_clean.dat").write_text((tmp / "sp_clean.dat").read_text())
EOF
echo "== board vs Python"
(cd "$OUT" && python ../../../python/board_compare.py internal out_modeA.dat out_modeB.dat g_stored.dat out_modeA_nr.dat out_modeB_nr.dat) | tee "$OUT/compare_internal.txt"
(cd "$OUT/speech_nr" && python ../../../../python/board_compare.py internal out_modeA.dat out_modeB.dat sp_stored.dat out_modeA_nr.dat out_modeB_nr.dat \
    && python ../../../../python/board_compare.py nr sp_clean.dat sp_stored.dat) | tee "$OUT/speech_nr/compare.txt"
