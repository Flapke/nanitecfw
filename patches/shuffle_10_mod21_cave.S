@ Shuffle: mod21 code cave (FUN_03079502..0x03079639, the never-called
@ "UNICODEXDIC" writer): 5-entry icon table, shuffle icon, shuffle_route.
@ patch 21 03079504
#include "fw.inc"
    .equ    media_library, 0x03079b90   @ dispatcher: strh r0,[MusicTypeSelID]; open window 1
    .equ    open_window,   0x03079b9a   @ dispatcher: bl FUN_0306b26a(r0, r1); return 1
    .equ    empty_notice,  0x03079618
icon_table:                             @ Tetris, Shuffle, Playback, Library, Settings
    .word   0x03072dff, shuffle_icon - _patch_start + PATCH_BASE, 0x03072d5f, 0x03072daf, 0x03072dd7
shuffle_icon:                           @ 20x16, 1 bpp, page-major: byte (y>>3)*20+x, bit y&7
    @ ....................
    @ ....................
    @ ................#...
    @ ..####......######..
    @ ..####......#######.
    @ .....##....##....#..
    @ ......##..##....#...
    @ .......####.........
    @ ........##..........
    @ .......####.....#...
    @ ......##..##.....#..
    @ ..#####....########.
    @ ..####......######..
    @ ................#...
    @ ....................
    @ ....................
    .byte   0x00,0x00,0x18,0x18,0x18,0x38,0x60,0xc0,0x80,0x80,0xc0,0x60,0x38,0x18,0x18,0x18,0x5c,0x38,0x10,0x00
    .byte   0x00,0x00,0x18,0x18,0x18,0x18,0x0c,0x06,0x03,0x03,0x06,0x0c,0x18,0x18,0x18,0x18,0x3a,0x1c,0x08,0x00
    .org    0x40                        @ shuffle_route = 0x03079544 (shuffle_11_mod21_route.S)
@ Replaces "ldr r1,=MusicTypeSelID; movs r0,#0" at 0x03079b8c (shuffle_11_mod21_route.S).
@ Item 1: play mode shuffle, then the media browser on All Songs with title
@ 0x82; mod23's shuffle_key (shuffle_20_mod23_key.S) picks and plays a random song.
shuffle_route:
    ldr     r1, =0x0300d482             @ MusicTypeSelID
    ldr     r2, =0x0300e708             @ main-menu cursor
    ldrh    r2, [r2]
    cmp     r2, #0
    fbeq    0x030795b4
    cmp     r2, #1
    bne     1f
    ldr     r3, =0x0300d164             @ settings / library counters
    ldrh    r0, [r3, #0x2e]             @ All Songs count (stock library dispatcher)
    cbz     r0, 2f
    ldr     r0, =0x0300e6e6            @ restore Shuffle All caption after refresh
    movs    r2, #0x82
    strh    r2, [r0]
    movs    r0, #1
    strh    r0, [r1]                    @ MusicTypeSelID = All Songs
    strb    r0, [r3, #0x6f]             @ play order: shuffle
@ end of Shuffle All route
    ldrb    r0, [r3, #0x6d]
    and     r0, r0, #4                  @ keep folder-jump bit
    orr     r0, r0, #3                  @ play mode: shuffle
    strb    r0, [r3, #0x6d]
    ldr     r1, =0x0300d592             @ cleared by mod22 before opening the browser
    movs    r0, #0
    strb    r0, [r1]
    strh    r0, [sp]
    movs    r0, #0x82
    strh    r0, [sp, #2]                @ window 2 {0, title 0x82}
    mov     r1, sp
    movs    r0, #2
    fb      open_window
2:  fb      empty_notice
1:  movs    r0, #0
    fb      media_library
    .ltorg
