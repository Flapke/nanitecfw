import struct
import sys
import unittest
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_SP,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.rknano_fw import LANGS, load

IMAGE_PATH = sys.argv.pop(1) if len(sys.argv) > 1 else 'out/tetris/NANOV170.IMG'


class GameMachine:
    def __init__(self):
        self.image = load(IMAGE_PATH)
        self.cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        self.cpu.mem_map(0x03000000, 0x100000)
        self.cpu.mem_map(0xe000e000, 0x1000)
        self.key = 0
        self.double_click = 0
        self.frame = None
        self.display_bytes = []
        self.fail_flash_read = False
        self.flags = set()
        self.screen_toggle_on_key = False
        self.screen_off_calls = 0
        self.engine_calls = []
        self.windows = []
        self.module_loads = []
        self.symbols = {
            name: int(value, 16) for value, kind, name in
            (line.split() for line in Path('out/gen/tetris.nm').read_text().splitlines())
        }
        self.load_module(0)
        self.load_module(4)
        self.load_module(21)
        self.cpu.hook_add(UC_HOOK_CODE, self.hook)
        self.original_callbacks = self.cpu.mem_read(0x0300e6c4, 12)
        self.write16(0x0300e708, 0)
        self.write32(0xe000e018, 12345)
        self.write32(0x0300d454, 0x0200)

    def load_module(self, index):
        module = self.image.modules[index]
        for kind in ['code', 'data']:
            length = module[kind + '_len']
            if length:
                offset = self.image.l2f(module[kind + '_load'])
                self.cpu.mem_write(module[kind + '_exec'], bytes(self.image.d[offset:offset + length]))
        if module['bss_len']:
            self.cpu.mem_write(module['bss_exec'], bytes(module['bss_len']))

    def write16(self, address, value):
        self.cpu.mem_write(address, struct.pack('<H', value))

    def write32(self, address, value):
        self.cpu.mem_write(address, struct.pack('<I', value))

    def read32(self, address):
        return struct.unpack('<I', self.cpu.mem_read(address, 4))[0]

    def return_value(self, value=0):
        self.cpu.reg_write(UC_ARM_REG_R0, value)
        self.cpu.reg_write(UC_ARM_REG_PC, self.cpu.reg_read(UC_ARM_REG_LR))

    def hook(self, cpu, address, size, user_data):
        for name in ['te_move_down', 'te_hard_drop', 'te_rotate_left', 'te_rotate_right']:
            if address == self.symbols.get(name):
                self.engine_calls.append(name)
        if address == 0x0306b6bc:
            index = cpu.reg_read(UC_ARM_REG_R0)
            self.module_loads.append(index)
            self.load_module(index)
            self.return_value()
        elif address == 0x0307aef0:
            self.return_value()
        elif address == 0x0306b36c:
            if self.fail_flash_read:
                self.return_value(1)
                return
            from unicorn.arm_const import UC_ARM_REG_R2, UC_ARM_REG_R3
            source = cpu.reg_read(UC_ARM_REG_R1)
            size = cpu.reg_read(UC_ARM_REG_R2)
            destination = cpu.reg_read(UC_ARM_REG_R3)
            file_offset = source - self.read32(0x0300d454) + 0x200
            cpu.mem_write(destination, bytes(self.image.d[file_offset:file_offset + size]))
            self.return_value()
        elif address in [0x0306a40e, 0x0306a466]:
            self.return_value()
        elif address == 0x0306b040:
            self.flags.add(cpu.reg_read(UC_ARM_REG_R0))
            self.return_value()
        elif address == 0x0306b082:
            self.flags.discard(cpu.reg_read(UC_ARM_REG_R0))
            self.return_value()
        elif address == 0x0306b05c:
            message = cpu.reg_read(UC_ARM_REG_R0)
            result = int(message in self.flags)
            self.flags.discard(message)
            self.return_value(result)
        elif address == 0x0306b0a0:
            self.return_value(int(cpu.reg_read(UC_ARM_REG_R0) in self.flags))
        elif address == 0x03068aee:
            self.screen_off_calls += 1
            self.return_value()
        elif address in [0x030599b8,
                 0x03078cd2, 0x03078ac8, 0x03078b1e]:
            self.return_value()
        elif address == 0x0306a532:
            self.return_value(self.read32(0x0300d144))
        elif address == 0x03063242:
            if self.screen_toggle_on_key:
                self.flags.add(0x17)
                self.screen_toggle_on_key = False
            self.return_value(self.key)
            self.key = 0
        elif address == 0x03051574:
            self.return_value(self.double_click)
        elif address == 0x0305159a:
            self.double_click = 0
            self.return_value()
        elif address == 0x03079010:
            pointer = self.read32(cpu.reg_read(UC_ARM_REG_SP))
            self.frame = bytes(cpu.mem_read(pointer, 512))
        elif address == 0x03078b56:
            self.display_bytes.append(cpu.reg_read(UC_ARM_REG_R0) & 255)
            self.return_value()
        elif address == 0x0306b26a:
            self.windows.append(cpu.reg_read(UC_ARM_REG_R0))
            self.return_value()

    def call(self, address):
        self.cpu.reg_write(UC_ARM_REG_SP, 0x03040000)
        self.cpu.reg_write(UC_ARM_REG_LR, 0x03010001)
        self.cpu.emu_start(address | 1, 0x03010000, count=1000000)
        if self.cpu.reg_read(UC_ARM_REG_PC) != 0x03010000:
            raise AssertionError('Firmware callback did not return')
        return self.cpu.reg_read(UC_ARM_REG_R0)

    def launch(self):
        return self.call(0x03079b1e)

    def state(self):
        self.call(self.symbols['te_get_state'])
        return self.cpu.reg_read(UC_ARM_REG_R0)


class TetrisFirmwareTests(unittest.TestCase):
    def test_labels_and_default(self):
        image = load(IMAGE_PATH)
        labels = []
        for index in range(5):
            offset, unused = image.region(21, 0x0300e6de + index * 8)
            title = struct.unpack_from('<H', image.d, offset)[0]
            offset = image.lang_text(LANGS.index('en'), title)
            labels.append(image.d[offset:offset + 200].decode('utf-16le').split('\0')[0])
        self.assertEqual(labels, ['Tetris', 'Shuffle All', 'Music Playback',
                      'Media Library', 'System Settings'])
        offset, unused = image.region(21, 0x03079b34)
        self.assertEqual(image.d[offset:offset + 5], bytes.fromhex('0b0b070b9c'))
        offset, unused = image.region(21, 0x0307941c)
        self.assertEqual(image.d[offset:offset + 2], bytes.fromhex('0220'))
        offset, unused = image.region(21, 0x03079ce2)
        self.assertEqual(image.d[offset:offset + 2], bytes.fromhex('0221'))
        offset, unused = image.region(21, 0x03079504)
        self.assertEqual(struct.unpack_from('<5I', image.d, offset)[2:4],
                 (0x03072d5f, 0x03072daf))

    def test_launch_render_exit(self):
        machine = GameMachine()
        self.assertEqual(machine.launch(), 0)
        self.assertEqual(machine.module_loads, [])
        self.assertFalse(machine.windows)
        self.assertEqual(machine.read32(0x0300e6c4), machine.symbols['tetris_update'] | 1)
        machine.call(machine.symbols['tetris_paint'])
        self.assertIsNotNone(machine.frame)
        self.assertGreater(sum(byte.bit_count() for byte in machine.frame), 100)
        self.assertEqual(len(machine.display_bytes), 520)
        transmitted = bytes(value for index, value in enumerate(machine.display_bytes)
                    if index % 130 >= 2)
        self.assertEqual(transmitted, machine.frame)
        machine.key = 0x20000040
        machine.call(machine.symbols['tetris_key'])
        self.assertEqual(machine.cpu.mem_read(0x0300e6c4, 12), machine.original_callbacks)

    def test_tetris_callbacks_stay_active_and_consume_idle_events(self):
        machine = GameMachine()
        machine.launch()
        self.assertEqual(machine.call(machine.symbols['tetris_key']), 0)
        self.assertEqual(machine.read32(0x0300e6c4), machine.symbols['tetris_update'] | 1)
        self.assertEqual(machine.call(machine.symbols['tetris_update']), 0)
        self.assertEqual(machine.call(machine.symbols['tetris_paint']), 0)
        self.assertNotIn(0x1f, machine.flags)

    def test_bottom_aligned_layout_and_full_labels(self):
        machine = GameMachine()
        machine.launch()
        state = machine.state()
        machine.write32(state + 4, 999999)
        machine.write32(state + 16, 999999)
        machine.write32(state + 12, 999999)
        machine.call(machine.symbols['tetris_paint'])

        def lit_upright(column, row):
            device_row = 31 - column
            device_column = (row - 2) & 127
            return bool(machine.frame[(device_row // 8) * 128 + device_column]
                        & (1 << (device_row % 8)))

        self.assertEqual([machine.frame[page * 128 + 61] for page in range(4)], [0xff] * 4)
        self.assertEqual([machine.frame[page * 128 + 124] for page in range(4)], [0xff] * 4)
        self.assertTrue(all(lit_upright(column, 126) for column in range(32)))
        self.assertTrue(all(lit_upright(column, 63) for column in range(32)))
        self.assertFalse(any(lit_upright(column, 127) for column in range(32)))
        self.assertTrue(all(lit_upright(0, row) and lit_upright(31, row) for row in range(63, 127)))
        self.assertFalse(any(lit_upright(column, 0) for column in range(32)))
        self.assertFalse(all(lit_upright(column, 1) for column in range(4, 28)))
        glyphs = {
            's': 0x79cf, 'c': 0x724f, 'o': 0x7b6f, 'r': 0x5aeb,
            'e': 0x72cf, 'l': 0x7249, 'i': 0x7497, 'n': 0x5ffd,
            'v': 0x2b6d,
        }
        for text, top in [('score', 1), ('lines', 15), ('level', 29)]:
            for index, character in enumerate(text):
                for vertical in range(5):
                    for horizontal in range(3):
                        expected = bool(glyphs[character] & (1 << (vertical * 3 + horizontal)))
                        self.assertEqual(lit_upright(4 + index * 4 + horizontal,
                                                     top + vertical), expected)
        for top in [1, 15, 29]:
            self.assertTrue(all(any(lit_upright(column, row) for column in range(4, 28))
                                for row in range(top, top + 5)))
        for top in [7, 21, 35]:
            self.assertTrue(all(any(lit_upright(column, row) for column in range(4, 28))
                                for row in range(top, top + 5)))
        for top, bottom in [(6, 7), (12, 15), (20, 21), (26, 29), (34, 35), (40, 50), (53, 63)]:
            self.assertFalse(any(lit_upright(column, row) for column in range(32)
                                 for row in range(top, bottom)))
        self.assertTrue(any(lit_upright(column, row) for column in range(32)
                            for row in range(45, 61)))

    def test_landing_ghost_is_outlined(self):
        machine = GameMachine()
        machine.launch()
        state = machine.state()
        data = machine.read32(state + 72)
        ghost_cells = []
        for index in range(200):
            if machine.read32(data + index * 4) == 1024:
                ghost_cells.append((index % 10, index // 10))
        self.assertTrue(ghost_cells)
        machine.call(machine.symbols['tetris_paint'])

        def lit_upright(column, row):
            device_row = 31 - column
            device_column = (row - 2) & 127
            return bool(machine.frame[(device_row // 8) * 128 + device_column]
                        & (1 << (device_row % 8)))

        for column, row in ghost_cells:
            left, top = 2 + column * 3, 65 + row * 3
            for vertical in range(3):
                for horizontal in range(3):
                    expected = vertical in [0, 2] or horizontal in [0, 2]
                    self.assertEqual(lit_upright(left + horizontal, top + vertical), expected)

    def test_hard_drop_commits_a_rendered_tetromino(self):
        machine = GameMachine()
        machine.launch()
        state = machine.state()
        piece_type = struct.unpack('<h', machine.cpu.mem_read(state + 24, 2))[0]
        machine.key = 0x40000008
        machine.call(machine.symbols['tetris_key'])
        data = machine.read32(state + 72)
        cells = []
        for row in range(20):
            for column in range(10):
                value = struct.unpack('<i', machine.cpu.mem_read(
                    data + (row * 10 + column) * 4, 4))[0]
                if value == piece_type:
                    cells.append((column, row))
        self.assertEqual(len(cells), 4)
        machine.call(machine.symbols['tetris_paint'])

        def lit_upright(column, row):
            device_row = 31 - column
            device_column = (row - 2) & 127
            return bool(machine.frame[(device_row // 8) * 128 + device_column]
                        & (1 << (device_row % 8)))

        for column, row in cells:
            left, top = 2 + column * 3, 65 + row * 3
            self.assertTrue(all(lit_upright(x, y) for x in range(left, left + 3)
                                for y in range(top, top + 3)))

    def test_next_piece_preview_has_four_full_blocks(self):
        machine = GameMachine()
        machine.launch()
        machine.call(machine.symbols['tetris_paint'])

        def lit_upright(column, row):
            device_row = 31 - column
            device_column = (row - 2) & 127
            return bool(machine.frame[(device_row // 8) * 128 + device_column]
                        & (1 << (device_row % 8)))

        self.assertEqual(sum(lit_upright(column, row)
                             for column in range(32) for row in range(50, 53)), 36)

    def test_all_seven_pieces_render_four_full_cells(self):
        machine = GameMachine()
        machine.launch()
        state = machine.state()
        data = machine.read32(state + 72)
        seen_types = set()
        for index in range(7):
            machine.cpu.reg_write(UC_ARM_REG_R0, 0)
            machine.call(machine.symbols['te_update'])
            piece_type = struct.unpack('<h', machine.cpu.mem_read(state + 24, 2))[0]
            self.assertNotIn(piece_type, seen_types)
            seen_types.add(piece_type)
            cells = []
            for row in range(20):
                for column in range(10):
                    value = struct.unpack('<i', machine.cpu.mem_read(
                        data + (row * 10 + column) * 4, 4))[0]
                    if value == piece_type:
                        cells.append((column, row))
            self.assertEqual(len(cells), 4, piece_type)
            machine.call(machine.symbols['tetris_paint'])

            def lit_upright(column, row):
                device_row = 31 - column
                device_column = (row - 2) & 127
                return bool(machine.frame[(device_row // 8) * 128 + device_column]
                            & (1 << (device_row % 8)))

            for column, row in cells:
                left, top = 2 + column * 3, 65 + row * 3
                self.assertTrue(all(lit_upright(x, y) for x in range(left, left + 3)
                                    for y in range(top, top + 3)), (piece_type, column, row))
            if index < 6:
                machine.call(machine.symbols['te_hard_drop'])
        self.assertEqual(seen_types, {8, 16, 32, 64, 128, 256, 512})

    def test_nav1_drop_nav2_right_confirm_left_and_restart(self):
        machine = GameMachine()
        machine.launch()
        state = machine.state()
        initial_type = struct.unpack('<h', machine.cpu.mem_read(state + 24, 2))[0]
        machine.key = 0x40000004
        machine.call(machine.symbols['tetris_key'])
        self.assertIn('te_rotate_right', machine.engine_calls)
        self.assertEqual(machine.cpu.mem_read(state + 26, 1)[0], 1)
        self.assertNotIn('te_move_down', machine.engine_calls)
        machine.key = 0x40000008
        machine.call(machine.symbols['tetris_key'])
        self.assertIn('te_hard_drop', machine.engine_calls)
        self.assertNotEqual(struct.unpack('<h', machine.cpu.mem_read(state + 24, 2))[0], initial_type)
        machine.key = 0x40000040
        machine.call(machine.symbols['tetris_key'])
        self.assertIn('te_rotate_left', machine.engine_calls)
        self.assertEqual(machine.cpu.mem_read(state + 26, 1)[0], 4)
        machine.key = 0x40000040
        machine.call(machine.symbols['tetris_key'])
        machine.key = 0x40000004
        machine.call(machine.symbols['tetris_key'])
        self.assertIn('te_hard_drop', machine.engine_calls)
        machine.write32(state, 1)
        machine.key = 0x40000040
        machine.call(machine.symbols['tetris_key'])
        self.assertEqual(machine.read32(state), 0)

    def test_loading_preserves_music_service(self):
        machine = GameMachine()
        machine.load_module(33)
        module = machine.image.modules[33]
        regions = [(module[kind + '_exec'], module[kind + '_len'])
                   for kind in ['code', 'data', 'bss']]
        snapshots = [machine.cpu.mem_read(address, length)
                     for address, length in regions]
        machine.write32(0x0300d454, 0x01000000)
        machine.launch()
        for (address, length), snapshot in zip(regions, snapshots):
            self.assertEqual(machine.cpu.mem_read(address, length), snapshot)
        self.assertFalse(machine.module_loads)

    def test_power_request_uses_stock_screen_off(self):
        machine = GameMachine()
        machine.launch()
        machine.write32(machine.state() + 4, 1234)
        self.assertNotIn(0x1f, machine.flags)
        machine.screen_toggle_on_key = True
        machine.call(machine.symbols['tetris_key'])
        self.assertIn(0x17, machine.flags)
        self.assertNotIn(0x1f, machine.flags)
        self.assertEqual(machine.cpu.mem_read(0x0300e6c4, 12), machine.original_callbacks)
        machine.call(0x030691c4)
        self.assertEqual(machine.screen_off_calls, 1)
        self.assertEqual(machine.cpu.mem_read(0x0300d7d4, 1), b'\1')
        self.assertIn(0x18, machine.flags)
        machine.cpu.mem_write(0x0300d7d4, b'\0')
        self.assertEqual(machine.cpu.mem_read(0x0300e6c4, 12), machine.original_callbacks)
        machine.write16(0x0300e708, 0)
        machine.flags.discard(0x17)
        machine.call(0x03079b1e)
        self.assertEqual(machine.read32(machine.state()), 0)
        self.assertEqual(machine.read32(machine.state() + 4), 0)

    def test_screen_off_stops_game_updates_and_draws(self):
        for callback in ['tetris_update', 'tetris_paint']:
            machine = GameMachine()
            machine.launch()
            state = machine.state()
            original_row = machine.read32(state + 32)
            machine.cpu.mem_write(0x0300d7d4, b'\1')
            machine.write32(0x0300d144, 1000)
            machine.call(machine.symbols[callback])
            self.assertEqual(machine.read32(state + 32), original_row)
            self.assertEqual(machine.display_bytes, [])
            self.assertEqual(machine.cpu.mem_read(0x0300e6c4, 12), machine.original_callbacks)

    def test_read_failure_leaves_menu_usable(self):
        machine = GameMachine()
        machine.fail_flash_read = True
        machine.launch()
        self.assertEqual(machine.cpu.mem_read(0x0300e6c4, 12), machine.original_callbacks)

    def test_gravity_and_shuffle_route(self):
        machine = GameMachine()
        machine.launch()
        state = machine.state()
        initial = machine.read32(state + 32)
        for tick in range(1, 71):
            machine.write32(0x0300d144, tick * 2)
            machine.call(machine.symbols['tetris_update'])
        self.assertGreater(machine.read32(state + 32), initial)
        machine.call(machine.symbols['tetris_exit'])
        machine.write16(0x0300e708, 1)
        machine.write16(0x0300d192, 2000)
        machine.write16(0x0300d194, 0)
        machine.call(0x03079b1e)
        self.assertEqual(machine.windows, [2])
        self.assertEqual(machine.cpu.mem_read(0x0300d1d3, 1), b'\1')
        self.assertEqual(struct.unpack('<H', machine.cpu.mem_read(0x0300e6e6, 2))[0], 0x82)

    def test_artist_album_play_all_shuffles_but_song_starts_sequential(self):
        for level, expected_mode, expected_order in [(1, 3, 1), (2, 2, 0)]:
            machine = GameMachine()
            machine.load_module(23)
            machine.write16(0x0300d482, 3)
            machine.write16(0x0300ea46, level)
            machine.write16(0x0300e80c + level * 2, 0x600)
            machine.cpu.mem_write(0x0300d1d1, b'\xff')
            machine.cpu.mem_write(0x0300d1d3, b'\x01')
            machine.call(0x03079e40)
            self.assertEqual(machine.cpu.mem_read(0x0300d1d1, 1)[0] & 3,
                             expected_mode, level)
            self.assertEqual(machine.cpu.mem_read(0x0300d1d3, 1)[0],
                             expected_order, level)

    def test_shuffle_all_without_songs_returns_to_main_menu(self):
        machine = GameMachine()
        machine.write16(0x0300e708, 1)
        machine.write16(0x0300d192, 0)
        machine.write16(0x0300d194, 2000)
        machine.call(0x03079b1e)
        self.assertEqual(machine.windows, [])
        self.assertEqual(machine.module_loads, [])
        self.assertEqual(machine.cpu.mem_read(0x0300e708, 2), b'\1\0')
        self.assertEqual(struct.unpack('<H', machine.cpu.mem_read(0x0300e6e6, 2))[0], 0x7c)
        self.assertIn(0x32, machine.flags)


if __name__ == '__main__':
    unittest.main()