"""Lightweight opening book helpers for fast king-side castling plans."""
from __future__ import annotations

from typing import Dict, List, Optional

import chess

from engine.board import Board


OPENING_BOOK_MAX_FULLMOVE = 14
OPENING_BOOK_CASTLE_DEADLINE_MOVES = 7

# Explicit Italian repertoire provided by user. Each entry is a full line in UCI.
WHITE_ITALIAN_LINES: List[List[str]] = [
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "c6d4", "f3d4", "e5d4", "e1g1"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6", "d2d4", "e5d4", "e1g1"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "d2d3", "g8f6", "e1g1"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "c2c3", "g8f6", "d2d4", "e5d4", "e1g1"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "d7d6", "d2d3", "g8f6", "e1g1"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8e7", "d2d3", "g8f6", "e1g1"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "b2b4", "c5b4", "c2c3", "b4a5", "e1g1"],
    # Caro-Kann branch requested by user: 1.e4 c6 2.Nf3 d5 3.d4 dxe4
    ["e2e4", "c7c6", "g1f3", "d7d5", "d2d4", "d5e4", "f3e5", "g8f6", "b1c3", "e7e6", "f1e2", "f8e7", "e1g1"],
    # Caro-Kann with ...e6 setup.
    ["e2e4", "c7c6", "g1f3", "d7d5", "d2d4", "e7e6", "b1c3", "g8f6", "f1d3", "f8e7", "e1g1"],
    ["e2e4", "c7c6", "g1f3", "d7d5", "d2d4", "d5e4", "f3e5", "e7e6", "b1c3", "g8f6", "f1e2", "f8e7", "e1g1"],
    # Caro/Pirc hybrid line requested by user: avoid castling into ...dxc4 tactic.
    ["e2e4", "c7c6", "g1f3", "g7g6", "f1c4", "d7d5", "c4b3", "d5e4", "f3g5", "e7e6", "e1g1"],
]

BLACK_ITALIAN_LINES: List[List[str]] = [
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "c2c3", "g8f6", "d2d4", "e5d4", "e1g1", "e8g8"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "d2d3", "g8f6", "e1g1", "e8g8"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6", "d2d4", "e5d4", "e1g1", "f6e4", "f1e1", "d7d5", "c4d5", "e8g8"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6", "d2d4", "e5d4", "e1g1", "f6d5", "e4d5", "d8d5", "f1e1", "f8e7", "e8g8"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "d7d6", "d2d3", "g8f6", "e1g1", "f8e7", "f1e1", "e8g8"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8e7", "d2d3", "g8f6", "e1g1", "e8g8"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "b2b4", "c5b4", "c2c3", "b4a5", "e1g1", "g8f6", "d2d4", "e8g8"],
    # Tactical safeguards for common Italian motifs where early ...O-O can drop a piece.
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "c2c3", "g8f6", "d2d4", "e5d4", "e4e5", "d7d5"],
    ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "c2c3", "g8f6", "d2d4", "e5d4", "c3d4", "c5b4"],
]

PIECE_VALUES: Dict[chess.PieceType, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20_000,
}


def _captured_piece(py_board: chess.Board, move: chess.Move) -> Optional[chess.Piece]:
    if not py_board.is_capture(move):
        return None
    if py_board.is_en_passant(move):
        capture_square = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        return py_board.piece_at(capture_square)
    return py_board.piece_at(move.to_square)


def _is_non_losing_move(py_board: chess.Board, move: chess.Move) -> bool:
    mover = py_board.piece_at(move.from_square)
    if mover is None:
        return False

    mover_value = PIECE_VALUES.get(mover.piece_type, 0)
    captured = _captured_piece(py_board, move)
    captured_value = PIECE_VALUES.get(captured.piece_type, 0) if captured is not None else 0

    after = py_board.copy(stack=False)
    after.push(move)

    side = not after.turn
    opponent = after.turn

    if after.is_attacked_by(opponent, move.to_square):
        defenders = [
            PIECE_VALUES.get(after.piece_at(sq).piece_type, 0)
            for sq in after.attackers(side, move.to_square)
            if after.piece_at(sq) is not None
        ]
        attackers = [
            PIECE_VALUES.get(after.piece_at(sq).piece_type, 0)
            for sq in after.attackers(opponent, move.to_square)
            if after.piece_at(sq) is not None
        ]
        if not defenders:
            return captured_value >= mover_value
        if attackers and min(attackers) <= min(defenders) and captured_value < mover_value:
            return False

    return True


def _is_castled(py_board: chess.Board, color: chess.Color) -> bool:
    king_sq = py_board.king(color)
    if king_sq is None:
        return False
    if color == chess.WHITE:
        return king_sq in (chess.G1, chess.C1)
    return king_sq in (chess.G8, chess.C8)


def _side_plies_played(py_board: chess.Board, color: chess.Color) -> int:
    if color == chess.WHITE:
        return (py_board.fullmove_number - 1) + (1 if py_board.turn == chess.BLACK else 0)
    return (py_board.fullmove_number - 1) + (1 if py_board.turn == chess.WHITE else 0)


def _kingside_castle_uci(color: chess.Color) -> str:
    return "e1g1" if color == chess.WHITE else "e8g8"


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _recent_enemy_capture_square(py_board: chess.Board, side_to_move: chess.Color) -> Optional[int]:
    if not py_board.move_stack:
        return None
    last_move = py_board.move_stack[-1]
    prev = py_board.copy(stack=True)
    prev.pop()
    if not prev.is_capture(last_move):
        return None

    mover = prev.piece_at(last_move.from_square)
    if mover is None:
        return None
    if mover.color == side_to_move:
        return None
    return last_move.to_square


def _recapture_candidates_uci(legal_moves: List[chess.Move], target_square: int) -> List[str]:
    # Any legal capture that lands on the just-captured square is an immediate recapture.
    return [move.uci() for move in legal_moves if move.to_square == target_square and move.promotion is None]


def _next_repertoire_move(py_board: chess.Board, color: chess.Color) -> Optional[str]:
    history = [move.uci() for move in py_board.move_stack]
    repertoire = WHITE_ITALIAN_LINES if color == chess.WHITE else BLACK_ITALIAN_LINES
    history_len = len(history)

    for line in repertoire:
        if history_len >= len(line):
            continue
        if line[:history_len] == history:
            next_uci = line[history_len]
            # Extra safety: ensure parity matches side to move.
            if (history_len % 2 == 0 and color == chess.WHITE) or (history_len % 2 == 1 and color == chess.BLACK):
                return next_uci
    return None


def _pick_first_safe_legal(move_by_uci: Dict[str, chess.Move], py_board: chess.Board, candidates: List[str]) -> Optional[chess.Move]:
    for uci in candidates:
        move = move_by_uci.get(uci)
        if move is None:
            continue
        if _is_non_losing_move(py_board, move):
            return move
    return None


def _white_italian_candidates(py_board: chess.Board) -> List[str]:
    # Stage 1: enforce the classical first move.
    white_e4 = py_board.piece_at(chess.E4)
    if white_e4 is None or white_e4.color != chess.WHITE or white_e4.piece_type != chess.PAWN:
        return ["e2e4"]

    # Stage 2: develop king side pieces.
    white_nf3 = py_board.piece_at(chess.F3)
    if white_nf3 is None or white_nf3.color != chess.WHITE or white_nf3.piece_type != chess.KNIGHT:
        return ["g1f3"]

    white_bc4 = py_board.piece_at(chess.C4)
    if white_bc4 is None or white_bc4.color != chess.WHITE or white_bc4.piece_type != chess.BISHOP:
        return ["f1c4"]

    # Stage 3: support center and then castle.
    candidates: List[str] = ["d2d3", "c2c3", "e1g1"]
    return candidates


def _black_italian_candidates(py_board: chess.Board) -> List[str]:
    # Stage 1: answer 1.e4 with ...e5.
    white_e4 = py_board.piece_at(chess.E4)
    black_e5 = py_board.piece_at(chess.E5)
    if (
        white_e4 is not None
        and white_e4.color == chess.WHITE
        and white_e4.piece_type == chess.PAWN
        and (black_e5 is None or black_e5.color != chess.BLACK or black_e5.piece_type != chess.PAWN)
    ):
        return ["e7e5"]

    # Stage 2: develop ...Nc6 after 2.Nf3 whenever possible.
    black_nc6 = py_board.piece_at(chess.C6)
    if black_nc6 is None or black_nc6.color != chess.BLACK or black_nc6.piece_type != chess.KNIGHT:
        return ["b8c6", "g8f6"]

    # Stage 3: choose common Italian branch and keep king safe.
    white_ng5 = py_board.piece_at(chess.G5)
    white_d4 = py_board.piece_at(chess.D4)
    white_c3 = py_board.piece_at(chess.C3)
    white_d3 = py_board.piece_at(chess.D3)

    # If White pushes d4 (Scotch/Italian gambit ideas), simplify center first.
    if white_d4 is not None and white_d4.color == chess.WHITE and white_d4.piece_type == chess.PAWN:
        return ["e5d4", "f8c5", "g8f6", "e8g8"]

    # Two Knights sharp idea (Ng5): play solid setup before castling.
    if white_ng5 is not None and white_ng5.color == chess.WHITE and white_ng5.piece_type == chess.KNIGHT:
        return ["f8e7", "d7d6", "h7h6", "g8f6", "e8g8"]

    # Giuoco Piano / Giuoco Pianissimo style plans.
    if (white_c3 is not None and white_c3.color == chess.WHITE and white_c3.piece_type == chess.PAWN) or (
        white_d3 is not None and white_d3.color == chess.WHITE and white_d3.piece_type == chess.PAWN
    ):
        return ["f8c5", "g8f6", "d7d6", "e8g8"]

    return ["f8c5", "g8f6", "d7d6", "e8g8", "f8e7"]


def _white_universal_castling_candidates() -> List[str]:
    # Broad, variation-agnostic setup to clear g1/f1 quickly.
    return [
        "e1g1",
        "g1f3",
        "e2e4",
        "e2e3",
        "d2d4",
        "d2d3",
        "f1e2",
        "f1d3",
        "f1c4",
        "f1b5",
        "g2g3",
        "f1g2",
        "b1c3",
        "c2c3",
        "h2h3",
        "a2a3",
    ]


def _black_universal_castling_candidates() -> List[str]:
    # Broad, variation-agnostic setup to clear g8/f8 quickly.
    return [
        "e8g8",
        "g8f6",
        "e7e5",
        "e7e6",
        "d7d5",
        "d7d6",
        "f8e7",
        "f8d6",
        "f8c5",
        "f8b4",
        "g7g6",
        "f8g7",
        "b8c6",
        "c7c6",
        "h7h6",
        "a7a6",
    ]


def _black_urgent_tactical_candidates(py_board: chess.Board) -> List[str]:
    candidates: List[str] = []

    # If white expands with a4 while our bishop is on b6, play ...a6 to preserve Ba7 retreat.
    white_a4 = py_board.piece_at(chess.A4)
    black_b6 = py_board.piece_at(chess.B6)
    black_a6 = py_board.piece_at(chess.A6)
    if (
        white_a4 is not None
        and white_a4.color == chess.WHITE
        and white_a4.piece_type == chess.PAWN
        and black_b6 is not None
        and black_b6.color == chess.BLACK
        and black_b6.piece_type == chess.BISHOP
        and (black_a6 is None or black_a6.color != chess.BLACK or black_a6.piece_type != chess.PAWN)
    ):
        candidates.extend(["a7a6", "h7h6"])

    white_e5 = py_board.piece_at(chess.E5)
    black_f6 = py_board.piece_at(chess.F6)
    if (
        white_e5 is not None
        and white_e5.color == chess.WHITE
        and white_e5.piece_type == chess.PAWN
        and black_f6 is not None
        and black_f6.color == chess.BLACK
        and black_f6.piece_type == chess.KNIGHT
    ):
        # Avoid dropping Nf6 to exf6 by challenging the center first.
        candidates.extend(["d7d5", "d7d6", "f8e7", "h7h6"])

    white_d4 = py_board.piece_at(chess.D4)
    black_c5 = py_board.piece_at(chess.C5)
    if (
        white_d4 is not None
        and white_d4.color == chess.WHITE
        and white_d4.piece_type == chess.PAWN
        and black_c5 is not None
        and black_c5.color == chess.BLACK
        and black_c5.piece_type == chess.BISHOP
    ):
        # Avoid dropping Bc5 to dxc5 by retreating/repositioning bishop first.
        candidates.extend(["c5b4", "c5e7", "c5d6", "c5b6", "d7d6"])

    return _dedupe_keep_order(candidates)


def _white_urgent_tactical_candidates(py_board: chess.Board) -> List[str]:
    candidates: List[str] = []

    # If bishop is on c4 and black has d5, save bishop before castling to avoid ...dxc4.
    white_c4 = py_board.piece_at(chess.C4)
    black_d5 = py_board.piece_at(chess.D5)
    if (
        white_c4 is not None
        and white_c4.color == chess.WHITE
        and white_c4.piece_type == chess.BISHOP
        and black_d5 is not None
        and black_d5.color == chess.BLACK
        and black_d5.piece_type == chess.PAWN
    ):
        candidates.extend(["c4b3", "c4e2", "c4d3", "c4b5", "e4d5"])

    # Caro-Kann: after ...dxe4, react immediately instead of drifting.
    white_d4 = py_board.piece_at(chess.D4)
    black_e4 = py_board.piece_at(chess.E4)
    white_f3 = py_board.piece_at(chess.F3)
    black_c6 = py_board.piece_at(chess.C6)
    black_d5 = py_board.piece_at(chess.D5)
    if (
        white_d4 is not None
        and white_d4.color == chess.WHITE
        and white_d4.piece_type == chess.PAWN
        and black_e4 is not None
        and black_e4.color == chess.BLACK
        and black_e4.piece_type == chess.PAWN
        and white_f3 is not None
        and white_f3.color == chess.WHITE
        and white_f3.piece_type == chess.KNIGHT
        and black_c6 is not None
        and black_c6.color == chess.BLACK
        and black_c6.piece_type == chess.PAWN
        and (black_d5 is None or black_d5.color != chess.BLACK or black_d5.piece_type != chess.PAWN)
    ):
        candidates.extend(["f3e5", "f3g5", "b1c3", "f1e2", "e1g1"])

    # Caro-Kann structure with ...e6: keep smooth development and fast castling.
    black_e6 = py_board.piece_at(chess.E6)
    black_d5 = py_board.piece_at(chess.D5)
    black_c6 = py_board.piece_at(chess.C6)
    white_e4 = py_board.piece_at(chess.E4)
    if (
        white_d4 is not None
        and white_d4.color == chess.WHITE
        and white_d4.piece_type == chess.PAWN
        and white_e4 is not None
        and white_e4.color == chess.WHITE
        and white_e4.piece_type == chess.PAWN
        and white_f3 is not None
        and white_f3.color == chess.WHITE
        and white_f3.piece_type == chess.KNIGHT
        and black_c6 is not None
        and black_c6.color == chess.BLACK
        and black_c6.piece_type == chess.PAWN
        and black_d5 is not None
        and black_d5.color == chess.BLACK
        and black_d5.piece_type == chess.PAWN
        and black_e6 is not None
        and black_e6.color == chess.BLACK
        and black_e6.piece_type == chess.PAWN
    ):
        candidates.extend(["b1c3", "f1d3", "f1e2", "e4e5", "e1g1"])

    return _dedupe_keep_order(candidates)


def _build_opening_candidates(py_board: chess.Board, color: chess.Color) -> List[str]:
    # Always prioritize immediate castling when legal.
    if color == chess.WHITE:
        preferred = _white_italian_candidates(py_board)
        universal = _white_universal_castling_candidates()
        urgent = _white_urgent_tactical_candidates(py_board)
    else:
        preferred = _black_italian_candidates(py_board)
        universal = _black_universal_castling_candidates()
        urgent = _black_urgent_tactical_candidates(py_board)

    # Tactical urgent moves must outrank castling to avoid drifting in sharp lines.
    if urgent:
        return _dedupe_keep_order(urgent + [_kingside_castle_uci(color)] + preferred + universal)
    return _dedupe_keep_order([_kingside_castle_uci(color)] + preferred + universal)


def choose_italian_castling_move(board: Board, legal_moves: List[chess.Move]) -> Optional[chess.Move]:
    """Return a safe opening move that aggressively targets king-side castling."""
    py_board = board.to_python_chess()
    if py_board.is_check():
        return None
    if py_board.fullmove_number > OPENING_BOOK_MAX_FULLMOVE:
        return None

    move_by_uci = {move.uci(): move for move in legal_moves}

    side = py_board.turn
    if _is_castled(py_board, side):
        return None

    side_plies = _side_plies_played(py_board, side)
    castle_move = move_by_uci.get(_kingside_castle_uci(side))
    urgent_black = _black_urgent_tactical_candidates(py_board) if side == chess.BLACK else []

    # Black should recapture first after a fresh white capture (e.g., ...Bc5 and Bxc6).
    if side == chess.BLACK:
        capture_square = _recent_enemy_capture_square(py_board, side)
        if capture_square is not None:
            recaptures = _recapture_candidates_uci(legal_moves, capture_square)
            safe_recap = _pick_first_safe_legal(move_by_uci, py_board, recaptures)
            if safe_recap is not None:
                return safe_recap
            # If no recapture passes safety filter, still prefer tactical restoration over castling.
            for uci in recaptures:
                move = move_by_uci.get(uci)
                if move is not None:
                    return move

    # Hard deadline policy: on the 7th move of a side, castle immediately if legal.
    if side_plies >= (OPENING_BOOK_CASTLE_DEADLINE_MOVES - 1) and castle_move is not None and not urgent_black:
        return castle_move

    # First priority: follow explicitly curated Italian lines when position matches.
    repertoire_uci = _next_repertoire_move(py_board, side)
    if repertoire_uci is not None:
        repertoire_move = move_by_uci.get(repertoire_uci)
        if repertoire_move is not None and _is_non_losing_move(py_board, repertoire_move):
            return repertoire_move

    candidates = _build_opening_candidates(py_board, side)
    chosen = _pick_first_safe_legal(move_by_uci, py_board, candidates)
    if chosen is not None:
        return chosen

    # If deadline is reached and castling is still unavailable, keep pushing setup moves.
    if side_plies >= (OPENING_BOOK_CASTLE_DEADLINE_MOVES - 1):
        if side == chess.WHITE:
            emergency = _dedupe_keep_order(_white_universal_castling_candidates())
        else:
            emergency = _dedupe_keep_order(_black_universal_castling_candidates())
        return _pick_first_safe_legal(move_by_uci, py_board, emergency)

    return None
