#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include "fw.h"
#include "tengine.h"

#define MENU ((u32 *)0x0300e6bc)
#define get_key FW(0x03063242, u32, void)
#define post FW(0x0306b040, void, u32)
#define clear FW(0x0306b082, void, u32)
#define flag FW(0x0306b0a0, u32, u32)
#define present FW(0x03079010, void, int, int, int, int, const void *)

static u32 saved_callbacks[3];
static u32 last_update, last_paint, frame_time, random_state;
static u32 arena[400], arena_used;
static u8 framebuffer[512];
static u32 saved_screen_inhibit;

void tetris_exit(void);

static int leave_for_screen_off(void)
{
    if (!flag(0x17) && !*(volatile u8 *)0x0300d7d4)
        return 0;
    tetris_exit();
    return 1;
}

void *malloc(size_t size)
{
    u32 words = (size + 3) / 4;
    if (words > 400 - arena_used)
        return NULL;
    void *result = arena + arena_used;
    arena_used += words;
    return result;
}

void free(void *pointer)
{
    (void)pointer;
}

void srand(unsigned seed)
{
    random_state = seed ? seed : 1;
}

int rand(void)
{
    random_state ^= random_state << 13;
    random_state ^= random_state >> 17;
    random_state ^= random_state << 5;
    return (int)(random_state & 0x7fffffff);
}

static void pixel(int column, int row)
{
    if ((unsigned)column < 128 && (unsigned)row < 32)
        framebuffer[(row >> 3) * 128 + column] |= 1u << (row & 7);
}

static void upright_pixel(int column, int row)
{
    pixel((row + 126) & 127, 31 - column);
}

static void block_pixels(int left, int top, int outline)
{
    for (int vertical = 0; vertical < 3; ++vertical)
        for (int horizontal = 0; horizontal < 3; ++horizontal)
            if (!outline || vertical == 0 || vertical == 2 || horizontal == 0 || horizontal == 2)
                upright_pixel(left + horizontal, top + vertical);
}

static void block(int column, int row, int outline)
{
    block_pixels(2 + column * 3, 65 + row * 3, outline);
}

static void __attribute__((unused)) tetromino(Piece piece, int outline)
{
    PieceOffsets offsets = te_get_piece_offsets(piece.type, piece.orientation);
    int columns[4] = {piece.x, piece.x + offsets.ox_1, piece.x + offsets.ox_2,
                      piece.x + offsets.ox_3};
    int rows[4] = {piece.y, piece.y + offsets.oy_1, piece.y + offsets.oy_2,
                   piece.y + offsets.oy_3};
    for (int index = 0; index < 4; ++index)
        block(columns[index], rows[index], outline);
}

static const u16 digits[10] = {
    0x7b6f, 0x2492, 0x73e7, 0x79e7, 0x49ed,
    0x79cf, 0x7bcf, 0x4927, 0x7bef, 0x79ef
};

static void number_at(int column, int row, u32 value)
{
    value %= 1000000;
    u32 divisor = 100000;
    int started = 0;
    while (divisor) {
        u32 digit = value / divisor % 10;
        if (digit || started || divisor == 1) {
            u16 glyph = digits[digit];
            for (int vertical = 0; vertical < 5; ++vertical)
                for (int horizontal = 0; horizontal < 3; ++horizontal)
                    if (glyph & (1u << (vertical * 3 + horizontal)))
                        upright_pixel(column + horizontal, row + vertical);
            column += 4;
            started = 1;
        }
        divisor /= 10;
    }
}

static void __attribute__((unused)) number(int row, u32 value)
{
    value %= 1000000;
    int width = 3;
    for (u32 remaining = value; remaining >= 10; remaining /= 10)
        width += 4;
    number_at((32 - width) / 2, row, value);
}

static void __attribute__((unused)) type_marker(int row, PieceType type)
{
    for (int index = 0; index < 7; ++index) {
        int left = 2 + index * 4;
        int selected = type == (PT_I << index);
        for (int vertical = 0; vertical < 3; ++vertical)
            for (int horizontal = 0; horizontal < 3; ++horizontal)
                if (selected || vertical == 0 || vertical == 2 || horizontal == 0 || horizontal == 2)
                    upright_pixel(left + horizontal, row + vertical);
    }
}

static void __attribute__((unused)) label(int row, const char *text)
{
    int column = 4;
    while (*text) {
        u16 bits = 0;
        switch (*text++) {
        case 's': bits = 0x79cf; break;
        case 'c': bits = 0x724f; break;
        case 'o': bits = 0x7b6f; break;
        case 'r': bits = 0x5aeb; break;
        case 'e': bits = 0x72cf; break;
        case 'l': bits = 0x7249; break;
        case 'i': bits = 0x7497; break;
        case 'n': bits = 0x5ffd; break;
        case 'v': bits = 0x2b6d; break;
        case 'x': bits = 0x5aad; break;
        case 't': bits = 0x2497; break;
        }
        for (int vertical = 0; vertical < 5; ++vertical)
            for (int horizontal = 0; horizontal < 3; ++horizontal)
                if (bits & (1u << (vertical * 3 + horizontal)))
                    upright_pixel(column + horizontal, row + vertical);
        column += 4;
    }
}

static void restart(void)
{
    arena_used = 0;
    te_init_system();
    te_update(0);
    frame_time = 0;
    last_update = fw_ticks();
    post(0x32);
}

u32 tetris_paint(void)
{
    if (leave_for_screen_off())
        return 1;
    memset(framebuffer, 0, sizeof framebuffer);
#ifdef TETRIS_ENGINE_DIAGNOSTIC
    for (int row = 64; row < 128; ++row) {
        upright_pixel(0, row);
        upright_pixel(31, row);
    }
    for (int column = 0; column < 32; ++column) {
        if ((column & 1) == 0)
            upright_pixel(column, 64);
        upright_pixel(column, 127);
    }
    block(0, 2, 0);
    block(1, 2, 0);
    block(1, 3, 0);
    block(2, 3, 0);
    Piece engine_piece = {PT_Z, PO_ZERO, 6, 2};
    tetromino(engine_piece, 0);
    present(0, 0, 128, 31, framebuffer);
    clear(0x32);
    clear(0x33);
    return 0;
#elif defined(TETRIS_COMMIT_DIAGNOSTIC)
    for (int row = 64; row < 128; ++row) {
        upright_pixel(0, row);
        upright_pixel(31, row);
    }
    for (int column = 0; column < 32; ++column) {
        if ((column & 1) == 0)
            upright_pixel(column, 64);
        upright_pixel(column, 127);
    }
    block(0, 2, 0);
    block(1, 2, 0);
    block(1, 3, 0);
    block(2, 3, 0);
    TState *state = te_get_state();
    Board *board = &state->committed_board;
    for (int row = 0; row < HEIGHT; ++row)
        for (int column = 0; column < WIDTH; ++column)
            if (te_get_board_xy(board, column, row) >= 0)
                block(column, row, 0);
    present(0, 0, 128, 31, framebuffer);
    clear(0x32);
    clear(0x33);
    return 0;
#elif defined(TETRIS_LIVE_DIAGNOSTIC)
    for (int row = 64; row < 128; ++row) {
        upright_pixel(0, row);
        upright_pixel(31, row);
    }
    for (int column = 0; column < 32; ++column) {
        if ((column & 1) == 0)
            upright_pixel(column, 64);
        upright_pixel(column, 127);
    }
    block(0, 2, 0);
    block(1, 2, 0);
    block(1, 3, 0);
    block(2, 3, 0);
    TState *state = te_get_state();
    tetromino(state->cur_piece, 0);
    tetromino(state->ghost_piece, 1);
    present(0, 0, 128, 31, framebuffer);
    clear(0x32);
    clear(0x33);
    return 0;
#elif defined(TETRIS_BAG_DIAGNOSTIC) || defined(TETRIS_RANDOM_DIAGNOSTIC) || defined(TETRIS_PREVIEW_DIAGNOSTIC) || defined(TETRIS_RAW_DIAGNOSTIC)
    for (int row = 64; row < 128; ++row) {
        upright_pixel(0, row);
        upright_pixel(31, row);
    }
    for (int column = 0; column < 32; ++column) {
        if ((column & 1) == 0)
            upright_pixel(column, 64);
        upright_pixel(column, 127);
    }
    block(0, 2, 0);
    block(1, 2, 0);
    block(1, 3, 0);
    block(2, 3, 0);
    TState *state = te_get_state();
    Board *board = &state->committed_board;
    for (int row = 0; row < HEIGHT; ++row)
        for (int column = 0; column < WIDTH; ++column)
            if (te_get_board_xy(board, column, row) >= 0)
                block(column, row, 0);
    tetromino(state->cur_piece, 0);
    tetromino(state->ghost_piece, 1);
#ifdef TETRIS_RAW_DIAGNOSTIC
    label(1, "live");
    number(6, state->cur_piece.type);
#elif defined(TETRIS_PREVIEW_DIAGNOSTIC)
    label(1, "live");
    type_marker(6, state->cur_piece.type);
#else
    number(1, state->cur_piece.type);
#endif
#ifdef TETRIS_PREVIEW_DIAGNOSTIC
    int length;
    PieceType next = te_get_next_piece_buf(&length)[0];
    PieceOffsets offsets = te_get_piece_offsets(next, PO_ZERO);
    int columns[4] = {0, offsets.ox_1, offsets.ox_2, offsets.ox_3};
    int rows[4] = {0, offsets.oy_1, offsets.oy_2, offsets.oy_3};
    label(12, "next");
#ifdef TETRIS_RAW_DIAGNOSTIC
    number(17, next);
#else
    type_marker(17, next);
#endif
    for (int index = 0; index < 4; ++index)
        block_pixels(14 + columns[index] * 4, 50 + rows[index] * 4, 0);
#endif
    present(0, 0, 128, 31, framebuffer);
    clear(0x32);
    clear(0x33);
    return 0;
#elif defined(TETRIS_TYPE_DUMP_DIAGNOSTIC)
    uint16_t values[21];
    te_debug_type_values(values);
    for (int index = 0; index < 21; ++index) {
        int row = index * 6;
        number_at(0, row, index);
        number_at(8, row, values[index]);
    }
    present(0, 0, 128, 31, framebuffer);
    clear(0x32);
    clear(0x33);
    return 0;
#elif defined(TETRIS_DISPLAY_DIAGNOSTIC)
    for (int row = 64; row < 128; ++row) {
        upright_pixel(0, row);
        upright_pixel(31, row);
    }
    for (int column = 0; column < 32; ++column) {
        if ((column & 1) == 0)
            upright_pixel(column, 64);
        upright_pixel(column, 127);
    }
    block_pixels(8, 72, 0);
    block_pixels(11, 72, 0);
    block_pixels(11, 75, 0);
    block_pixels(14, 75, 0);
    block_pixels(20, 90, 1);
    block_pixels(17, 93, 1);
    block_pixels(20, 93, 1);
    block_pixels(23, 93, 1);
    present(0, 0, 128, 31, framebuffer);
    clear(0x32);
    clear(0x33);
    return 0;
#else
    for (int row = 63; row < 127; ++row) {
        upright_pixel(0, row);
        upright_pixel(31, row);
    }
    for (int column = 0; column < 32; ++column) {
        upright_pixel(column, 63);
        upright_pixel(column, 126);
    }
    TState *state = te_get_state();
    Board *board = &state->committed_board;
    for (int row = 0; row < HEIGHT; ++row)
        for (int column = 0; column < WIDTH; ++column) {
            int cell = te_get_board_xy(board, column, row);
            if (cell >= 0)
                block(column, row, 0);
        }
    tetromino(state->ghost_piece, 1);
    tetromino(state->cur_piece, 0);
    label(1, "score");
    number(7, te_get_score());
    label(15, "lines");
    number(21, te_get_state()->num_lines_cleared);
    label(29, "level");
    number(35, te_get_level());
    int length;
    PieceType next = te_get_next_piece_buf(&length)[0];
#ifdef TETRIS_GAME_TRACE
    label(41, "live");
    number(46, state->cur_piece.type);
    label(52, "next");
    number(57, next);
#else
    PieceOffsets offsets = te_get_piece_offsets(next, PO_ZERO);
    int columns[4] = {0, offsets.ox_1, offsets.ox_2, offsets.ox_3};
    int rows[4] = {0, offsets.oy_1, offsets.oy_2, offsets.oy_3};
    for (int index = 0; index < 4; ++index)
        block_pixels(14 + columns[index] * 4, 50 + rows[index] * 4, 0);
#endif
    if (te_is_game_over()) {
        for (int row = 8; row < 24; ++row)
            for (int column = 85; column < 109; ++column)
                framebuffer[(row >> 3) * 128 + column] &= ~(1u << (row & 7));
        for (int row = 90; row < 100; ++row) {
            if (te_is_game_over()) {
                upright_pixel(11 + row - 90, row);
                upright_pixel(20 - row + 90, row);
            }
        }
    }
    present(0, 0, 128, 31, framebuffer);
    clear(0x32);
    clear(0x33);
    return 0;
#endif
}

u32 tetris_update(void)
{
    if (leave_for_screen_off())
        return 1;
    u32 now = fw_ticks(), elapsed = now - last_update;
    last_update = now;
    if (!te_is_game_over()) {
        u32 level = te_get_level();
        te_get_state()->gravity_fr = level < 12 ? 65 - level * 5 : 5;
        frame_time += (elapsed > 10 ? 10 : elapsed) * 60;
        while (frame_time >= 100) {
            te_update(1);
            frame_time -= 100;
        }
    }
    if (now - last_paint >= 3) {
        last_paint = now;
        post(0x32);
    }
    return 0;
}

void tetris_exit(void)
{
    for (int index = 0; index < 3; ++index)
        MENU[index + 2] = saved_callbacks[index];
    *(volatile u16 *)0x0300e708 = 0;
    if (saved_screen_inhibit)
        post(0x1f);
    post(0x32);
    post(0x33);
}

u32 tetris_key(void)
{
    u32 key = get_key();
    if (leave_for_screen_off())
        return 1;
    if (key == 0x20000040) {
        tetris_exit();
        return 1;
    }
    if (key == 0)
        return 0;
    if (te_is_game_over()) {
        if (key == 0x40000040)
            restart();
    } else {
        if (key == 0x40008000)
            te_move_right();
        else if (key == 0x40004000)
            te_move_left();
        else if (key == 0x40000004 || key == 0x20000004 || key == 0x50000004)
            te_rotate_right();
        else if (key == 0x40000008)
            te_hard_drop();
        else if (key == 0x40000040)
            te_rotate_left();
        te_update(0);
    }
    if (key)
        post(0x32);
    return 0;
}

u32 tetris_enter(void)
{
    srand(fw_ticks() ^ *(volatile u32 *)0xe000e018);
    saved_screen_inhibit = flag(0x1f);
    clear(0x1f);
    clear(0x17);
    for (int index = 0; index < 3; ++index)
        saved_callbacks[index] = MENU[index + 2];
    MENU[2] = (u32)tetris_update;
    MENU[3] = (u32)tetris_key;
    MENU[4] = (u32)tetris_paint;
    restart();
#ifdef TETRIS_COMMIT_DIAGNOSTIC
    TState *state = te_get_state();
    state->cur_piece = (Piece){PT_Z, PO_ZERO, 4, 2};
    te_update(0);
    te_hard_drop();
    te_update(0);
#endif
#ifdef TETRIS_LIVE_DIAGNOSTIC
    TState *state = te_get_state();
    state->cur_piece = (Piece){PT_Z, PO_ZERO, 6, 2};
    te_update(0);
#endif
    return 1;
}