#!/usr/bin/env bash
set -euo pipefail
out=$1
firmware=${2:-NANOV170.IMG}
diagnostic=${3:-0}
mkdir -p "$out/tetris"
flags=(-mthumb -mcpu=cortex-m3 -Os -std=gnu11 -ffreestanding -fno-builtin
       -ffunction-sections -fdata-sections -fno-strict-aliasing
       -Wall -Wextra -Wno-unused-parameter -Isrc -Ithird_party/tengine)
case "$diagnostic" in
    1) flags+=(-DTETRIS_DISPLAY_DIAGNOSTIC) ;;
    2) flags+=(-DTETRIS_ENGINE_DIAGNOSTIC) ;;
    3) flags+=(-DTETRIS_COMMIT_DIAGNOSTIC) ;;
    4) flags+=(-DTETRIS_LIVE_DIAGNOSTIC) ;;
    5) flags+=(-DTETRIS_BAG_DIAGNOSTIC) ;;
    6) flags+=(-DTETRIS_RANDOM_DIAGNOSTIC) ;;
    7) flags+=(-DTETRIS_PREVIEW_DIAGNOSTIC) ;;
    8) flags+=(-DTETRIS_PREVIEW_DIAGNOSTIC -DTETRIS_RAW_DIAGNOSTIC) ;;
    9) flags+=(-DTETRIS_TYPE_DUMP_DIAGNOSTIC -DTETRIS_TYPE_DEBUG) ;;
    10) flags+=(-DTETRIS_GAME_TRACE) ;;
esac
objects=()
for source in src/tetris/game.c src/tetris/start.S src/libc.c third_party/tengine/tengine.c; do
    object="$out/tetris/$(basename "${source%.*}").o"
    arm-none-eabi-gcc "${flags[@]}" -c "$source" -o "$object"
    objects+=("$object")
done
arm-none-eabi-objcopy -I binary -O elf32-littlearm -B arm \
    --rename-section .data=.rodata.tengine_license,alloc,load,readonly,data,contents \
    third_party/tengine/LICENSE "$out/tetris/license.o"
objects+=("$out/tetris/license.o")
arm-none-eabi-gcc -mthumb -mcpu=cortex-m3 -nostdlib -T src/tetris/link.ld \
    -Wl,--gc-sections,-Map="$out/tetris.map",--undefined=tetris_enter \
    -Wl,--no-warn-rwx-segments -o "$out/tetris.elf" "${objects[@]}" -lgcc
arm-none-eabi-objcopy -O binary "$out/tetris.elf" "$out/tetris.bin"
arm-none-eabi-nm -g "$out/tetris.elf" > "$out/tetris.nm"
python3 - "$out" "$firmware" <<'PY'
import sys
from pathlib import Path
from tools.rknano_fw import load
output = Path(sys.argv[1])
symbols = {name: int(value, 16) for value, kind, name in
           (line.split() for line in (output / 'tetris.nm').read_text().splitlines())}
data = (output / 'tetris.bin').read_bytes()
(output / 'tetris_blob.patch').write_text(
    '40:%08x:%s\n' % (symbols['tetris_stub'], data.hex()))
symbols['tetris_text_size'] = symbols['__game_end'] - symbols['__game_start']
symbols['tetris_bss_size'] = symbols['__game_bss_end'] - symbols['__game_bss']
symbols['tetris_flash_offset'] = load(sys.argv[2]).region(40, symbols['__game_load'])[0] - 0x200
(output / 'tetris_syms.inc').write_text(
    ''.join('    .equ %s, 0x%08x\n' % (name, symbols[name]) for name in
            ['tetris_enter', '__game_start', '__game_bss', 'tetris_text_size',
             'tetris_bss_size', 'tetris_flash_offset']))
print('Tetris: %d bytes staged, %d bytes of RAM used' %
      (len(data), symbols['__game_bss_end'] - symbols['__game_start']))
PY