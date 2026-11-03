import struct
import subprocess
import unittest
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.rknano_fw import load, parse_patches

ROOT = Path(__file__).resolve().parents[1]
IMAGE_PATH = ROOT / "NANOV200.IMG"
HOOK_SOURCE = ROOT / "patches/v2/shuffle_20_mod23_key.S"
HOOK_PATCH = ROOT / "out/gen/v2-shuffle_20_mod23_key.patch"
HOOK_ADDRESS = 0x0307B180
GET_KEY_ADDRESS = 0x030632DA
RETURN_ADDRESS = 0x03010000
TITLE_ADDRESS = 0x03004B12
LIST_ADDRESS = 0x0300E968
TICK_ADDRESS = 0xE000E018


class ShuffleHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            ["bash", "tools/asm2patch.sh", str(HOOK_SOURCE), str(HOOK_PATCH)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        image = load(str(IMAGE_PATH))
        mod, address, data = next(parse_patches(["@" + str(HOOK_PATCH)]))
        if mod != 23 or address != HOOK_ADDRESS:
            raise AssertionError("unexpected V2 key-hook patch location")
        cls.hook_bytes = data
        cls.image = image

    def run_hook(self, title, key, count=10, index=3, ticks=12345):
        cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        cpu.mem_map(0x03000000, 0x100000)
        cpu.mem_map(0xE000E000, 0x1000)
        cpu.mem_write(HOOK_ADDRESS, self.hook_bytes)
        cpu.mem_write(TITLE_ADDRESS, struct.pack("<H", title))
        cpu.mem_write(LIST_ADDRESS, struct.pack("<H", count))
        cpu.mem_write(LIST_ADDRESS + 0x16, struct.pack("<H", index))
        cpu.mem_write(TICK_ADDRESS, struct.pack("<I", ticks))
        cpu.reg_write(UC_ARM_REG_SP, 0x03040000)
        cpu.reg_write(UC_ARM_REG_LR, RETURN_ADDRESS | 1)

        def firmware_call(machine, address, size, user_data):
            if address == GET_KEY_ADDRESS:
                machine.reg_write(UC_ARM_REG_R0, key)
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        cpu.hook_add(UC_HOOK_CODE, firmware_call)
        cpu.emu_start(HOOK_ADDRESS | 1, RETURN_ADDRESS, count=1000)
        if cpu.reg_read(UC_ARM_REG_PC) != RETURN_ADDRESS:
            raise AssertionError("V2 Shuffle All hook did not return")
        title_after = struct.unpack("<H", cpu.mem_read(TITLE_ADDRESS, 2))[0]
        index_after = struct.unpack("<H", cpu.mem_read(LIST_ADDRESS + 0x16, 2))[0]
        return cpu.reg_read(UC_ARM_REG_R0), title_after, index_after

    def test_shuffle_all_selects_random_song(self):
        key, title, index = self.run_hook(0x82, 0)
        self.assertEqual(key, 0x40000040)
        self.assertEqual(title, 0x5A)
        self.assertLess(index, 10)

    def test_m3u_title_and_key_pass_through(self):
        original_key = 0x40008000
        key, title, index = self.run_hook(0x5E, original_key)
        self.assertEqual(key, original_key)
        self.assertEqual(title, 0x5E)
        self.assertEqual(index, 3)

    def test_other_browser_title_passes_through(self):
        original_key = 0x40004000
        key, title, index = self.run_hook(0x5A, original_key)
        self.assertEqual(key, original_key)
        self.assertEqual(title, 0x5A)
        self.assertEqual(index, 3)


if __name__ == "__main__":
    unittest.main()
