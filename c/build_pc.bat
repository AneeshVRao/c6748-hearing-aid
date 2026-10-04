@echo off
rem Build and run the PC tests of the portable C code (GCC, e.g. WinLibs mingw-w64).
rem   1. own radix-2 FFT backend
rem   2. TI DSPLIB natural-C FFT reference backend (the same fft256() wrapper the board uses)
rem Usage: c\build_pc.bat   (from the repository root or from c\)
setlocal
cd /d "%~dp0"
set DSPLIB=C:\ti\dsplib_c674x_3_4_0_0\packages\ti\dsplib\src
set CFLAGS=-std=c99 -O2 -Wall -Wextra -Wno-unknown-pragmas
set SRC=ha.c hpf.c modeA_bank.c modeB_ola.c fft_own.c goertzel.c coeffs.c pc_test.c
if not exist build mkdir build
if not exist ..\results\phase3 mkdir ..\results\phase3

python ..\python\export.py || exit /b 1

gcc %CFLAGS% %SRC% -o build\pc_test_own.exe -lm || exit /b 1
gcc %CFLAGS% -DUSE_DSPLIB %SRC% fft_dsplib.c ^
    "%DSPLIB%\DSPF_sp_fftSPxSP\c674\DSPF_sp_fftSPxSP_cn.c" ^
    "%DSPLIB%\DSPF_sp_ifftSPxSP\c674\DSPF_sp_ifftSPxSP_cn.c" ^
    -I"%DSPLIB%\DSPF_sp_fftSPxSP\c674" -I"%DSPLIB%\DSPF_sp_ifftSPxSP\c674" ^
    -o build\pc_test_dsplib.exe -lm || exit /b 1

rem lab experiments of the board project, with TI's natural-C DSPLIB references
set LABCN=
for %%f in (fir_gen biquad cfftr2_dit icfftr2_dif cfftr4_dif fftSPxSP ifftSPxSP) do (
    call set LABCN=%%LABCN%% "%DSPLIB%\DSPF_sp_%%f\c674\DSPF_sp_%%f_cn.c" -I"%DSPLIB%\DSPF_sp_%%f\c674"
)
gcc %CFLAGS% -Wno-unused-parameter -DUSE_DSPLIB -I. -I..\ccs\hearing_aid lab_check.c ..\ccs\hearing_aid\lab_modes.c ^
    ha.c hpf.c modeA_bank.c modeB_ola.c fft_own.c fft_dsplib.c goertzel.c coeffs.c %LABCN% ^
    -o build\lab_check.exe -lm || exit /b 1

build\pc_test_own.exe > ..\results\phase3\pc_test_own.txt
set R1=%ERRORLEVEL%
build\pc_test_dsplib.exe > ..\results\phase3\pc_test_dsplib.txt
set R2=%ERRORLEVEL%
build\lab_check.exe > ..\results\phase3\lab_check.txt
set R3=%ERRORLEVEL%
type ..\results\phase3\pc_test_own.txt
type ..\results\phase3\pc_test_dsplib.txt
type ..\results\phase3\lab_check.txt
if not "%R1%%R2%%R3%"=="000" exit /b 1
echo PC tests passed.
