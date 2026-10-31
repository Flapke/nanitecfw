# FiiO Echo Nano custom firmware: patches the official V1.7.0 image you supply.
#
#   make                 build out/nanitecfw-VERSION-DATE/NANOV170.IMG from stock + patches/ + src/
#   make FW=path/to/NANOV170.IMG   stock image somewhere else
#   make DATE=20260901   build date (default 20260825, one day after stock V1.7.0)
#   make recovery        unmodified stock code dated 20260826 -> out/recovery/NANOV170.IMG
#   make check           is the input the expected stock image?
#   make info / verify / diff / clean

FW      ?= NANOV170.IMG
DATE    ?= 20260825
TETRIS_DIAGNOSTIC ?= 0
PY      := python3
FWTOOL  := $(PY) tools/rknano_fw.py
VERSION := $(shell $(PY) -c 'from tools.rknano_fw import parse_patches; print(next(parse_patches(["@patches/about_version.patch"]))[2].decode("utf-16le").rstrip("\0"))')
OUT     ?= out/nanitecfw-$(VERSION)-$(DATE)/NANOV170.IMG

PATCHES := $(sort $(wildcard patches/*.patch))
ASM     := $(sort $(wildcard patches/*.S))
GEN     := $(ASM:patches/%.S=out/gen/%.patch)
SRC     := $(wildcard src/*.c src/*.S src/*.h src/*.ld)
BLOB    := out/gen/cfw_blob.patch out/gen/cfw_hooks.patch
GAME_SRC := $(wildcard src/tetris/* third_party/tengine/*)
GAME    := out/gen/tetris_blob.patch
TETRIS_MODE_STAMP := out/gen/.tetris-mode-$(TETRIS_DIAGNOSTIC)

ifeq ($(filter grouped-target,$(.FEATURES)),)
$(error GNU make 4.3 or newer needed (on macOS: brew install make, then run gmake))
endif
ifeq ($(shell command -v arm-none-eabi-gcc),)
$(warning arm-none-eabi-gcc not found - see README "Requirements")
endif

.PHONY: all build recovery check verify info diff help clean

all: build

help:
	@sed -n 's/^#   //p' Makefile

check:
	$(FWTOOL) check $(FW)

build: check $(GEN) $(BLOB) $(GAME)
	@mkdir -p $(dir $(OUT))
	$(FWTOOL) patch $(FW) $(OUT) --date $(DATE) $(addprefix @,$(PATCHES) $(GEN) $(BLOB) $(GAME))
	$(FWTOOL) crc $(OUT)
	@printf '\nBuilt firmware %s (date %s): %s\n' '$(VERSION)' '$(DATE)' '$(OUT)'

# C code run from RAM during the library refresh; syms.inc exports its symbols to patches/*.S
$(BLOB) out/gen/syms.inc &: $(SRC) src/hooks.txt tools/build_blob.sh tools/hooks.py
	tools/build_blob.sh out/gen $(FW)

$(TETRIS_MODE_STAMP):
	@mkdir -p out/gen
	@rm -f out/gen/.tetris-mode-*
	@touch $@

$(GAME) out/gen/tetris_syms.inc &: $(GAME_SRC) tools/build_tetris.sh src/libc.c src/fw.h $(TETRIS_MODE_STAMP)
	bash tools/build_tetris.sh out/gen $(FW) $(TETRIS_DIAGNOSTIC)

# stock code, new date: the loader boots the newest valid copy, so the original
# image would not replace a newer custom build
ifeq ($(origin DATE),file)
recovery: DATE := 20260826
endif
recovery: check
	@mkdir -p out/recovery
	$(FWTOOL) patch $(FW) out/recovery/NANOV170.IMG --date $(DATE)
	$(FWTOOL) crc out/recovery/NANOV170.IMG

out/gen/%.patch: patches/%.S patches/fw.inc out/gen/syms.inc out/gen/tetris_syms.inc tools/asm2patch.sh
	tools/asm2patch.sh $< $@

verify:
	$(FWTOOL) crc $(OUT)

info:
	$(FWTOOL) info $(FW)

# byte ranges that differ from stock
diff:
	@cmp -l $(FW) $(OUT) | awk 'NR==1||$$1!=p+1{if(NR>1)printf "-0x%x\n",p-1;printf "0x%x",$$1-1}{p=$$1}END{if(NR)printf "-0x%x\n",p-1}'

clean:
	rm -rf out
