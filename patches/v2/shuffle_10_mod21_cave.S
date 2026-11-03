@ V2 module-21 unused file-writer helper; code/data table and route.
@ patch 21 0307a6e0
#include "fw.inc"
    .equ    media_library, 0x0307ad6c
    .equ    open_window,   0x0307ad76
    .equ    empty_notice,  0x0307a7f4
    .equ    tetris_launch, 0x0307a750
shuffle_route:
    ldr     r1, =0x0300c36a
    ldr     r2, =0x0300e600
    ldrh    r2, [r2]
    cmp     r2, #0
    fbeq    tetris_launch
    cmp     r2, #1
    bne     1f
    ldr     r3, =0x0300c04c
    ldrh    r0, [r3, #0x2e]
    cbz     r0, 2f
    ldr     r0, =0x0300e5de
    movs    r2, #0x82
    strh    r2, [r0]
    movs    r0, #1
    strh    r0, [r1]
    strb    r0, [r3, #0x6f]
    ldrb    r0, [r3, #0x6d]
    and     r0, r0, #4
    orr     r0, r0, #3
    strb    r0, [r3, #0x6d]
    movs    r0, #0
    strh    r0, [sp]
    movs    r0, #0x82
    strh    r0, [sp, #2]
    mov     r1, sp
    movs    r0, #2
    fb      open_window
2:  fb      empty_notice
1:  movs    r0, #0
    fb      media_library
    .ltorg
