"""Board evaluation heuristics."""
from __future__ import annotations

from typing import Dict, List

import chess

PIECE_VALUES: Dict[chess.PieceType, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,  # king value handled implicitly via checkmate detection
}

MATE_SCORE = 100_000

# Piece-square tables from White perspective. Black uses mirrored index.
PAWN_TABLE: List[int] = [
    0, 0, 0, 0, 0, 0, 0, 0,
    5, 10, 10, -20, -20, 10, 10, 5,
    5, -5, -10, 0, 0, -10, -5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, 5, 10, 25, 25, 10, 5, 5,
    10, 10, 20, 30, 30, 20, 10, 10,
    50, 50, 50, 50, 50, 50, 50, 50,
    0, 0, 0, 0, 0, 0, 0, 0,
]

KNIGHT_TABLE: List[int] = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -30, 0, 10, 15, 15, 10, 0, -30,
    -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30,
    -30, 5, 10, 15, 15, 10, 5, -30,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]

BISHOP_TABLE: List[int] = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]

ROOK_TABLE: List[int] = [
    0, 0, 0, 5, 5, 0, 0, 0,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    5, 10, 10, 10, 10, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
]

QUEEN_TABLE: List[int] = [
    -20, -10, -10, -5, -5, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 5, 5, 5, 0, -10,
    -5, 0, 5, 5, 5, 5, 0, -5,
    0, 0, 5, 5, 5, 5, 0, -5,
    -10, 5, 5, 5, 5, 5, 0, -10,
    -10, 0, 5, 0, 0, 0, 0, -10,
    -20, -10, -10, -5, -5, -10, -10, -20,
]

KING_TABLE_MID: List[int] = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20,
    20, 30, 10, 0, 0, 10, 30, 20,
]

PIECE_SQUARE_TABLES: Dict[chess.PieceType, List[int]] = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
    chess.KING: KING_TABLE_MID,
}


class Evaluator:
    """Static evaluation based on material with light bonuses."""

    @staticmethod
    def evaluate(board: chess.Board) -> int:
        """Return a score from White's perspective (centipawns)."""
        if board.is_checkmate():
            return -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        score = 0
        for piece_type, value in PIECE_VALUES.items():
            score += value * len(board.pieces(piece_type, chess.WHITE))
            score -= value * len(board.pieces(piece_type, chess.BLACK))

        score += Evaluator._piece_square_bonus(board)
        score += Evaluator._bishop_pair_bonus(board)
        score += Evaluator._king_safety_bonus(board)
        score += Evaluator._mobility_bonus(board)
        return score

    @staticmethod
    def _piece_square_bonus(board: chess.Board) -> int:
        score = 0
        for piece_type, table in PIECE_SQUARE_TABLES.items():
            for sq in board.pieces(piece_type, chess.WHITE):
                score += table[sq]
            for sq in board.pieces(piece_type, chess.BLACK):
                score -= table[chess.square_mirror(sq)]
        return score

    @staticmethod
    def _bishop_pair_bonus(board: chess.Board) -> int:
        score = 0
        if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
            score += 30
        if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
            score -= 30
        return score

    @staticmethod
    def _king_safety_bonus(board: chess.Board) -> int:
        score = 0
        white_king = board.king(chess.WHITE)
        black_king = board.king(chess.BLACK)
        if white_king is not None:
            score += 12 if chess.square_rank(white_king) <= 1 else -8
        if black_king is not None:
            score -= 12 if chess.square_rank(black_king) >= 6 else -8
        return score

    @staticmethod
    def _mobility_bonus(board: chess.Board) -> int:
        """Simple mobility heuristic: difference in legal moves."""
        white_board = board.copy(stack=False)
        white_board.turn = chess.WHITE
        white_moves = len(list(white_board.legal_moves))

        black_board = board.copy(stack=False)
        black_board.turn = chess.BLACK
        black_moves = len(list(black_board.legal_moves))
        return (white_moves - black_moves) * 2
