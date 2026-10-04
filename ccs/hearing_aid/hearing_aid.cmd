/* Linker command file: C6748 DSP, EABI ELF. Memory map from the C6748 datasheet (S8 Table 3-4).
 * Code and real-time data in L2 RAM; the stored test signal and IO_INTERNAL outputs in DDR2.
 * Stack 16 KB and heap 4 KB are set on the linker command line (build.bat, projectspec);
 * the book's link file used a 1 KB stack, too small for this program. */

MEMORY
{
    VECTORS: o = 0x11800000  l = 0x00000400   /* L2 RAM (global address); ISTP points here */
    L2RAM:   o = 0x11800400  l = 0x0003FC00   /* rest of the 256 KB L2 RAM */
    SHRAM:   o = 0x80000000  l = 0x00020000   /* 128 KB shared RAM */
    DDR2:    o = 0xC0000000  l = 0x08000000   /* 128 MB on the LCDK */
}

SECTIONS
{
    "vectors"  > VECTORS
    .text      > L2RAM
    .const     > L2RAM
    .switch    > L2RAM
    .cinit     > L2RAM
    .init_array > L2RAM
    GROUP (NEAR_DP)            /* DP-relative data must stay together near the static base */
    {
        .neardata
        .rodata
        .bss
    } > L2RAM
    .far       > L2RAM
    .fardata   > L2RAM
    .stack     > L2RAM
    .sysmem    > L2RAM
    .cio       > L2RAM
    .ddr       > DDR2      /* uninitialised: stored input (Load Memory) and IO_INTERNAL outputs */
}
