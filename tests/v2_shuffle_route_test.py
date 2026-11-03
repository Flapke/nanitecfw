import struct
import sys
import unittest
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.rknano_fw import load

IMAGE_PATH = ROOT / "out/nanitecfw-6.0.58-20261104/NANOV200.IMG"
DISPATCH_ADDRESS = 0x0307ACFA
OPEN_WINDOW_ADDRESS = 0x0306B302
RETURN_ADDRESS = 0x03010000
MENU_CURSOR = 0x0300E600
LIBRARY_STATE = 0x0300C04C
MUSIC_TYPE_ID = 0x0300C36A
SHUFFLE_TITLE = 0x82


class ShuffleRouteTests(unittest.TestCase):
    def test_main_menu_icon_slots_match_the_visible_items(self):
        image = load(str(IMAGE_PATH))
        offset, unused = image.region(0, 0x03004124)
        icons = struct.unpack_from("<5I", image.d, offset)
        self.assertEqual(
            icons,
            (0x03072E77, 0x03072DFF, 0x03072DD7, 0x03072E27, 0x03072E4F),
        )

    def test_shuffle_bitmap_fits_its_twenty_column_slot(self):
        image = load(str(IMAGE_PATH))
        stock = load(str(ROOT / "NANOV200.IMG"))
        offset, unused = image.region(0, 0x03072DFF)
        bitmap = bytes.fromhex(
            "00001818183860c08080c060381818185c381000"
            "0000181818180c060303060c181818183a1c0800"
        )
        self.assertEqual(len(bitmap), 40)
        self.assertEqual(image.d[offset:offset + 40], bitmap)
        self.assertEqual(image.d[offset + 40:offset + 48], stock.d[offset + 40:offset + 48])

    def dispatch(self, cursor, song_count=12):
        image = load(str(IMAGE_PATH))
        cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        cpu.mem_map(0x03000000, 0x100000)
        module = image.modules[21]
        for kind in ("code", "data"):
            length = module[kind + "_len"]
            if length:
                offset = image.l2f(module[kind + "_load"])
                cpu.mem_write(module[kind + "_exec"], bytes(image.d[offset:offset + length]))
        if module["bss_len"]:
            cpu.mem_write(module["bss_exec"], bytes(module["bss_len"]))

        cpu.mem_write(MENU_CURSOR, struct.pack("<H", cursor))
        cpu.mem_write(LIBRARY_STATE + 0x2E, struct.pack("<H", song_count))
        cpu.mem_write(MUSIC_TYPE_ID, struct.pack("<H", 0))
        cpu.mem_write(LIBRARY_STATE + 0x6D, b"\0")
        cpu.mem_write(LIBRARY_STATE + 0x6F, b"\0")
        cpu.reg_write(UC_ARM_REG_SP, 0x03040000)
        cpu.reg_write(UC_ARM_REG_LR, RETURN_ADDRESS | 1)
        opened = []
        messages = []

        def open_window(machine, address, size, user_data):
            if address == 0x0306B0D8:
                messages.append(machine.reg_read(UC_ARM_REG_R0))
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
                return
            if address == 0x03059A18:
                machine.reg_write(UC_ARM_REG_R0, 1)
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
                return
            window_id = machine.reg_read(UC_ARM_REG_R0)
            descriptor = machine.reg_read(UC_ARM_REG_R1)
            first, title = struct.unpack("<HH", machine.mem_read(descriptor, 4))
            opened.append((window_id, first, title))
            machine.reg_write(UC_ARM_REG_R0, 0)
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        cpu.hook_add(UC_HOOK_CODE, open_window, begin=OPEN_WINDOW_ADDRESS, end=OPEN_WINDOW_ADDRESS)
        cpu.hook_add(UC_HOOK_CODE, open_window, begin=0x03059A18, end=0x03059A18)
        cpu.hook_add(UC_HOOK_CODE, open_window, begin=0x0306B0D8, end=0x0306B0D8)
        cpu.emu_start(DISPATCH_ADDRESS | 1, RETURN_ADDRESS, count=1000)

        self.assertEqual(cpu.reg_read(UC_ARM_REG_PC), RETURN_ADDRESS)
        self.assertEqual(cpu.reg_read(UC_ARM_REG_SP), 0x03040000)
        return cpu, opened, messages

    def test_shuffle_all_opens_all_songs_with_sentinel_title(self):
        cpu, opened, messages = self.dispatch(1)
        self.assertEqual(opened, [(2, 0, SHUFFLE_TITLE)])
        self.assertEqual(struct.unpack("<H", cpu.mem_read(MUSIC_TYPE_ID, 2))[0], 1)
        self.assertEqual(cpu.mem_read(LIBRARY_STATE + 0x6F, 1), b"\1")
        self.assertEqual(cpu.mem_read(LIBRARY_STATE + 0x6D, 1), b"\3")
        self.assertEqual(struct.unpack("<H", cpu.mem_read(0x0300E5DE, 2))[0], SHUFFLE_TITLE)

    def test_library_keeps_its_stock_window(self):
        cpu, opened, messages = self.dispatch(3)
        self.assertEqual(opened, [(1, 0, 0)])

    def test_playback_keeps_its_stock_window(self):
        cpu, opened, messages = self.dispatch(2)
        self.assertEqual(opened, [(1, 0, 0)])
        self.assertIn(0x18C, messages)

    def test_empty_shuffle_does_not_open_a_window(self):
        cpu, opened, messages = self.dispatch(1, song_count=0)
        self.assertEqual(opened, [])
        self.assertIn(0x32, messages)
        self.assertEqual(struct.unpack("<H", cpu.mem_read(0x0300E5DE, 2))[0], 0x7C)


if __name__ == "__main__":
    unittest.main()
