# FiiO Echo Nano custom firmware

| **Tetris** is the leftmost main-menu entry, with tetromino gameplay, next-piece preview, score, line count, landing ghost and restart | 6.0.55: nav1 rotates right, nav2 hard-drops, Confirm rotates left; field raised 1 pixel |
| **Shuffle All** replaces File Browser: shuffle play over the whole card in one press, whatever Folder Jumping Song is set to | 6.0.55: empty library displays “List Empty” and returns without opening the browser |
| **Album playback** starts songs inside albums in Sequential Play; Artist album-level Play All uses Shuffle; other lists retain their mode and Folder Jumping Song | 6.0.55: distinguishes artist album-list from song-list level |
features and make the library refresh much faster. This repository contains only
### Customized menus (6.0.55)
firmware: you download the official image yourself and build the custom image
python3 tests/tetris_firmware_test.py out/nanitecfw-6.0.55-20261209/NANOV170.IMG
chosen date in their output folder. For example, `gmake DATE=20261209` on macOS
writes `out/nanitecfw-6.0.55-20261209/NANOV170.IMG`. Add `TETRIS_DIAGNOSTIC=10`
  example, use `out/nanitecfw-6.0.55-20261209/NANOV170.IMG`. Copy the image,
For the customized image built above with `DATE=20261209`, use
`gmake recovery DATE=20261210` on macOS instead of the default recovery date.
  32:0307cf14:u"6.0.55"                # module 32, UTF-16 string + NUL

## Features

| Feature | Status |
|---|---|
| **Faster library refresh**: about 5× faster on a FLAC-heavy card (148 s → 28 s for 2,000 songs) | tested on device |
| **Tetris** is the leftmost main-menu entry, with tetromino gameplay, next-piece preview, score, line count, landing ghost and restart | 6.0.54: nav1 rotates right, nav2 hard-drops, Confirm rotates left; field raised 1 pixel |
| **Shuffle All** replaces File Browser: shuffle play over the whole card in one press, whatever Folder Jumping Song is set to | 6.0.54: empty library displays “List Empty” and returns without opening the browser |
| **Album playback** switches to Sequential Play when starting an album or a song within one; Artist Play All enables Shuffle; other lists retain their mode and Folder Jumping Song | 6.0.54: mode corrected from device menu order |
| **Unsupported tracks** are skipped without a popup; playback stops after 10 failures in a row | tested on device |
| **Artists** uses the stock album-artist grouping; the separate track-artist list is hidden | 6.0.7: menu layout checked; not yet tested on device |
| `CFWLOG.TXT` in the card's root after each refresh: timings and counters | tested on device |
| **Power saving**: lower CPU clocks during playback (decode core 144-288 MHz instead of 350-450 MHz for MP3, AAC, WMA, WAV, OGG, FLAC and ALAC), the CPU sleeps between events with the screen on, and the scroll wheel is polled every 1 ms instead of every 0.4 ms | new in 6.0.5; battery gain not measured |

About shows the custom version (6.0.x) instead of the stock version.

### Customized menus (6.0.54)

The main menu is **Tetris, Shuffle All, Music Playback, Media Library, System Settings**.
Music Playback remains the startup selection.
File Browser is removed here; **Folder Navigation** remains available inside
Media Library. Music Settings is also removed from the main menu; double-click
Confirm during playback to open the same settings screen.

The Media Library menu is **Favorites, Artists, Folder Navigation, Media Library
Refresh**, in that order. Artists groups by album artist, then album, then song.
The separate All Songs, Albums, Genres, Recent Albums, Now Playing and track-artist
entries are hidden. Shuffle All still uses the full All Songs index internally.
The extra Recent Albums and track-artist indexes are still generated during refresh.

After flashing, run **Media Library → Media Library Refresh** once.

### Tetris (experimental)

The normal build is playable. `TETRIS_DIAGNOSTIC=10` keeps normal gameplay and
shows live/next type values above the field. Mode 9 dumps 21 indexed raw values:
0-3 current type/orientation/x/y, 4-7 ghost type/orientation/x/y, 8-13 current
piece offsets, 14 next type, and 15-20 preview offsets. Offset values are stored
as value+2 (so 0..4 represents -2..2). This mode bypasses the unknown-type
offset fallback solely for diagnosis. Mode 8 shows decimal live and next
types, mode 7 uses one-hot markers, and mode 6 shows the fixed
reference and true randomized piece without overriding the bag. Mode 5 overrides
the current piece with Z; mode 4 compares a fixed Z with live `TState` state.
Mode 3 compares a fixed Z with one hard-dropped
and committed by the engine; mode 2 uses the engine's offset API; mode 1 builds
the fixed border and solid Z / hollow-center T calibration screen. All modes
replace gameplay; the default is `TETRIS_DIAGNOSTIC=0`.

The OLED is 128-by-32 pixels. The board is rotated to use 60-by-30 pixels;
turn the player 90 degrees clockwise for an upright board. The wheel moves the
piece, navigation button 1 hard-drops, navigation button 2 rotates right, and
Confirm rotates left. There is no manual soft-drop control. Long Confirm returns
to the main menu. After game over, Confirm starts again. Normal controls outside the game
are unchanged. Five-pixel-tall SCORE, LINES and LEVEL labels each have
their five-pixel-tall value centered underneath. The unlabeled next piece is
below the counters and above the board. The playfield is raised one pixel from
the bottom edge of the upright display. Scores are not saved.

Power uses the stock screen-off behavior. The game ends when screen-off is
requested, restoring the normal menu callbacks before the display blanks.
Waking the screen returns to the main menu; starting Tetris again begins a new
game rather than resuming the discarded run.

The game runs in separate temporary RAM, shared with the library-refresh payload
at different times. It reads only its own code from firmware storage; it does
not load an overlay over the music service. Playback memory preservation is
tested in emulation, but actual concurrent playback, button timing, screen
wake behavior and power-off still require device testing. Do not treat this
build as device-validated. The previous working build remains in `out/custom/`.

Game logic reuses [T-Engine](https://github.com/raywan/tengine), under the MIT
license in `third_party/tengine/LICENSE`, with embedded adaptations documented
in `third_party/tengine/README.nanite.md`.

Tests (from the repository root, with Clang and Python's `unicorn` installed):

```sh
clang -std=c11 -O1 -g -fsanitize=address,undefined -Ithird_party/tengine tests/tetris_engine_test.c third_party/tengine/tengine.c -o out/engine-test
out/engine-test
python3 tests/tetris_firmware_test.py out/nanitecfw-6.0.54-20261208/NANOV170.IMG
```

## Requirements

1. The official **Echo Nano V1.7.0** firmware file `NANOV170.IMG`, from FiiO's
   website. The build checks its SHA-256 and refuses any other file:
   `54a45d233a23c3ce142d1da9c093cc40c46eba417aa91fe915ee867726f4a116`.
   Other firmware versions are **not** supported: the patches are written for the
   exact code addresses of V1.7.0.
2. GNU make 4.3 or newer, `python3` (3.8 or newer, standard library only) and
   the Arm GNU toolchain (`arm-none-eabi-gcc`, binutils 2.39 or newer):
   - macOS: `brew install make python && brew install --cask gcc-arm-embedded`,
     then use **`gmake`** instead of `make` (the system make is too old).
   - Debian 12+ / Ubuntu 24.04+: `sudo apt install make python3 gcc-arm-none-eabi`
   - Nix: `nix-shell` in this directory provides everything.

## Build

```sh
cp ~/Downloads/NANOV170.IMG .        # the official V1.7.0 image
make check                           # confirms it is the expected stock file
make                                 # writes out/nanitecfw-VERSION-DATE/NANOV170.IMG
```

`DATE` is the build date stored in the image. The device boots whichever
firmware copy has the **newest** date, so every image you flash must have a
newer date than the one before it. The stock V1.7.0 image is dated 2026-08-24
and the build defaults to one day later, `DATE=20260825`. Keep the date as
close to stock as possible: a future official FiiO update with an older date
than your custom build would be ignored. If you flash another custom build
over this one, raise the date by a day each time (`make DATE=20260826`, ...).

Builds automatically use the version from `patches/about_version.patch` and the
chosen date in their output folder. For example, `gmake DATE=20261208` on macOS
writes `out/nanitecfw-6.0.54-20261208/NANOV170.IMG`. Add `TETRIS_DIAGNOSTIC=10`
for the gameplay trace. This date is suitable only
if the installed firmware is older; increase it if needed. The build prints
the exact output path after verification. `OUT=...` still overrides the path.

Keep the image filename `NANOV170.IMG` when installing: acceptance of arbitrary
filenames has not been verified. The versioned folder distinguishes builds on
your computer without depending on a different device-side filename. Older
files such as `out/NANOV170.IMG` are not updated by these versioned builds.

## Install

1. Connect the Echo Nano by USB and copy `NANOV170.IMG` from the versioned folder
  printed by the build to the root of its internal storage. For the current
  example, use `out/nanitecfw-6.0.54-20261208/NANOV170.IMG`. Copy the image,
  not the enclosing folder, and leave the filename unchanged.
2. Eject it and restart the player; it installs the update while it boots.
3. Check **About**: it should show `6.0.x`.
4. Run **Media Library Refresh** once.

## Recovery

To go back to the official firmware, build the stock code with a newer date and
flash it the same way:

```sh
make recovery                        # dated 20260826
```

The default date is one day after the default build. If you flashed custom
builds with later dates, pass a newer one: `make recovery DATE=...`.

This writes `out/recovery/NANOV170.IMG`: FiiO's unmodified code with only the
date changed, because the device would ignore the original file while a
newer-dated custom build is installed.

For the customized image built above with `DATE=20261208`, use
`gmake recovery DATE=20261209` on macOS instead of the default recovery date.
Always choose a recovery date newer than the last image you installed.

## Known issues

- FLAC files tagged only with `ALBUM ARTIST` or `ALBUM_ARTIST` (instead of
  `ALBUMARTIST`) are grouped by track artist in Album Artists. This is stock
  behaviour.
- Playback can freeze on some files that show "Format Not Supported!". The cause
  is not found yet.
- Shuffle order is not kept across power cycles.
- Power saving (6.0.5) is not yet tested on hi-res files (FLAC 24/192): watch for
  dropouts. A very fast spin of the scroll wheel may skip steps.

## How it works

The image is the stock firmware with patched bytes, a recomputed CRC and a new
date. Everything is applied at build time from three kinds of input:

- `patches/*.patch`: data patches, written at a runtime address inside a
  firmware module, or as UI strings by ID and language:
  ```
  32:0307cf14:u"6.0.54"                # module 32, UTF-16 string + NUL
  22:030794f4:0a21                     # raw hex bytes
  lang:82:en:u"Shuffle All"            # UI string 0x82, English
  ```
- `patches/*.S`: small Thumb-2 code patches, each assembled at its target address
  (`@ patch MOD ADDR`; see `patches/examples/template.S` and `patches/fw.inc`).
- `src/`: C code that runs from free RAM during the media-library refresh
  (faster tag reading and sorting, Recent Albums and Artists tables, the log).
  `src/hooks.txt` lists the firmware calls redirected into it.

`tools/rknano_fw.py` reads and writes the RKNano image format (`info`, `crc`,
`check`, `patch`); `tools/build_blob.sh` builds the C code; `tools/asm2patch.sh`
assembles the `.S` patches.

### Image format

| Offset | Content |
|---|---|
| `0x000` | u16 year, u16 monthday (BCD build date). Loader boots the valid flash slot with the newest date |
| `0x010` | `"Rockchip"`, `0x030` `"RKnano SDK 1.0"` |
| `0x070..0x150` | resource section table (offset/length pairs) |
| `0x1F4` | firmware length, `0x1F8` `"RKnanoFW"` (checked by the loader) |
| `0x200` | module table: `load_base`, `count`, then 8-word entries `code_load, code_exec, code_len, data_load, data_exec, data_len, bss_exec, bss_len` |
| `0xF8C` | module 0 (resident kernel) at `0x03050000`; overlay modules (UI screens, services) are swapped in at `0x03078ab0..` |
| `0x15212C` | sysdefault · fonts · codepage · lang (21 languages) · images |
| `fw_len` | copy of the `0x200` header, compared with sector 0 by the loader |
| `end-4` | Rockchip CRC32 (poly `0x04C10DB7`, MSB-first, init 0) over everything before it, LE |
