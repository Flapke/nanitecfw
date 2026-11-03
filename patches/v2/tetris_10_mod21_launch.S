@ Read the game payload from the active firmware slot, without overlays.
@ patch 21 0307a750
#include "fw.inc"
#include "tetris_syms.inc"
    .equ    tetris_menu_return, 0x0307a7d0
    push    {r4, r5, r6, lr}
    fbl     fw_lock
    movs    r4, #0
read_chunk:
    ldr     r5, =tetris_text_size
    subs    r5, r5, r4
    cmp     r5, #512
    it      hi
    movhi   r5, #512
    ldr     r0, =0x0300c33c
    ldr     r1, [r0]
    ldr     r0, =tetris_flash_offset
    add     r1, r0
    add     r1, r4
    ldr     r3, =__game_start
    add     r3, r4
    mov     r2, r5
    mov     r0, #0x30000
    fbl     fw_read
    cbnz    r0, read_failed
    add     r4, r5
    ldr     r0, =tetris_text_size
    cmp     r4, r0
    blo     read_chunk
    fbl     fw_unlock
    ldr     r0, =__game_bss
    movw    r1, #tetris_bss_size
    movs    r2, #0
1:  str     r2, [r0], #4
    subs    r1, #4
    bne     1b
    fbl     tetris_enter
    b       return_to_menu
read_failed:
    mov     r6, r0
    fbl     fw_unlock
    mov     r0, r6
return_to_menu:
    pop     {r4, r5, r6, lr}
    movs    r0, #0
    fb      tetris_menu_return
    .ltorg
    .org    0x80
    movs    r0, #0
    add     sp, #36
    pop     {r4, r5, pc}
    .ltorg
