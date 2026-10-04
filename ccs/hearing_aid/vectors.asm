; Interrupt vector table for the hearing aid (C674x, EABI/ELF).
; 16 entries of 8 instructions (32 bytes). Placed at 0x11800000; the book's Init_Interrupts_EDMA()
; and Init_Interrupts() set ISTP to that address.
;   RESET -> _c_int00 (C run-time start-up)
;   INT8  -> edma_isr  (EDMA3_CC0_INT1: one 4-sample block received)       default I/O
;   INT12 -> mcasp_isr (McASP0 event 61, mapped by Init_Interrupts())      fallback, per sample
; An ISR entry saves B0, loads the handler address, branches, and restores B0 in the branch delay
; slots; the 'interrupt' C function then saves its own context and returns with B IRP.

        .ref    _c_int00
        .ref    edma_isr
        .ref    mcasp_isr

ISR_ENTRY .macro handler
        STW     .D2T2   B0, *B15--[2]
        MVKL    .S2     handler, B0
        MVKH    .S2     handler, B0
        B       .S2     B0
        LDW     .D2T2   *++B15[2], B0
        NOP     4
        NOP
        NOP
        .endm

STALL   .macro
stall?: B       .S2     stall?          ; unexpected interrupt: stay here (visible in the debugger)
        NOP     5
        NOP
        NOP
        NOP
        NOP
        NOP
        NOP
        .endm

        .sect   "vectors"
        .nocmp                          ; no 16-bit compact instructions: keep 32-byte entries
        .align  1024
RESET:
        MVKL    .S2     _c_int00, B0
        MVKH    .S2     _c_int00, B0
        B       .S2     B0
        NOP     5
        NOP
        NOP
        NOP
        NOP
NMI:    STALL
RSVD2:  STALL
RSVD3:  STALL
INT4:   STALL
INT5:   STALL
INT6:   STALL
INT7:   STALL
INT8:   ISR_ENTRY edma_isr
INT9:   STALL
INT10:  STALL
INT11:  STALL
INT12:  ISR_ENTRY mcasp_isr
INT13:  STALL
INT14:  STALL
INT15:  STALL
