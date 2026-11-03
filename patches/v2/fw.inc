    .syntax unified
    .thumb
_patch_start:

    .equ msg_post, 0x0306b0d8
    .equ msg_test, 0x0306b138
    .equ fw_lock, 0x0306a4a6
    .equ fw_unlock, 0x0306a4fe
    .equ fw_read, 0x0306b404

.macro _t32_b24 target, second
    .set _off, (\target) - (PATCH_BASE + (. - _patch_start) + 4)
    .set _s, (_off >> 24) & 1
    .set _j1, ~(((_off >> 23) & 1) ^ _s) & 1
    .set _j2, ~(((_off >> 22) & 1) ^ _s) & 1
    .short 0xf000 | (_s << 10) | ((_off >> 12) & 0x3ff)
    .short \second | (_j1 << 13) | (_j2 << 11) | ((_off >> 1) & 0x7ff)
.endm
.macro fbl target
    _t32_b24 \target, 0xd000
.endm
.macro fb target
    _t32_b24 \target, 0x9000
.endm
.macro _t32_bcc cond, target
    .set _off, (\target) - (PATCH_BASE + (. - _patch_start) + 4)
    .short 0xf000 | (((_off >> 20) & 1) << 10) | (\cond << 6) | ((_off >> 12) & 0x3f)
    .short 0x8000 | (((_off >> 18) & 1) << 13) | (((_off >> 19) & 1) << 11) | ((_off >> 1) & 0x7ff)
.endm
.macro fbeq target
    _t32_bcc 0, \target
.endm
.macro fbne target
    _t32_bcc 1, \target
.endm
