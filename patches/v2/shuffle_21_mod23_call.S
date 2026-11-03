@ Route V2 browser key reads through the title-gated Shuffle All hook.
@ patch 23 0307cad6
#include "fw.inc"
    .equ    shuffle_key, 0x0307b180
    fbl     shuffle_key
