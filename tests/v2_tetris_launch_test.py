import struct
import subprocess
import sys
import unittest
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
from unicorn.arm_const import (
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_R3,
    UC_ARM_REG_SP,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.rknano_fw import load, parse_patches

STOCK_IMAGE_PATH = ROOT / "NANOV200.IMG"
IMAGE_PATH = ROOT / "out/nanitecfw-6.0.58-20261104/NANOV200.IMG"
OUTPUT = ROOT / "out/gen/v2"
LAUNCH_SOURCE = ROOT / "patches/v2/tetris_10_mod21_launch.S"
LAUNCH_PATCH = OUTPUT / "v2-tetris_10_mod21_launch.patch"
EMPTY_PATCH = OUTPUT / "v2-shuffle_12_mod21_empty.patch"
LAUNCH_ADDRESS = 0x0307A750
SECTOR_READ_ADDRESS = 0x0306B7AE
LOCK_ADDRESS = 0x0306A4A6
UNLOCK_ADDRESS = 0x0306A4FE
READ_BASE = 0x0300C33C
RETURN_ADDRESS = 0x03010000


class TetrisLaunchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["bash", "tools/build_tetris.sh", str(OUTPUT), str(STOCK_IMAGE_PATH), "0", "1"],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            ["bash", "tools/asm2patch.sh", str(LAUNCH_SOURCE), str(LAUNCH_PATCH)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            ["bash", "tools/asm2patch.sh", str(ROOT / "patches/v2/shuffle_12_mod21_empty.S"), str(EMPTY_PATCH)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        image = load(str(IMAGE_PATH))
        cls.image = image
        cls.symbols = {}
        for line in (OUTPUT / "tetris_syms.inc").read_text().splitlines():
            _, name, value = line.split()
            cls.symbols[name.rstrip(",")] = int(value, 16)
        cls.text_size = cls.symbols["tetris_text_size"]
        cls.bss_size = cls.symbols["tetris_bss_size"]
        cls.flash_offset = cls.symbols["tetris_flash_offset"]
        cls.game_start = cls.symbols["__game_start"]
        cls.game_bss = cls.symbols["__game_bss"]
        cls.launch_bytes = next(parse_patches(["@" + str(LAUNCH_PATCH)]))[2]
        cls.empty_address, cls.empty_bytes = next(
            (address, data)
            for mod, address, data in parse_patches(["@" + str(EMPTY_PATCH)])
            if mod == 21
        )

    def test_reads_v2_payload_initializes_bss_and_returns(self):
        cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        cpu.mem_map(0x03000000, 0x100000)
        cpu.mem_map(0xE000E000, 0x1000)
        module = self.image.modules[0]
        for kind in ("code", "data"):
            length = module[kind + "_len"]
            if length:
                offset = self.image.l2f(module[kind + "_load"])
                cpu.mem_write(module[kind + "_exec"], bytes(self.image.d[offset:offset + length]))
        if module["bss_len"]:
            cpu.mem_write(module["bss_exec"], bytes(module["bss_len"]))
        cpu.mem_write(LAUNCH_ADDRESS, self.launch_bytes)
        cpu.mem_write(self.empty_address, self.empty_bytes)
        cpu.mem_write(READ_BASE, struct.pack("<I", 0x200))
        cpu.mem_write(0x0300D120, b"\0")
        cpu.mem_write(0x0300D10C, struct.pack("<I", 0))
        cpu.reg_write(UC_ARM_REG_SP, 0x03040000)
        cpu.mem_write(0x03040000 + 36, struct.pack("<III", 0, 0, RETURN_ADDRESS | 1))
        cpu.reg_write(UC_ARM_REG_LR, RETURN_ADDRESS | 1)
        reads = []
        entered = []
        expected = bytes(
            self.image.d[0x200 + self.flash_offset:0x200 + self.flash_offset + self.text_size]
        )

        def firmware_hook(machine, address, size, user_data):
            if address in (LOCK_ADDRESS, UNLOCK_ADDRESS):
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
            elif address in (0x0306B0D8, 0x0306B11A):
                machine.reg_write(UC_ARM_REG_R0, 0)
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
            elif address == 0x0306B138:
                machine.reg_write(UC_ARM_REG_R0, 0)
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
            elif address == SECTOR_READ_ADDRESS:
                device = machine.reg_read(UC_ARM_REG_R0)
                sector = machine.reg_read(UC_ARM_REG_R1)
                sectors = machine.reg_read(UC_ARM_REG_R2)
                destination = machine.reg_read(UC_ARM_REG_R3)
                source = sector * 512
                length = sectors * 512
                reads.append((device, source, length))
                machine.mem_write(destination, bytes(self.image.d[source:source + length]))
                machine.reg_write(UC_ARM_REG_R0, 0)
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
            elif address == self.symbols["tetris_enter"]:
                entered.append(True)
                loaded = bytes(machine.mem_read(self.game_start, self.text_size))
                if loaded != expected:
                    mismatch = next(i for i, (actual, wanted) in enumerate(zip(loaded, expected)) if actual != wanted)
                    self.fail("payload mismatch at %#x loaded=%s expected=%s reads=%s" % (
                        mismatch, loaded[mismatch:mismatch + 16].hex(), expected[mismatch:mismatch + 16].hex(), reads
                    ))
                self.assertEqual(bytes(machine.mem_read(self.game_bss, self.bss_size)), bytes(self.bss_size))
                machine.reg_write(UC_ARM_REG_R0, 1)
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        cpu.hook_add(UC_HOOK_CODE, firmware_hook)
        cpu.emu_start(LAUNCH_ADDRESS | 1, RETURN_ADDRESS, count=100000)

        self.assertEqual(cpu.reg_read(UC_ARM_REG_PC), RETURN_ADDRESS)
        self.assertEqual(cpu.reg_read(UC_ARM_REG_R0), 0)
        self.assertTrue(reads)
        self.assertTrue(all(device == 0x30000 for device, source, length in reads))
        self.assertEqual(entered, [True])


if __name__ == "__main__":
    unittest.main()
