"""MCTS-specific value and rollout evaluation helpers."""
from __future__ import annotations

import math
import random
from typing import Optional

import chess

from engine.board import Board
from engine.evaluator import Evaluator


PIECE_VALUE_LIGHT = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}

PIECE_VALUE_CP = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20_000,
}

OPENING_KING_WALK_SOFT_PENALTY = 85
OPENING_DEVELOPMENT_BONUS = 10
OPENING_CASTLING_RIGHTS_BONUS = 16
SCRIPTED_CASTLING_MAX_FULLMOVE = 16
SCRIPTED_MAX_STATIC_DROP_CP = 120
TRADE_EQUAL_BONUS = 7
TRADE_WINNING_BONUS = 13
TRADE_PHASE_MIN = 0.42
RECAPTURE_RISK_CP_MULT = 2
HANGING_PIECE_CP_PENALTY = 260
HANGING_QUEEN_CP_PENALTY = 900
HANGING_MAJOR_CP_PENALTY = 500
HANGING_MINOR_CP_PENALTY = 220
FORCED_TRADE_EQUAL_BONUS = 20
FORCED_TRADE_WINNING_BONUS = 35
ROLLOUT_OPPONENT_PUNISH_BEST_MOVE_PROB = 0.82
ROLLOUT_OPPONENT_CHECK_BONUS = 8
ROLLOUT_OPPONENT_WIN_CAPTURE_BONUS = 14
ROLLOUT_OPPONENT_EQUAL_CAPTURE_BONUS = 7
BASIC_ROLLOUT_RULES_ENABLED = True
BASIC_ROLLOUT_MAX_HANGING_RISK_CP = 360
BASIC_ROLLOUT_TOP_K = 4
KING_FILE_DOUBLE_PUSH_PENALTY = 16
KING_CORNER_DRIFT_PENALTY = 18
KING_CORNER_DISTANCE_PENALTY = 4
QUEEN_TRADE_PHASE_MIN = 0.40
QUEEN_TRADE_BONUS = 34

SCRIPTED_ITALIAN_WHITE = [
    "e2e4",
    "g1f3",
    "f1c4",
    "e1g1",
]

SCRIPTED_WHITE_VS_NF6 = [
    "b1c3",
    "g1f3",
    "d2d3",
    "f1e2",
    "f1c4",
    "e1g1",
]

SCRIPTED_ITALIAN_BLACK = [
    "e7e5",
    "b8c6",
    "g8f6",
    "f8c5",
    "e8g8",
]

SCRIPTED_QGD_BLACK_VS_D4 = [
    "d7d5",
    "g8f6",
    "e7e6",
    "f8e7",
    "e8g8",
]


def _is_castled(py_board: chess.Board, color: chess.Color) -> bool:
    king_sq = py_board.king(color)
    if king_sq is None:
        return False
    if color == chess.WHITE:
        return king_sq in (chess.G1, chess.C1)
    return king_sq in (chess.G8, chess.C8)


def _opening_script_completed(py_board: chess.Board) -> bool:
    color = py_board.turn
    if py_board.fullmove_number > SCRIPTED_CASTLING_MAX_FULLMOVE:
        return True
    if _is_castled(py_board, color):
        return True
    if not py_board.has_kingside_castling_rights(color):
        return True
    return False


def _game_phase(py_board: chess.Board) -> float:
    phase_score = 0
    phase_score += len(py_board.pieces(chess.KNIGHT, chess.WHITE)) + len(py_board.pieces(chess.KNIGHT, chess.BLACK))
    phase_score += len(py_board.pieces(chess.BISHOP, chess.WHITE)) + len(py_board.pieces(chess.BISHOP, chess.BLACK))
    phase_score += 2 * (len(py_board.pieces(chess.ROOK, chess.WHITE)) + len(py_board.pieces(chess.ROOK, chess.BLACK)))
    phase_score += 4 * (len(py_board.pieces(chess.QUEEN, chess.WHITE)) + len(py_board.pieces(chess.QUEEN, chess.BLACK)))
    return min(24, phase_score) / 24.0


def _is_effective_endgame(py_board: chess.Board) -> bool:
    # If any queen remains, treat as non-endgame for king-safety behavior.
    if py_board.pieces(chess.QUEEN, chess.WHITE) or py_board.pieces(chess.QUEEN, chess.BLACK):
        return False
    return _game_phase(py_board) <= 0.28


def _min_corner_distance(square: chess.Square) -> int:
    file_idx = chess.square_file(square)
    rank_idx = chess.square_rank(square)
    corners = ((0, 0), (0, 7), (7, 0), (7, 7))
    return min(abs(file_idx - corner_file) + abs(rank_idx - corner_rank) for corner_file, corner_rank in corners)


def _king_file_double_push_penalty(py_board: chess.Board, move: chess.Move) -> int:
    piece = py_board.piece_at(move.from_square)
    if piece is None or piece.piece_type != chess.PAWN:
        return 0

    side = py_board.turn
    king_sq = py_board.king(side)
    if king_sq is None:
        return 0

    if chess.square_file(move.from_square) != chess.square_file(king_sq):
        return 0

    rank_delta = chess.square_rank(move.to_square) - chess.square_rank(move.from_square)
    if side == chess.WHITE and rank_delta == 2:
        return KING_FILE_DOUBLE_PUSH_PENALTY
    if side == chess.BLACK and rank_delta == -2:
        return KING_FILE_DOUBLE_PUSH_PENALTY
    return 0


def _king_corner_safety_penalty(py_board: chess.Board, move: chess.Move) -> int:
    piece = py_board.piece_at(move.from_square)
    if piece is None or piece.piece_type != chess.KING:
        return 0

    if py_board.is_check() or _is_effective_endgame(py_board):
        return 0

    before_dist = _min_corner_distance(move.from_square)
    after_dist = _min_corner_distance(move.to_square)
    drift = max(0, after_dist - before_dist)
    return drift * KING_CORNER_DRIFT_PENALTY + after_dist * KING_CORNER_DISTANCE_PENALTY


def _queen_trade_bonus(py_board: chess.Board, move: chess.Move) -> int:
    if _game_phase(py_board) < QUEEN_TRADE_PHASE_MIN:
        return 0
    if not py_board.is_capture(move):
        return 0

    attacker = py_board.piece_at(move.from_square)
    captured = py_board.piece_at(move.to_square)
    if attacker is None or captured is None:
        return 0

    # Prioritize direct queen trade (QxQ) in early/midgame when tactically safe.
    if attacker.piece_type == chess.QUEEN and captured.piece_type == chess.QUEEN and is_immediate_non_losing_move(py_board, move):
        return QUEEN_TRADE_BONUS
    return 0


def _opening_structure_cp(py_board: chess.Board) -> int:
    """Soft opening priors for MCTS value heads; avoid hard move filtering."""
    phase = _game_phase(py_board)
    if phase <= 0.35:
        return 0

    score = 0

    white_king = py_board.king(chess.WHITE)
    if white_king is not None and white_king != chess.E1 and not py_board.is_check():
        score -= int(OPENING_KING_WALK_SOFT_PENALTY * phase)
    black_king = py_board.king(chess.BLACK)
    if black_king is not None and black_king != chess.E8 and not py_board.is_check():
        score += int(OPENING_KING_WALK_SOFT_PENALTY * phase)

    if py_board.has_kingside_castling_rights(chess.WHITE):
        score += int(OPENING_CASTLING_RIGHTS_BONUS * phase)
    if py_board.has_kingside_castling_rights(chess.BLACK):
        score -= int(OPENING_CASTLING_RIGHTS_BONUS * phase)

    # Encourage early minor-piece development from home squares.
    if py_board.piece_at(chess.G1) is None:
        score += int(OPENING_DEVELOPMENT_BONUS * phase)
    if py_board.piece_at(chess.B1) is None:
        score += int(OPENING_DEVELOPMENT_BONUS * phase)
    if py_board.piece_at(chess.F1) is None:
        score += int(OPENING_DEVELOPMENT_BONUS * phase)

    if py_board.piece_at(chess.G8) is None:
        score -= int(OPENING_DEVELOPMENT_BONUS * phase)
    if py_board.piece_at(chess.B8) is None:
        score -= int(OPENING_DEVELOPMENT_BONUS * phase)
    if py_board.piece_at(chess.F8) is None:
        score -= int(OPENING_DEVELOPMENT_BONUS * phase)

    return score


def evaluate_cp_for_mcts(py_board: chess.Board) -> int:
    return Evaluator.evaluate(py_board) + _opening_structure_cp(py_board)


def is_immediate_non_losing_move(py_board: chess.Board, move: chess.Move) -> bool:
    piece = py_board.piece_at(move.from_square)
    if piece is None:
        return False

    side = py_board.turn
    opponent = not side

    capture_value = 0
    if py_board.is_capture(move):
        captured_piece = py_board.piece_at(move.to_square)
        if captured_piece is None and py_board.is_en_passant(move):
            ep_sq = move.to_square - 8 if side == chess.WHITE else move.to_square + 8
            captured_piece = py_board.piece_at(ep_sq)
        if captured_piece is not None:
            capture_value = PIECE_VALUE_LIGHT.get(captured_piece.piece_type, 0)

    moved_value = PIECE_VALUE_LIGHT.get(piece.piece_type, 0)

    after = py_board.copy(stack=False)
    after.push(move)
    if after.is_check():
        return False

    attacked = after.is_attacked_by(opponent, move.to_square)
    defended = after.is_attacked_by(side, move.to_square)
    if not attacked:
        return True

    if not defended:
        return capture_value >= moved_value

    least_opp = _least_attacker_value(after, opponent, move.to_square)
    least_our = _least_attacker_value(after, side, move.to_square)
    if least_opp is None:
        return True
    if least_our is None:
        return capture_value >= moved_value

    # If opponent can recapture with an equal/cheaper piece, require non-losing trade.
    if least_opp <= least_our and capture_value < moved_value:
        return False
    return True


def _least_attacker_value(board: chess.Board, color: chess.Color, square: chess.Square) -> Optional[int]:
    values = []
    for from_sq in board.attackers(color, square):
        piece = board.piece_at(from_sq)
        if piece is None:
            continue
        values.append(PIECE_VALUE_CP.get(piece.piece_type, 0))
    if not values:
        return None
    return min(values)


def _immediate_recapture_risk_cp(py_board: chess.Board, move: chess.Move) -> int:
    """Estimate tactical downside if the moved piece can be cheaply recaptured immediately."""
    piece = py_board.piece_at(move.from_square)
    if piece is None:
        return 0

    side = py_board.turn
    opponent = not side
    moved_cp = PIECE_VALUE_CP.get(piece.piece_type, 0)

    captured_cp = 0
    if py_board.is_capture(move):
        captured_piece = py_board.piece_at(move.to_square)
        if captured_piece is None and py_board.is_en_passant(move):
            ep_sq = move.to_square - 8 if side == chess.WHITE else move.to_square + 8
            captured_piece = py_board.piece_at(ep_sq)
        if captured_piece is not None:
            captured_cp = PIECE_VALUE_CP.get(captured_piece.piece_type, 0)

    after = py_board.copy(stack=False)
    after.push(move)
    dst = move.to_square

    if not after.is_attacked_by(opponent, dst):
        return 0

    opp_min = _least_attacker_value(after, opponent, dst)
    our_min = _least_attacker_value(after, side, dst)
    if opp_min is None:
        return 0

    gross_loss = max(0, moved_cp - captured_cp)

    if our_min is None:
        # Hanging piece after the move.
        return max(HANGING_PIECE_CP_PENALTY, gross_loss)

    # If opponent recaptures with equal/cheaper unit than our best defender,
    # treat it as high tactical risk in short rollouts.
    if opp_min <= our_min:
        return gross_loss

    # Still keep a light penalty for tactical volatility.
    return gross_loss // 3


def _post_move_hanging_risk_cp(py_board: chess.Board, move: chess.Move) -> int:
    """Penalize moves that leave high-value pieces en prise after the move."""
    side = py_board.turn
    opponent = not side

    after = py_board.copy(stack=False)
    after.push(move)

    risk = 0
    for piece_type, hanging_penalty in (
        (chess.QUEEN, HANGING_QUEEN_CP_PENALTY),
        (chess.ROOK, HANGING_MAJOR_CP_PENALTY),
        (chess.BISHOP, HANGING_MINOR_CP_PENALTY),
        (chess.KNIGHT, HANGING_MINOR_CP_PENALTY),
    ):
        for sq in after.pieces(piece_type, side):
            if not after.is_attacked_by(opponent, sq):
                continue

            opp_min = _least_attacker_value(after, opponent, sq)
            our_min = _least_attacker_value(after, side, sq)
            if opp_min is None:
                continue

            if our_min is None:
                risk += hanging_penalty
                continue

            if opp_min <= our_min:
                piece_cp = PIECE_VALUE_CP.get(piece_type, 0)
                risk += max(piece_cp // 2, 120)

    return risk


def scripted_castling_move(board: Board, moves: list[chess.Move]) -> Optional[chess.Move]:
    """Return a safe move from opening scripts focused on fast king-side castling."""
    py_board = board.to_python_chess()
    if py_board.fullmove_number > SCRIPTED_CASTLING_MAX_FULLMOVE:
        return None
    if py_board.is_check():
        return None

    move_by_uci = {move.uci(): move for move in moves}

    if py_board.turn == chess.WHITE:
        white_e4 = py_board.piece_at(chess.E4)
        black_nf6 = py_board.piece_at(chess.F6)
        if (
            white_e4 is not None
            and white_e4.color == chess.WHITE
            and white_e4.piece_type == chess.PAWN
            and black_nf6 is not None
            and black_nf6.color == chess.BLACK
            and black_nf6.piece_type == chess.KNIGHT
        ):
            plan = SCRIPTED_WHITE_VS_NF6
        else:
            plan = SCRIPTED_ITALIAN_WHITE
    else:
        white_d4 = py_board.piece_at(chess.D4)
        white_e4 = py_board.piece_at(chess.E4)
        if white_d4 is not None and white_d4.color == chess.WHITE and white_d4.piece_type == chess.PAWN and (
            white_e4 is None or white_e4.color != chess.WHITE or white_e4.piece_type != chess.PAWN
        ):
            plan = SCRIPTED_QGD_BLACK_VS_D4
        else:
            plan = SCRIPTED_ITALIAN_BLACK

    root_eval_cp = Evaluator.evaluate(py_board)
    root_eval_for_side = root_eval_cp if py_board.turn == chess.WHITE else -root_eval_cp
    for uci in plan:
        move = move_by_uci.get(uci)
        if move is None:
            continue
        if not is_immediate_non_losing_move(py_board, move):
            continue

        after = py_board.copy(stack=False)
        after.push(move)
        after_eval_cp = Evaluator.evaluate(after)
        after_eval_for_side = after_eval_cp if py_board.turn == chess.WHITE else -after_eval_cp
        if after_eval_for_side + SCRIPTED_MAX_STATIC_DROP_CP < root_eval_for_side:
            continue
        return move

    return None


def _capture_gain_light(py_board: chess.Board, move: chess.Move) -> int:
    attacker = py_board.piece_at(move.from_square)
    captured = py_board.piece_at(move.to_square)
    if captured is None and py_board.is_en_passant(move):
        ep_sq = move.to_square - 8 if py_board.turn == chess.WHITE else move.to_square + 8
        captured = py_board.piece_at(ep_sq)
    attacker_v = PIECE_VALUE_LIGHT.get(attacker.piece_type, 0) if attacker else 0
    captured_v = PIECE_VALUE_LIGHT.get(captured.piece_type, 0) if captured else 0
    return captured_v - attacker_v


def prioritized_trade_move(board: Board, moves: list[chess.Move]) -> Optional[chess.Move]:
    """After opening script is done, prioritize safe equal-or-better captures."""
    py_board = board.to_python_chess()
    if not _opening_script_completed(py_board):
        return None

    root_eval_cp = Evaluator.evaluate(py_board)
    root_eval_for_side = root_eval_cp if py_board.turn == chess.WHITE else -root_eval_cp
    candidates = []
    for move in moves:
        if not py_board.is_capture(move):
            continue
        if not is_immediate_non_losing_move(py_board, move):
            continue

        hanging_risk = _post_move_hanging_risk_cp(py_board, move)
        if hanging_risk >= 300:
            continue

        after = py_board.copy(stack=False)
        after.push(move)
        after_eval_cp = Evaluator.evaluate(after)
        after_eval_for_side = after_eval_cp if py_board.turn == chess.WHITE else -after_eval_cp
        if after_eval_for_side + 80 < root_eval_for_side:
            continue

        gain = _capture_gain_light(py_board, move)
        if gain < 0:
            continue
        score = (FORCED_TRADE_WINNING_BONUS if gain > 0 else FORCED_TRADE_EQUAL_BONUS) + _rollout_move_score(py_board, move)
        candidates.append((score, move))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _terminal_reward(result: str, root_player: chess.Color) -> Optional[float]:
    if result == "1-0":
        return 1.0 if root_player == chess.WHITE else 0.0
    if result == "0-1":
        return 1.0 if root_player == chess.BLACK else 0.0
    if result == "1/2-1/2":
        return 0.5
    return None


def _rollout_move_score(py_board: chess.Board, move: chess.Move) -> int:
    score = 0
    if py_board.gives_check(move):
        score += 4

    piece = py_board.piece_at(move.from_square)
    if piece is not None and piece.piece_type == chess.KING and not py_board.is_check() and not _is_effective_endgame(py_board):
        score -= 3

    score -= _king_file_double_push_penalty(py_board, move)
    score -= _king_corner_safety_penalty(py_board, move)

    if py_board.is_capture(move):
        attacker = py_board.piece_at(move.from_square)
        captured = py_board.piece_at(move.to_square)
        if captured is None and py_board.is_en_passant(move):
            ep_capture_sq = move.to_square - 8 if py_board.turn == chess.WHITE else move.to_square + 8
            captured = py_board.piece_at(ep_capture_sq)
        attacker_v = PIECE_VALUE_LIGHT.get(attacker.piece_type, 0) if attacker else 0
        captured_v = PIECE_VALUE_LIGHT.get(captured.piece_type, 0) if captured else 0
        score += 2 * captured_v - attacker_v

        gain = captured_v - attacker_v
        if _opening_script_completed(py_board) and gain >= 0 and is_immediate_non_losing_move(py_board, move):
            score += FORCED_TRADE_WINNING_BONUS if gain > 0 else FORCED_TRADE_EQUAL_BONUS

    score += _queen_trade_bonus(py_board, move)

    score += _trade_preference_bonus(py_board, move)
    score -= int(_immediate_recapture_risk_cp(py_board, move) / RECAPTURE_RISK_CP_MULT)
    score -= int(_post_move_hanging_risk_cp(py_board, move) / RECAPTURE_RISK_CP_MULT)

    if move.promotion is not None:
        score += 6
    return score


def _piece_complexity_units(py_board: chess.Board) -> int:
    return (
        len(py_board.pieces(chess.KNIGHT, chess.WHITE))
        + len(py_board.pieces(chess.BISHOP, chess.WHITE))
        + 2 * len(py_board.pieces(chess.ROOK, chess.WHITE))
        + 3 * len(py_board.pieces(chess.QUEEN, chess.WHITE))
        + len(py_board.pieces(chess.KNIGHT, chess.BLACK))
        + len(py_board.pieces(chess.BISHOP, chess.BLACK))
        + 2 * len(py_board.pieces(chess.ROOK, chess.BLACK))
        + 3 * len(py_board.pieces(chess.QUEEN, chess.BLACK))
    )


def _trade_preference_bonus(py_board: chess.Board, move: chess.Move) -> int:
    """Encourage safe simplification in opening/middlegame via equal-or-better piece trades."""
    if not py_board.is_capture(move):
        return 0

    phase = _game_phase(py_board)
    if phase < TRADE_PHASE_MIN:
        return 0

    attacker = py_board.piece_at(move.from_square)
    captured = py_board.piece_at(move.to_square)
    if captured is None and py_board.is_en_passant(move):
        ep_capture_sq = move.to_square - 8 if py_board.turn == chess.WHITE else move.to_square + 8
        captured = py_board.piece_at(ep_capture_sq)
    if attacker is None or captured is None:
        return 0

    # Encourage exchanging pieces (not pawn trades) and only when not material-losing.
    if attacker.piece_type in (chess.KING, chess.PAWN):
        return 0
    if captured.piece_type in (chess.KING, chess.PAWN):
        return 0

    attacker_v = PIECE_VALUE_LIGHT.get(attacker.piece_type, 0)
    captured_v = PIECE_VALUE_LIGHT.get(captured.piece_type, 0)
    if captured_v < attacker_v:
        return 0

    if not is_immediate_non_losing_move(py_board, move):
        return 0

    base = TRADE_WINNING_BONUS if captured_v > attacker_v else TRADE_EQUAL_BONUS
    complexity = _piece_complexity_units(py_board)
    complexity_factor = 1.0 + min(0.9, complexity / 20.0)
    phase_factor = 0.8 + 0.5 * phase
    return int(base * complexity_factor * phase_factor)


def _rollout_rule_candidates(py_board: chess.Board, moves: list[chess.Move]) -> list[chess.Move]:
    """Basic rollout rules: avoid obvious hanging blunders, then prefer tactical options."""
    if not BASIC_ROLLOUT_RULES_ENABLED:
        return moves

    safe_moves = [move for move in moves if _post_move_hanging_risk_cp(py_board, move) <= BASIC_ROLLOUT_MAX_HANGING_RISK_CP]
    pool = safe_moves if safe_moves else moves

    tactical_safe = [move for move in pool if py_board.is_capture(move) or py_board.gives_check(move)]
    if tactical_safe:
        return tactical_safe
    return pool


def _opponent_one_ply_punish_score(py_board: chess.Board, move: chess.Move) -> int:
    """Cheap tactical score for opponent rollout: punish immediate blunders in one move."""
    score = 0
    if py_board.gives_check(move):
        score += ROLLOUT_OPPONENT_CHECK_BONUS

    if py_board.is_capture(move):
        gain = _capture_gain_light(py_board, move)
        if gain > 0:
            score += ROLLOUT_OPPONENT_WIN_CAPTURE_BONUS + 2 * gain
        elif gain == 0:
            score += ROLLOUT_OPPONENT_EQUAL_CAPTURE_BONUS

    score += _queen_trade_bonus(py_board, move)
    score -= _king_file_double_push_penalty(py_board, move)
    score -= _king_corner_safety_penalty(py_board, move)

    score -= int(_immediate_recapture_risk_cp(py_board, move) / RECAPTURE_RISK_CP_MULT)
    score -= int(_post_move_hanging_risk_cp(py_board, move) / RECAPTURE_RISK_CP_MULT)
    return score


def _select_opponent_rollout_move(
    board: Board,
    rng: random.Random,
    use_biased_rollout: bool,
) -> Optional[chess.Move]:
    moves = board.legal_chess_moves()
    if not moves:
        return None

    if use_biased_rollout:
        py_board = board.to_python_chess()
        candidates = _rollout_rule_candidates(py_board, moves)
        best_score = None
        best_moves = []
        for move in candidates:
            score = _opponent_one_ply_punish_score(py_board, move)
            if best_score is None or score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        if best_moves and rng.random() < ROLLOUT_OPPONENT_PUNISH_BEST_MOVE_PROB:
            return rng.choice(best_moves)
    return rng.choice(moves)


def select_rollout_move(
    board: Board,
    rng: random.Random,
    use_biased_rollout: bool,
    root_player: Optional[chess.Color] = None,
    pure_rollout: bool = False,
) -> Optional[chess.Move]:
    moves = board.legal_chess_moves()
    if not moves:
        return None

    if pure_rollout:
        return rng.choice(moves)

    if root_player is not None and board.turn != root_player:
        return _select_opponent_rollout_move(board, rng, use_biased_rollout)

    scripted = scripted_castling_move(board, moves)
    if scripted is not None:
        return scripted

    if not use_biased_rollout:
        return rng.choice(moves)

    py_board = board.to_python_chess()
    candidates = _rollout_rule_candidates(py_board, moves)

    best_score = None
    best_moves = []
    for move in candidates:
        score = _rollout_move_score(py_board, move)
        if best_score is None or score > best_score:
            best_score = score
            best_moves = [move]
        elif score == best_score:
            best_moves.append(move)

    if len(best_moves) > BASIC_ROLLOUT_TOP_K:
        best_moves = best_moves[:BASIC_ROLLOUT_TOP_K]

    if best_moves and rng.random() < 0.75:
        return rng.choice(best_moves)
    return rng.choice(moves)


def _short_rollout_signal(
    board: Board,
    root_player: chess.Color,
    rng: random.Random,
    rollout_mix_extra_depth: int,
    use_biased_rollout: bool,
) -> float:
    probe = board.copy()
    depth = 0
    while not probe.is_game_over() and depth < rollout_mix_extra_depth:
        move = select_rollout_move(
            probe,
            rng,
            use_biased_rollout,
            root_player,
            pure_rollout=False,
        )
        if move is None:
            break
        probe.push_move(move)
        depth += 1

    reward = _terminal_reward(probe.result(), root_player)
    if reward is None:
        eval_cp = evaluate_cp_for_mcts(probe.to_python_chess())
        eval_for_root = eval_cp if root_player == chess.WHITE else -eval_cp
        return 0.5 + 0.5 * math.tanh(eval_for_root / 350.0)
    return reward


def simulate_rollout_reward(
    node_board: Board,
    root_player: chess.Color,
    rng: random.Random,
    rollout_depth: int,
    use_heuristic_eval: bool,
    heuristic_scale: float,
    rollout_eval_mix_alpha: float,
    rollout_mix_extra_depth: int,
    use_biased_rollout: bool,
) -> float:
    rollout_board = node_board.copy()
    pure_rollout = not use_heuristic_eval
    depth = 0
    while not rollout_board.is_game_over() and depth < rollout_depth:
        move = select_rollout_move(
            rollout_board,
            rng,
            use_biased_rollout,
            root_player,
            pure_rollout=pure_rollout,
        )
        if move is None:
            break
        rollout_board.push_move(move)
        depth += 1

    reward = _terminal_reward(rollout_board.result(), root_player)
    if reward is not None:
        return reward

    if not use_heuristic_eval:
        return 0.5

    eval_cp = evaluate_cp_for_mcts(rollout_board.to_python_chess())
    eval_for_root = eval_cp if root_player == chess.WHITE else -eval_cp
    eval_reward = 0.5 + 0.5 * math.tanh(eval_for_root / max(1.0, heuristic_scale))

    phase = _game_phase(rollout_board.to_python_chess())
    # In opening, rely more on static evaluator; in late phase, trust rollout signal a bit more.
    dynamic_alpha = max(0.15, min(0.55, rollout_eval_mix_alpha - 0.10 * phase + 0.05 * (1.0 - phase)))

    rollout_signal = _short_rollout_signal(
        rollout_board,
        root_player,
        rng,
        max(1, rollout_mix_extra_depth),
        use_biased_rollout,
    )
    return dynamic_alpha * rollout_signal + (1.0 - dynamic_alpha) * eval_reward
