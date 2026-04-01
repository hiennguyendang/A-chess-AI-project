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
KING_CORNER_DISTANCE_PENALTY = 4
KING_ENDGAME_ACTIVITY_BONUS = 5
PASSED_PAWN_BASE_BONUS = 26
PASSED_PAWN_ADVANCE_BONUS = 9
CONNECTED_PAWN_BONUS = 8
KING_PAWN_SUPPORT_BONUS = 12
GAME_PHASE_MAX = 24

KING_SAFETY_MID_MULT = 1.10
KING_SAFETY_END_MULT = 0.15
KING_CORNER_MID_MULT = 1.0
KING_CORNER_END_MULT = 0.10
MOBILITY_MID_MULT = 1.0
MOBILITY_END_MULT = 0.55
KING_ACTIVITY_END_MULT = 0.45
PAWN_STRUCTURE_END_MULT = 1.20
ENDGAME_TRIGGER_MINOR_PAIR_PAWNS_MAX = 5
ENDGAME_TRIGGER_MIXED_PAWNS_MAX = 3
ATTACKING_ENDGAME_KING_ACTIVITY_BONUS = 10
ATTACKING_ENDGAME_PAWN_ADVANCE_BONUS = 6
DEFENSIVE_COMPACTNESS_MULT = 6
DEFENSIVE_KING_SHELTER_BONUS = 10
PROMOTION_THREAT_BASE = 500  # 7th-rank pawn ~= rook
PROMOTION_THREAT_DEFENDED_BONUS = 100  # +1 pawn if defended
PROMOTION_THREAT_PROMO_SQ_DEF_BONUS = 200  # +2 pawns if promotion square defended

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

KING_TABLE_END: List[int] = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10, 0, 0, -10, -20, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -30, 0, 0, 0, 0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50,
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

        phase = Evaluator._game_phase(board)

        score = 0
        for piece_type, value in PIECE_VALUES.items():
            score += value * len(board.pieces(piece_type, chess.WHITE))
            score -= value * len(board.pieces(piece_type, chess.BLACK))

        score += Evaluator._piece_square_bonus(board, phase)
        score += Evaluator._bishop_pair_bonus(board)
        score += int(Evaluator._king_safety_bonus(board) * (KING_SAFETY_END_MULT + (KING_SAFETY_MID_MULT - KING_SAFETY_END_MULT) * phase))
        score += int(Evaluator._king_corner_penalty_when_enemy_queen_alive(board) * (KING_CORNER_END_MULT + (KING_CORNER_MID_MULT - KING_CORNER_END_MULT) * phase))
        score += int(Evaluator._mobility_bonus(board) * (MOBILITY_END_MULT + (MOBILITY_MID_MULT - MOBILITY_END_MULT) * phase))
        score += int(Evaluator._king_activity_endgame_bonus(board) * (1.0 - phase) * KING_ACTIVITY_END_MULT)
        score += int(Evaluator._pawn_structure_endgame_bonus(board) * (1.0 - phase) * PAWN_STRUCTURE_END_MULT)
        score += Evaluator._dynamic_endgame_posture_bonus(board)
        score += Evaluator._promotion_threat_bonus(board)
        return score

    @staticmethod
    def _material_cp(board: chess.Board, color: chess.Color) -> int:
        score = 0
        for piece_type, value in PIECE_VALUES.items():
            if piece_type == chess.KING:
                continue
            score += value * len(board.pieces(piece_type, color))
        return score

    @staticmethod
    def _opponent_endgame_profile(board: chess.Board, color: chess.Color) -> bool:
        opponent = not color
        opp_minors = len(board.pieces(chess.KNIGHT, opponent)) + len(board.pieces(chess.BISHOP, opponent))
        opp_majors = len(board.pieces(chess.ROOK, opponent)) + len(board.pieces(chess.QUEEN, opponent))
        opp_pawns = len(board.pieces(chess.PAWN, opponent))

        profile_minor_pair = opp_majors == 0 and opp_minors == 2 and opp_pawns <= ENDGAME_TRIGGER_MINOR_PAIR_PAWNS_MAX
        profile_mixed = opp_majors == 1 and opp_minors == 1 and opp_pawns <= ENDGAME_TRIGGER_MIXED_PAWNS_MAX
        return profile_minor_pair or profile_mixed

    @staticmethod
    def _endgame_intent(board: chess.Board, color: chess.Color) -> int:
        """Return 1 for attacking endgame posture, -1 for defensive posture, else 0."""
        if not Evaluator._opponent_endgame_profile(board, color):
            return 0

        our_cp = Evaluator._material_cp(board, color)
        opp_cp = Evaluator._material_cp(board, not color)
        if our_cp > opp_cp:
            return 1
        if our_cp < opp_cp:
            return -1
        return 0

    @staticmethod
    def _center_activity_score(board: chess.Board, color: chess.Color) -> int:
        king_sq = board.king(color)
        if king_sq is None:
            return 0
        center_squares = (chess.D4, chess.E4, chess.D5, chess.E5)
        min_dist = min(chess.square_distance(king_sq, center_sq) for center_sq in center_squares)
        return 4 - min_dist

    @staticmethod
    def _pawn_push_score(board: chess.Board, color: chess.Color) -> int:
        score = 0
        for sq in board.pieces(chess.PAWN, color):
            rank_idx = chess.square_rank(sq)
            progress = rank_idx - 1 if color == chess.WHITE else 6 - rank_idx
            score += max(0, progress)
        return score

    @staticmethod
    def _compactness_score(board: chess.Board, color: chess.Color) -> int:
        king_sq = board.king(color)
        if king_sq is None:
            return 0

        compactness = 0
        tracked = (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
        for piece_type in tracked:
            for sq in board.pieces(piece_type, color):
                # Closer pieces to king => larger compactness score.
                compactness += max(0, 5 - chess.square_distance(sq, king_sq))
        return compactness

    @staticmethod
    def _king_shelter_score(board: chess.Board, color: chess.Color) -> int:
        king_sq = board.king(color)
        if king_sq is None:
            return 0

        rank_idx = chess.square_rank(king_sq)
        shelter = 0
        if color == chess.WHITE and rank_idx <= 1:
            shelter += DEFENSIVE_KING_SHELTER_BONUS
        if color == chess.BLACK and rank_idx >= 6:
            shelter += DEFENSIVE_KING_SHELTER_BONUS
        shelter += max(0, 4 - Evaluator._min_corner_distance(king_sq))
        return shelter

    @staticmethod
    def _dynamic_endgame_posture_bonus(board: chess.Board) -> int:
        score = 0

        white_intent = Evaluator._endgame_intent(board, chess.WHITE)
        if white_intent > 0:
            score += ATTACKING_ENDGAME_KING_ACTIVITY_BONUS * Evaluator._center_activity_score(board, chess.WHITE)
            score += ATTACKING_ENDGAME_PAWN_ADVANCE_BONUS * Evaluator._pawn_push_score(board, chess.WHITE)
        elif white_intent < 0:
            score += DEFENSIVE_COMPACTNESS_MULT * Evaluator._compactness_score(board, chess.WHITE)
            score += Evaluator._king_shelter_score(board, chess.WHITE)

        black_intent = Evaluator._endgame_intent(board, chess.BLACK)
        if black_intent > 0:
            score -= ATTACKING_ENDGAME_KING_ACTIVITY_BONUS * Evaluator._center_activity_score(board, chess.BLACK)
            score -= ATTACKING_ENDGAME_PAWN_ADVANCE_BONUS * Evaluator._pawn_push_score(board, chess.BLACK)
        elif black_intent < 0:
            score -= DEFENSIVE_COMPACTNESS_MULT * Evaluator._compactness_score(board, chess.BLACK)
            score -= Evaluator._king_shelter_score(board, chess.BLACK)

        return score

    @staticmethod
    def _promotion_pawn_threat(board: chess.Board, square: chess.Square, color: chess.Color) -> int:
        rank_idx = chess.square_rank(square)
        is_seventh = rank_idx == 6 if color == chess.WHITE else rank_idx == 1
        if not is_seventh:
            return 0

        threat = PROMOTION_THREAT_BASE
        opponent = not color
        if board.is_attacked_by(color, square):
            threat += PROMOTION_THREAT_DEFENDED_BONUS

        file_idx = chess.square_file(square)
        promo_rank = 7 if color == chess.WHITE else 0
        promo_square = chess.square(file_idx, promo_rank)
        if board.is_attacked_by(color, promo_square) and not board.is_attacked_by(opponent, promo_square):
            threat += PROMOTION_THREAT_PROMO_SQ_DEF_BONUS
        return threat

    @staticmethod
    def _promotion_threat_bonus(board: chess.Board) -> int:
        score = 0
        for sq in board.pieces(chess.PAWN, chess.WHITE):
            score += Evaluator._promotion_pawn_threat(board, sq, chess.WHITE)
        for sq in board.pieces(chess.PAWN, chess.BLACK):
            score -= Evaluator._promotion_pawn_threat(board, sq, chess.BLACK)
        return score

    @staticmethod
    def _game_phase(board: chess.Board) -> float:
        """Return game phase in [0, 1]: 1.0 opening/midgame, 0.0 endgame."""
        phase_score = 0
        phase_score += (len(board.pieces(chess.KNIGHT, chess.WHITE)) + len(board.pieces(chess.KNIGHT, chess.BLACK)))
        phase_score += (len(board.pieces(chess.BISHOP, chess.WHITE)) + len(board.pieces(chess.BISHOP, chess.BLACK)))
        phase_score += 2 * (len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK)))
        phase_score += 4 * (len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK)))
        return min(GAME_PHASE_MAX, phase_score) / GAME_PHASE_MAX

    @staticmethod
    def _piece_square_bonus(board: chess.Board, phase: float) -> int:
        score = 0
        for piece_type, table in PIECE_SQUARE_TABLES.items():
            if piece_type == chess.KING:
                for sq in board.pieces(chess.KING, chess.WHITE):
                    mid = KING_TABLE_MID[sq]
                    end = KING_TABLE_END[sq]
                    score += int(mid * phase + end * (1.0 - phase))
                for sq in board.pieces(chess.KING, chess.BLACK):
                    mirrored = chess.square_mirror(sq)
                    mid = KING_TABLE_MID[mirrored]
                    end = KING_TABLE_END[mirrored]
                    score -= int(mid * phase + end * (1.0 - phase))
                continue
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
            score += 24 if chess.square_rank(white_king) <= 1 else -18
        if black_king is not None:
            score -= 24 if chess.square_rank(black_king) >= 6 else -18
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

    @staticmethod
    def _min_corner_distance(square: chess.Square) -> int:
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        corners = ((0, 0), (0, 7), (7, 0), (7, 7))
        return min(abs(file_idx - file_corner) + abs(rank_idx - rank_corner) for file_corner, rank_corner in corners)

    @staticmethod
    def _king_corner_penalty_when_enemy_queen_alive(board: chess.Board) -> int:
        """Penalize kings that drift from corners while the opponent queen is still on board."""
        score = 0

        white_king = board.king(chess.WHITE)
        if white_king is not None and board.pieces(chess.QUEEN, chess.BLACK):
            score -= Evaluator._min_corner_distance(white_king) * KING_CORNER_DISTANCE_PENALTY

        black_king = board.king(chess.BLACK)
        if black_king is not None and board.pieces(chess.QUEEN, chess.WHITE):
            score += Evaluator._min_corner_distance(black_king) * KING_CORNER_DISTANCE_PENALTY

        return score

    @staticmethod
    def _king_activity_endgame_bonus(board: chess.Board) -> int:
        """Encourage king activity toward the center in endgames."""
        center_squares = (chess.D4, chess.E4, chess.D5, chess.E5)
        score = 0

        white_king = board.king(chess.WHITE)
        if white_king is not None:
            min_dist = min(chess.square_distance(white_king, center_sq) for center_sq in center_squares)
            score += (4 - min_dist) * KING_ENDGAME_ACTIVITY_BONUS

        black_king = board.king(chess.BLACK)
        if black_king is not None:
            min_dist = min(chess.square_distance(black_king, center_sq) for center_sq in center_squares)
            score -= (4 - min_dist) * KING_ENDGAME_ACTIVITY_BONUS

        return score

    @staticmethod
    def _is_passed_pawn(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        enemy_color = not color

        for file_delta in (-1, 0, 1):
            f = file_idx + file_delta
            if f < 0 or f > 7:
                continue
            ranks = range(rank_idx + 1, 8) if color == chess.WHITE else range(rank_idx - 1, -1, -1)
            for r in ranks:
                sq = chess.square(f, r)
                piece = board.piece_at(sq)
                if piece is not None and piece.color == enemy_color and piece.piece_type == chess.PAWN:
                    return False
        return True

    @staticmethod
    def _is_connected_pawn(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)

        for file_delta in (-1, 1):
            f = file_idx + file_delta
            if f < 0 or f > 7:
                continue
            for r in (rank_idx - 1, rank_idx, rank_idx + 1):
                if r < 0 or r > 7:
                    continue
                sq = chess.square(f, r)
                piece = board.piece_at(sq)
                if piece is not None and piece.color == color and piece.piece_type == chess.PAWN:
                    return True
        return False

    @staticmethod
    def _pawn_structure_endgame_bonus(board: chess.Board) -> int:
        """Reward promotion potential and connected pawn structures in endgames."""
        score = 0

        white_king = board.king(chess.WHITE)
        for sq in board.pieces(chess.PAWN, chess.WHITE):
            rank_idx = chess.square_rank(sq)
            if Evaluator._is_passed_pawn(board, sq, chess.WHITE):
                progress = max(0, rank_idx - 1)
                score += PASSED_PAWN_BASE_BONUS + progress * PASSED_PAWN_ADVANCE_BONUS
                if white_king is not None and chess.square_distance(white_king, sq) <= 2:
                    score += KING_PAWN_SUPPORT_BONUS
            if Evaluator._is_connected_pawn(board, sq, chess.WHITE):
                score += CONNECTED_PAWN_BONUS

        black_king = board.king(chess.BLACK)
        for sq in board.pieces(chess.PAWN, chess.BLACK):
            rank_idx = chess.square_rank(sq)
            if Evaluator._is_passed_pawn(board, sq, chess.BLACK):
                progress = max(0, 6 - rank_idx)
                score -= PASSED_PAWN_BASE_BONUS + progress * PASSED_PAWN_ADVANCE_BONUS
                if black_king is not None and chess.square_distance(black_king, sq) <= 2:
                    score -= KING_PAWN_SUPPORT_BONUS
            if Evaluator._is_connected_pawn(board, sq, chess.BLACK):
                score -= CONNECTED_PAWN_BONUS

        return score
