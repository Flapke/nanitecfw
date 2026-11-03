import struct
import subprocess
import sys
import unittest
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.rknano_fw import load, parse_patches


class V2FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image = load(str(ROOT / "NANOV200.IMG"))
        files = [ROOT / "patches/v2/power_idle.patch"]
        for name in ("album_sequence_50_mod23_play", "album_sequence_51_mod24_call"):
            output = ROOT / ("out/gen/v2-" + name + ".patch")
            subprocess.run(
                ["bash", "tools/asm2patch.sh", "patches/v2/" + name + ".S", str(output)],
                cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
            )
            files.append(output)
        for module, address, data in parse_patches(["@" + str(path) for path in files]):
            cls.image.patch(module, address, data)

    def machine(self, modules):
        cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        cpu.mem_map(0x03000000, 0x100000)
        for index in modules:
            module = self.image.modules[index]
            for kind in ("code", "data"):
                offset = self.image.l2f(module[kind + "_load"])
                length = module[kind + "_len"]
                if length:
                    cpu.mem_write(module[kind + "_exec"], bytes(self.image.d[offset:offset + length]))
        cpu.reg_write(UC_ARM_REG_SP, 0x03040000)
        cpu.reg_write(UC_ARM_REG_LR, 0x03010001)
        return cpu

    def test_idle_sleep_respects_inhibition_and_recording(self):
        for inhibited, recording, expected in ((0, 0, 1), (1, 0, 0), (0, 1, 0)):
            with self.subTest(inhibited=inhibited, recording=recording):
                cpu = self.machine((0,))
                sleeps = []

                def hook(machine, address, size, user_data):
                    if address == 0x0306B138:
                        self.assertEqual(machine.reg_read(UC_ARM_REG_R0), 0x1F)
                        machine.reg_write(UC_ARM_REG_R0, inhibited)
                    elif address == 0x03059A18:
                        machine.reg_write(UC_ARM_REG_R0, recording)
                    elif address == 0x03059A64:
                        sleeps.append(address)
                    else:
                        return
                    machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

                cpu.hook_add(UC_HOOK_CODE, hook)
                cpu.emu_start(0x0306A205, 0x0306A220, count=100)
                self.assertEqual(len(sleeps), expected)

    def test_wheel_period_at_every_initialization_site(self):
        for module, address in ((0, 0x0306B364), (1, 0x0307B198), (9, 0x0307D684), (33, 0x03083D34)):
            with self.subTest(module=module):
                cpu = self.machine((module,))
                cpu.emu_start(address | 1, address + 4, count=1)
                self.assertEqual(cpu.reg_read(UC_ARM_REG_R2), 1000)

    def test_album_modes_and_m3u_pass_through(self):
        cases = (
            (4, 0, [0x600, 0x400], 6, 0),
            (4, 1, [0x600, 0x400], 6, 0),
            (3, 1, [0x500, 0x600, 0x400], 7, 1),
            (3, 2, [0x500, 0x600, 0x400], 6, 0),
            (14, 0, [0x600], 5, 1),
            (1, 0, [0x400], 5, 1),
            (5, 0, [0x700, 0x500, 0x600, 0x400], 5, 1),
            (5, 2, [0x700, 0x500, 0x600, 0x400], 6, 0),
            (5, 3, [0x700, 0x500, 0x600, 0x400], 6, 0),
        )
        for list_type, level, fields, mode, order in cases:
            with self.subTest(list_type=list_type, level=level):
                cpu = self.machine((23, 24))
                cpu.mem_write(0x0300C36A, struct.pack("<H", list_type))
                cpu.mem_write(0x0300E972, struct.pack("<H", level))
                cpu.mem_write(0x0300E738, struct.pack("<" + "H" * len(fields), *fields))
                cpu.mem_write(0x0300C0B9, b"\x05")
                cpu.mem_write(0x0300C0BB, b"\x01")
                events = []

                def message(machine, address, size, user_data):
                    events.append(machine.reg_read(UC_ARM_REG_R0))
                    machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

                cpu.hook_add(UC_HOOK_CODE, message, begin=0x0306B0D8, end=0x0306B0D8)
                cpu.emu_start(0x0307D42D, 0x0307D430, count=200)
                self.assertEqual(cpu.reg_read(UC_ARM_REG_PC), 0x0307D430)
                self.assertEqual(cpu.reg_read(UC_ARM_REG_SP), 0x03040000 - 36)
                self.assertEqual(bytes(cpu.mem_read(0x0300C0B9, 1)), bytes([mode]))
                self.assertEqual(bytes(cpu.mem_read(0x0300C0BB, 1)), bytes([order]))
                self.assertEqual(events, [] if mode == 5 else [0x113, 0x114])


if __name__ == "__main__":
    unittest.main()