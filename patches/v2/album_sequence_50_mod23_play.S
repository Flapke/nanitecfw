@ patch 23 0307af8c
#include "fw.inc"
album_sequence:
    push    {r0-r4, lr}
    ldr     r0, =0x0300c36a
    ldrh    r0, [r0]
    mov     r4, r0
    cmp     r0, #3
    blo     done
    cmp     r0, #5
    bhi     done
    ldr     r1, =0x0300e968
    ldrh    r0, [r1, #0xa]
    cmp     r0, #3
    bhi     done
    ldr     r1, =0x0300e738
    add     r1, r1, r0, lsl #1
    ldrh    r2, [r1]
    cmp     r2, #0x600
    beq     album_context
    cbz     r0, done
    ldrh    r2, [r1, #-2]
    cmp     r2, #0x600
    bne     done
album_context:
    cmp     r4, #3
    bne     sequential
    cmp     r0, #1
    beq     shuffle
sequential:
    ldr     r4, =0x0300c04c
    ldrb    r0, [r4, #0x6d]
    bic     r0, r0, #3
    orr     r0, r0, #2
    strb    r0, [r4, #0x6d]
    movs    r0, #0
    strb    r0, [r4, #0x6f]
    b       notify
shuffle:
    ldr     r4, =0x0300c04c
    ldrb    r0, [r4, #0x6d]
    bic     r0, r0, #3
    orr     r0, r0, #3
    strb    r0, [r4, #0x6d]
    movs    r0, #1
    strb    r0, [r4, #0x6f]
notify:
    movw    r0, #0x113
    fbl     msg_post
    movw    r0, #0x114
    fbl     msg_post
done:
    pop     {r0-r4, lr}
    push.w  {r4-r11, lr}
    fb      0x0307d430
    .ltorg