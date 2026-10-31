    .syntax unified
    .thumb
    .section .stub, "ax"
    .global tetris_stub
    .type tetris_stub, %function
tetris_stub:
    ldr     r0, =__game_load
    ldr     r1, =__game_start
    ldr     r2, =__game_end
1:  cmp     r1, r2
    itt     lo
    ldrlo   r3, [r0], #4
    strlo   r3, [r1], #4
    blo     1b
    ldr     r1, =__game_bss
    ldr     r2, =__game_bss_end
    movs    r3, #0
2:  cmp     r1, r2
    itt     lo
    strlo   r3, [r1], #4
    blo     2b
    bx      lr
    .ltorg