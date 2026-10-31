MEMORY
{
    STAGE (rx) : ORIGIN = 0x0308b674, LENGTH = 0x10000
    RAM (rwx) : ORIGIN = 0x0309b694, LENGTH = 0x0309ff80 - 0x0309b694
}
ENTRY(tetris_stub)
SECTIONS
{
    .stub : { KEEP(*(.stub)) } > STAGE
    .text : ALIGN(4)
    {
        __game_start = .;
        *(.text*)
        KEEP(*(.rodata.tengine_license))
        *(.rodata*)
        *(.data*)
        . = ALIGN(4);
        __game_end = .;
    } > RAM AT > STAGE
    __game_load = LOADADDR(.text);
    .bss (NOLOAD) : ALIGN(4)
    {
        __game_bss = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        __game_bss_end = .;
    } > RAM
    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.attributes) *(.comment) *(.note*) }
}
ASSERT(__game_bss_end <= 0x0309ff80, "Tetris exceeds free RAM")