# FiiO Echo Nano Custom Firmware

Custom firmware for the FiiO Echo Nano, supporting official **V1.7.0** and **V2.0.0** firmware. This repository contains source patches and build tools, not FiiO firmware. Supply the official `NANOV170.IMG` or `NANOV200.IMG` yourself.

> **Warning:** This is unofficial firmware. Flashing carries a risk of data loss or an unusable device. Read [Recovery](#recovery) before installing.

## What changes

- Adds Shuffle All for the full song library.
- Makes playback sequential when starting an album or a song inside an album. **Play All** from an artist uses shuffle; other lists retain their selected mode.
- Skips unsupported tracks without repeatedly showing a popup.
- Adds power-saving behavior during playback.
- Adds Tetris, the video game! Controls: wheel moves, nav1 rotates right, nav2 hard-drops, Confirm rotates left, and long Confirm exits. The playfield is rotated; hold the player 90 degrees clockwise to view it upright.
- Reorders the main menu to **Tetris**, **Shuffle All**, **Music Playback**, **Media Library**, and **System Settings**.

V2 retains its stock Library submenu and **M3U playlist support**. Faster library refresh and `CFWLOG.TXT` logging are currently V1-only; Recent Albums, separate artist indexing, and the custom Library views have not been ported to V2.

## Requirements

- Official Echo Nano V1.7.0 (`NANOV170.IMG`) or V2.0.0 (`NANOV200.IMG`). The build verifies the stock image's SHA-256 and rejects unknown images.
- GNU make 4.3 or newer, Python 3, and the Arm GNU toolchain (`arm-none-eabi-gcc` and binutils).
- macOS users: install GNU make and the Arm GNU toolchain, then use `gmake` instead of the system `make`.
- Nix users can run `nix-shell` in this directory.

## Build

Place the official firmware image in the repository root, then choose your version:

```sh
# V1.7.0
gmake FW=NANOV170.IMG build

# V2.0.0
gmake FW=NANOV200.IMG build
```

The build prints the versioned output path under `out/` and verifies the image CRC and header. To override the build date, append `DATE=20261211`; use a date newer than the firmware currently installed on the player.

Keep the generated filename (`NANOV170.IMG` or `NANOV200.IMG`) when installing. Firmware images and build output are excluded from Git; do not commit or upload firmware images.

## Install

1. Copy the generated `.IMG` from the versioned output directory to the root of the player's internal storage. Copy the image itself, not the folder.
2. Eject the player safely and restart it to install the update.
3. Check **Information** in **Settings** to confirm the custom version.
4. Run **Media Library Refresh** once after installing.

## Recovery

Create an unmodified stock image with a date newer than the firmware installed. After building V2, for example:

```sh
python3 tools/rknano_fw.py patch NANOV200.IMG out/NANOV200.IMG --date 20261211
```

For V1, replace both filenames with `NANOV170.IMG`. Install the image from `out/` the same way as above, keeping its filename unchanged.

## Tests

Tests are in `tests/`; the firmware-emulation tests require Python's `unicorn` package. Emulator checks do not replace testing on the physical player.

## Project layout

- `patches/`: V1 patches; `patches/v2/` contains the V2 patches.
- `src/`: firmware support code.
- `src/tetris/` and `third_party/tengine/`: Tetris integration and engine.
- `tests/`: engine and firmware-emulation tests.
- `tools/`: firmware parser and build scripts.
