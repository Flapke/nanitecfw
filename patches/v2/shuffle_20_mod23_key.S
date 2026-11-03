@ Select a random All Songs row only for the Shuffle All sentinel title.
@ The M3U title (0x5e) and every other browser key pass through unchanged.
@ patch 23 0307b180
#include "fw.inc"
    .equ    get_key, 0x030632da
shuffle_key:
    push    {r4, lr}
    fbl     get_key
    ldr     r1, =0x03004b12
    ldrh    r2, [r1]
    cmp     r2, #0x82
    bne     1f
    movs    r2, #0x5a
    strh    r2, [r1]
    ldr     r4, =0x0300e968
    ldrh    r1, [r4]
    cbz     r1, 1f
    ldr     r0, =0xe000e018
    ldr     r0, [r0]
    udiv    r2, r0, r1
    mls     r0, r2, r1, r0
    strh    r0, [r4, #0x16]
    ldr     r0, =0x40000040
1:  pop     {r4, pc}
    .ltorg
