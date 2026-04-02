"""Board evaluation heuristics."""
from __future__ import annotations

from typing import Dict, List, Optional

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
HANGING_PIECE_PENALTY_MIN = 30
HANGING_PIECE_PENALTY_DIVISOR = 3
UNFAVORABLE_EXCHANGE_PENALTY_MIN = 16
UNFAVORABLE_EXCHANGE_PENALTY_DIVISOR = 8
PRESSURE_IMBALANCE_PENALTY_MIN = 8
PRESSURE_IMBALANCE_PENALTY_DIVISOR = 16
CASTLED_BONUS = 28
UNCASLTED_CENTER_KING_PENALTY = 24
KING_ZONE_ATTACK_PENALTY = 9
KING_PAWN_SHIELD_BONUS = 10

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
        # Keep terminal draw rules in sync with engine.board.Board.
        if board.is_stalemate() or board.is_insufficient_material() or board.halfmove_clock >= 100:
            return 0

        score = 0
        for piece_type, value in PIECE_VALUES.items():
            score += value * len(board.pieces(piece_type, chess.WHITE))
            score -= value * len(board.pieces(piece_type, chess.BLACK))

        score += Evaluator._piece_square_bonus(board)
        score += Evaluator._bishop_pair_bonus(board)
        score += Evaluator._king_safety_bonus(board)
        score += Evaluator._mobility_bonus(board)
        # Tactical safety: discourage leaving pieces en prise at low depth.
        score -= Evaluator._hanging_risk_penalty(board, chess.WHITE)
        score += Evaluator._hanging_risk_penalty(board, chess.BLACK)
        return score

    @staticmethod
    def _least_attacker_value(board: chess.Board, color: chess.Color, square: chess.Square) -> Optional[int]:
        values: List[int] = []
        for from_sq in board.attackers(color, square):
            piece = board.piece_at(from_sq)
            if piece is None:
                continue
            values.append(PIECE_VALUES.get(piece.piece_type, 0))
        if not values:
            return None
        return min(values)

    @staticmethod
    def _is_castled(board: chess.Board, color: chess.Color) -> bool:
        king_sq = board.king(color)
        if king_sq is None:
            return False
        if color == chess.WHITE:
            return king_sq in (chess.G1, chess.C1)
        return king_sq in (chess.G8, chess.C8)

    @staticmethod
    def _king_zone_squares(king_sq: chess.Square) -> List[chess.Square]:
        file_idx = chess.square_file(king_sq)
        rank_idx = chess.square_rank(king_sq)
        squares = [king_sq]
        for df in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if df == 0 and dr == 0:
                    continue
                nf = file_idx + df
                nr = rank_idx + dr
                if 0 <= nf < 8 and 0 <= nr < 8:
                    squares.append(chess.square(nf, nr))
        return squares

    @staticmethod
    def _king_pawn_shield(board: chess.Board, color: chess.Color) -> int:
        king_sq = board.king(color)
        if king_sq is None:
            return 0

        file_idx = chess.square_file(king_sq)
        rank_idx = chess.square_rank(king_sq)
        front_rank = rank_idx + 1 if color == chess.WHITE else rank_idx - 1
        if not (0 <= front_rank < 8):
            return 0

        shield = 0
        for df in (-1, 0, 1):
            nf = file_idx + df
            if not (0 <= nf < 8):
                continue
            sq = chess.square(nf, front_rank)
            piece = board.piece_at(sq)
            if piece is not None and piece.color == color and piece.piece_type == chess.PAWN:
                shield += 1
        return shield

    @staticmethod
    def _hanging_risk_penalty(board: chess.Board, color: chess.Color) -> int:
        opponent = not color
        penalty = 0
        for piece_type in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            piece_value = PIECE_VALUES[piece_type]
            for sq in board.pieces(piece_type, color):
                opp_attackers = list(board.attackers(opponent, sq))
                if not opp_attackers:
                    continue

                opp_min = Evaluator._least_attacker_value(board, opponent, sq)
                if opp_min is None:
                    continue

                our_defenders = list(board.attackers(color, sq))
                our_min = Evaluator._least_attacker_value(board, color, sq)
                if our_min is None:
                    penalty += max(HANGING_PIECE_PENALTY_MIN, piece_value // HANGING_PIECE_PENALTY_DIVISOR)
                elif opp_min <= our_min:
                    penalty += max(UNFAVORABLE_EXCHANGE_PENALTY_MIN, piece_value // UNFAVORABLE_EXCHANGE_PENALTY_DIVISOR)

                pressure_gap = len(opp_attackers) - len(our_defenders)
                if pressure_gap > 0:
                    penalty += pressure_gap * max(
                        PRESSURE_IMBALANCE_PENALTY_MIN,
                        piece_value // PRESSURE_IMBALANCE_PENALTY_DIVISOR,
                    )
        return penalty

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
            if Evaluator._is_castled(board, chess.WHITE):
                score += CASTLED_BONUS
            elif chess.square_file(white_king) in (3, 4) and chess.square_rank(white_king) <= 1:
                score -= UNCASLTED_CENTER_KING_PENALTY

            score += KING_PAWN_SHIELD_BONUS * Evaluator._king_pawn_shield(board, chess.WHITE)
            zone = Evaluator._king_zone_squares(white_king)
            attacked = sum(1 for sq in zone if board.is_attacked_by(chess.BLACK, sq))
            score -= attacked * KING_ZONE_ATTACK_PENALTY

        if black_king is not None:
            if Evaluator._is_castled(board, chess.BLACK):
                score -= CASTLED_BONUS
            elif chess.square_file(black_king) in (3, 4) and chess.square_rank(black_king) >= 6:
                score += UNCASLTED_CENTER_KING_PENALTY

            score -= KING_PAWN_SHIELD_BONUS * Evaluator._king_pawn_shield(board, chess.BLACK)
            zone = Evaluator._king_zone_squares(black_king)
            attacked = sum(1 for sq in zone if board.is_attacked_by(chess.WHITE, sq))
            score += attacked * KING_ZONE_ATTACK_PENALTY
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
