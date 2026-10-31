@ Read only the game payload from the active firmware slot, without overlays.
@ patch 21 030795b4
#include "fw.inc"
#include "tetris_syms.inc"
    .equ    tetris_menu_return, 0x03079610
tetris_launch:
    push    {r4, lr}
    fbl     0x0306a40e                  @ serialize storage access like the module loader
    ldr     r0, =0x0300d454
    ldr     r1, [r0]
    ldr     r0, =tetris_flash_offset
    add     r1, r0
    ldr     r2, =tetris_text_size
    ldr     r3, =__game_start
    mov     r0, #0x30000
    fbl     0x0306b36c
    mov     r4, r0
    fbl     0x0306a466
    mov     r0, r4
    cbnz    r0, failed
    ldr     r0, =__game_bss
    movw    r1, #tetris_bss_size
    movs    r2, #0
1:  str     r2, [r0], #4
    subs    r1, #4
    bne     1b
    fbl     tetris_enter
failed:
    pop     {r4, lr}
    movs    r0, #0
    fb      tetris_menu_return
    .ltorg
    .org    0x5c
    tetris_menu_return_impl:
    movs    r0, #0
    add     sp, #36
    pop     {r4, r5, pc}
    .ltorg