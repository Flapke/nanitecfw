@ Shuffle All empty-list notice, in the free tail after the Tetris launcher.
@ The existing localized 0x7c label is "List Empty".
@ patch 21 03079618
#include "fw.inc"

shuffle_empty_notice:
    ldr     r1, =0x0300e6e6
    movs    r0, #0x7c
    strh    r0, [r1]
    movs    r0, #0x32
    fbl     msg_post
    fb      0x03079b9e
    .ltorg
