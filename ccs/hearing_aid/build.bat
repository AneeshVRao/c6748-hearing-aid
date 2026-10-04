@echo off
rem Command-line build of the hearing-aid project with TI CGT 8.1.3 and C674x DSPLIB 3.4.0.0.
rem Builds every configuration into ccs\build\<name>\<name>.out and stops at the first failure.
rem Usage (from anywhere):  ccs\hearing_aid\build.bat            all configurations
rem                         ccs\hearing_aid\build.bat live       one configuration (names below)
rem Needs: python tools\fetch_board_files.py   (third-party board files in third_party\rt-dsp)
setlocal enabledelayedexpansion
cd /d "%~dp0"
set CGT=C:\ti\ccsv7\tools\compiler\ti-cgt-c6000_8.1.3
set DSPLIB=C:\ti\dsplib_c674x_3_4_0_0\packages
set ROOT=%~dp0..\..
set TP=%ROOT%\third_party\rt-dsp
if not exist "%TP%\LCDK6748_Support_DSP.c" (
    echo Board files missing. Run: python tools\fetch_board_files.py
    exit /b 1
)
set INC=-I"%CGT%\include" -I"%ROOT%\c" -I. -I"%TP%" -I"%DSPLIB%"
set CFLAGS=-mv6740 --abi=eabi -g --display_error_number --diag_warning=225 --diag_suppress=880 -DUSE_DSPLIB
set SRC=main.c board_io.c lab_modes.c vectors.asm "%TP%\LCDK6748_Support_DSP.c" ^
 "%ROOT%\c\ha.c" "%ROOT%\c\hpf.c" "%ROOT%\c\modeA_bank.c" "%ROOT%\c\modeB_ola.c" ^
 "%ROOT%\c\fft_own.c" "%ROOT%\c\fft_dsplib.c" "%ROOT%\c\goertzel.c" "%ROOT%\c\coeffs.c"

rem name          defines                                   optimisation
set CFG_loop_fallback=-DIO_MODE=0 -DIO_FIFO=0 -DPASSTHROUGH=1 -O3
set CFG_loop_fifo=-DIO_MODE=0 -DIO_FIFO=1 -DPASSTHROUGH=1     -O3
set CFG_live=-DIO_MODE=0 -DIO_FIFO=1                         -O3
set CFG_stored=-DIO_MODE=1 -DIO_FIFO=1                       -O3
set CFG_internal=-DIO_MODE=2                                 -O3
set CFG_fallback=-DIO_MODE=0 -DIO_FIFO=0                     -O3
set CFG_lab_arith=-DLAB_MODE=1                               -O3
set CFG_lab_conv=-DLAB_MODE=2                                -O3
set CFG_lab_dft=-DLAB_MODE=3                                 -O3
set CFG_lab_bench=-DLAB_MODE=4                               -O3
set CFG_lab_bench_o0=-DLAB_MODE=4                            -O0
set CFG_internal_o0=-DIO_MODE=2                              -O0

if not "%~1"=="" ( call :build %1 & exit /b !errorlevel! )
for %%n in (loop_fallback loop_fifo live stored internal fallback lab_arith lab_conv lab_dft lab_bench lab_bench_o0 internal_o0) do (
    call :build %%n || exit /b 1
)
echo.
echo All configurations built.
exit /b 0

:build
set NAME=%1
set OUT=%ROOT%\ccs\build\%NAME%
if not exist "%OUT%" mkdir "%OUT%"
echo === %NAME%: !CFG_%NAME%!
"%CGT%\bin\cl6x" %CFLAGS% !CFG_%NAME%! %INC% --obj_directory="%OUT%" --asm_directory="%OUT%" ^
    %SRC% -z -m"%OUT%\%NAME%.map" -o"%OUT%\%NAME%.out" -i"%CGT%\lib" -i"%DSPLIB%\ti\dsplib\lib" ^
    --stack_size=0x4000 --heap_size=0x1000 --rom_model --reread_libs --warn_sections ^
    -l dsplib.ae674 -l libc.a hearing_aid.cmd > "%OUT%\build.log" 2>&1
set RC=%errorlevel%
findstr /i /c:"warning" /c:"error" "%OUT%\build.log"
if not "%RC%"=="0" ( echo FAILED: see %OUT%\build.log & exit /b 1 )
echo     OK: %OUT%\%NAME%.out
exit /b 0
