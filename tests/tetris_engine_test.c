#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "tengine.h"

static void check_board(void)
{
    Board *board = te_get_committed_board();
    for (int row = 0; row < HEIGHT; ++row)
        for (int column = 0; column < WIDTH; ++column) {
            int value = te_get_board_xy(board, column, row);
            assert(value == -1 || value == PT_I || value == PT_O ||
                   value == PT_T || value == PT_S || value == PT_Z ||
                   value == PT_J || value == PT_L);
        }
}

int main(void)
{
    for (unsigned seed = 1; seed <= 64; ++seed) {
        srand(seed);
        te_init_system();
        int seen = te_get_current_piece().type;
        for (int index = 1; index < 7; ++index) {
            int type = te_get_next_piece().type;
            assert(!(seen & type));
            seen |= type;
        }
        assert(seen == (PT_I | PT_O | PT_T | PT_S | PT_Z | PT_J | PT_L));
        int preview_length = 0;
        PieceType *preview = te_get_next_piece_buf(&preview_length);
        assert(preview_length == 5);
        for (int index = 0; index < preview_length; ++index)
            assert(preview[index] == PT_I || preview[index] == PT_O ||
                   preview[index] == PT_T || preview[index] == PT_S ||
                   preview[index] == PT_Z || preview[index] == PT_J ||
                   preview[index] == PT_L);
        te_destroy_system();
    }

    srand(7);
    te_init_system();
    Piece initial = te_get_current_piece();
    for (int frame = 0; frame < 100; ++frame)
        te_update(0);
    assert(te_get_current_piece().y == initial.y);
    for (int frame = 0; frame < 61; ++frame)
        te_update(1);
    assert(te_get_current_piece().y > initial.y);
    te_destroy_system();

    te_init_system();
    TState *invalid_state = te_get_state();
    PieceType expected_current = invalid_state->cur_piece.type;
    PieceType expected_next = invalid_state->next_piece_buf[0];
    invalid_state->next_piece_buf[0] = (PieceType)61440;
    int next_length = 0;
    PieceType *next_pieces = te_get_next_piece_buf(&next_length);
    assert(next_length == 5);
    assert(next_pieces[0] == expected_next);
    invalid_state->cur_piece = (Piece){(PieceType)8198, PO_ZERO, 4, 2};
    te_update(0);
    assert(invalid_state->cur_piece.type == expected_current);
    Board *invalid_board = te_get_board();
    int current_cells = 0;
    for (int index = 0; index < WIDTH * HEIGHT; ++index)
        current_cells += invalid_board->data[index] == expected_current;
    assert(current_cells == 4);
    te_hard_drop();
    Board *invalid_committed = te_get_committed_board();
    int committed_cells = 0;
    for (int index = 0; index < WIDTH * HEIGHT; ++index)
        committed_cells += invalid_committed->data[index] == expected_current;
    assert(committed_cells == 4);
    te_destroy_system();

    te_init_system();
    Board *board = te_get_committed_board();
    TState *state = te_get_state();
    Piece line_piece;
    do {
        line_piece = te_get_next_piece();
    } while (line_piece.type != PT_I);
    state->cur_piece = line_piece;
    state->cur_piece.orientation = PO_ZERO;
    state->cur_piece.x = 4;
    state->cur_piece.y = 0;
    PieceOffsets offsets = te_get_piece_offsets(PT_I, PO_ZERO);
    int columns[4] = {4, 4 + offsets.ox_1, 4 + offsets.ox_2, 4 + offsets.ox_3};
    for (int column = 0; column < WIDTH; ++column)
        board->data[(HEIGHT - 1) * WIDTH + column] = PT_J;
    for (int index = 0; index < 4; ++index)
        board->data[(HEIGHT - 1) * WIDTH + columns[index]] = -1;
    te_update(0);
    te_hard_drop();
    assert(state->num_lines_cleared == 1);
    assert(state->score == 100);
    check_board();
    te_destroy_system();

    for (unsigned seed = 1; seed <= 32; ++seed) {
        srand(seed);
        te_init_system();
        for (int step = 0; step < 300 && !te_is_game_over(); ++step) {
            if (rand() & 1)
                te_move_left();
            else
                te_move_right();
            te_rotate_right();
            te_update(1);
            if (step % 4 == 0)
                te_hard_drop();
            check_board();
        }
        te_destroy_system();
    }

    te_init_system();
    te_get_state()->cur_piece.y = -1;
    te_commit();
    assert(te_is_game_over());
    te_destroy_system();
    puts("PASS: piece bags, gravity, line clearing, movement, top-out memory safety");
    return 0;
}