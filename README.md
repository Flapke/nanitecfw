# FiiO Echo Nano Custom Firmware

Patches for the official FiiO Echo Nano **V1.7.0** firmware. This repository contains source patches and build tools, not FiiO firmware. You must supply the official `NANOV170.IMG` yourself.

> **Warning:** This is unofficial firmware. Flashing carries a risk of data loss or an unusable device. Read [Recovery](#recovery) before installing.

## What changes

- Speeds up media-library refresh.
- Adds Shuffle All for the full song library.
- Makes playback sequential when starting an album or a song inside an album. **Play All** from an artist uses shuffle; other lists retain their selected mode.
- Skips unsupported tracks without repeatedly showing a popup.
- Adds power-saving behavior during playback.
- Adds Tetris, the video game! Controls: wheel moves, nav1 rotates right, nav2 hard-drops, Confirm rotates left, and long Confirm exits. The playfield is rotated; hold the player 90 degrees clockwise to view it upright.
- Reorders the main menu to **Tetris**, **Shuffle All**, **Music Playback**, **Media Library**, and **System Settings**.

## Requirements

- Official Echo Nano V1.7.0 firmware, named `NANOV170.IMG`. The build verifies its SHA-256 and rejects other firmware versions.
- GNU make 4.3 or newer, Python 3, and the Arm GNU toolchain (`arm-none-eabi-gcc` and binutils).
- macOS users: install GNU make and the Arm GNU toolchain, then use `gmake` instead of the system `make`.
- Nix users can run `nix-shell` in this directory.

## Build

Place the official firmware image in the repository root, then run:

```sh
make check
make [DATE=20261211]
```

The build writes `out/nanitecfw-VERSION-DATE/NANOV170.IMG`; the version comes from `patches/about_version.patch`. Set `DATE` to a value newer than the firmware currently installed on the player. The build prints the output path and verifies the image CRC and header.

Keep the filename `NANOV170.IMG` when installing. Firmware images and build output are excluded from Git; do not commit or upload the firmware image.

## Install

1. Copy `NANOV170.IMG` from the generated versioned output directory to the root of the player's internal storage. Copy the image itself, not the folder.
2. Eject the player safely and restart it to install the update.
3. Check **Information** in **Settings** to confirm the custom version.
4. Run **Media Library Refresh** once after installing.

## Recovery

Build the unmodified stock firmware with a date newer than the latest image installed:

```sh
gmake recovery DATE=20261211
```

Copy `out/recovery/NANOV170.IMG` to the player and install it the same way. Always use a date later than the currently installed firmware.

## Tests

The firmware tests use Python's `unicorn` package. From the repository root:

```sh
clang -std=c11 -O1 -g -fsanitize=address,undefined \
  -Ithird_party/tengine tests/tetris_engine_test.c \
  third_party/tengine/tengine.c -o out/engine-test
out/engine-test
python3 tests/tetris_firmware_test.py out/nanitecfw-6.0.55-20261209/NANOV170.IMG
```

The engine test covers piece bags, movement, gravity, line clearing, and bounds safety. Firmware tests exercise menu routing, callbacks, controls, display rendering, and payload loading in an ARM emulator; they do not replace testing on the physical player.

## Project layout

- `patches/`: binary data and assembly patches for firmware V1.7.0.
- `src/`: firmware support code.
- `src/tetris/` and `third_party/tengine/`: Tetris integration and engine.
- `tests/`: engine and firmware-emulation tests.
- `tools/`: firmware parser and build scripts.
