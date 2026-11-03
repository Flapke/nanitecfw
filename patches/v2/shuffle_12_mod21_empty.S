@ Restore the Shuffle All caption and show the stock localized empty-list label.
@ patch 21 0307a7f4
#include "fw.inc"
    ldr     r1, =0x0300e5de
    movs    r0, #0x7c
    strh    r0, [r1]
    movs    r0, #0x32
    fbl     msg_post
    fb      0x0307ad7a
    .ltorg
