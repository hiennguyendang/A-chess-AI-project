"""Move generation utilities built on python-chess."""
from __future__ import annotations

import chess
from typing import List

from engine.board import Board


class MoveGenerator:
    """Generate legal moves and ordering hints for search algorithms."""

    def __init__(self) -> None:
        self._killer_moves = []  # TODO: add killer move heuristic for ordering

    def generate(self, board: Board) -> List[chess.Move]:
        """Return legal moves as chess.Move objects."""
        return list(board.to_python_chess().legal_moves)

    def _piece_values(self):
        return {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20_000,
        }

    def _captured_piece(self, py_board: chess.Board, move: chess.Move):
        if not py_board.is_capture(move):
            return None
        if py_board.is_en_passant(move):
            capture_square = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
            return py_board.piece_at(capture_square)
        return py_board.piece_at(move.to_square)

    def _see_gain(self, py_board: chess.Board, move: chess.Move) -> int | None:
        """Return static exchange eval in centipawns when available."""
        try:
            return int(py_board.see(move))
        except Exception:
            return None

    def _move_score(self, py_board: chess.Board, move: chess.Move) -> int:
        piece = py_board.piece_at(move.from_square)
        if piece is None:
            return -10_000

        piece_values = self._piece_values()

        score = 0
        if py_board.is_castling(move):
            score += 2_000

        if py_board.gives_check(move):
            score += 120

        captured = self._captured_piece(py_board, move)
        captured_value = piece_values[captured.piece_type] if captured is not None else 0
        if captured is not None:
            score += 10 * captured_value - piece_values[piece.piece_type]
            see_gain = self._see_gain(py_board, move)
            if see_gain is not None:
                score += see_gain * 6
                if see_gain < 0 and not py_board.gives_check(move):
                    score += see_gain * 18

        if move.promotion is not None:
            score += 800

        after = py_board.copy(stack=False)
        after.push(move)
        opponent = after.turn
        side = not opponent
        attacked = after.is_attacked_by(opponent, move.to_square)
        defended = after.is_attacked_by(side, move.to_square)
        if attacked and not defended:
            score -= piece_values[piece.piece_type]
        elif attacked and defended:
            opp_attackers = [
                piece_values.get(after.piece_at(sq).piece_type, 0)
                for sq in after.attackers(opponent, move.to_square)
                if after.piece_at(sq) is not None
            ]
            our_defenders = [
                piece_values.get(after.piece_at(sq).piece_type, 0)
                for sq in after.attackers(side, move.to_square)
                if after.piece_at(sq) is not None
            ]
            if opp_attackers and our_defenders and min(opp_attackers) <= min(our_defenders):
                score -= piece_values[piece.piece_type] // 3

            pressure_gap = len(opp_attackers) - len(our_defenders)
            if pressure_gap > 0:
                score -= pressure_gap * (piece_values[piece.piece_type] // 5)

            # Explicitly discourage "minor piece takes protected pawn" patterns.
            if (
                captured is not None
                and captured.piece_type == chess.PAWN
                and piece.piece_type in (chess.KNIGHT, chess.BISHOP)
                and opp_attackers
                and our_defenders
                and min(opp_attackers) <= min(our_defenders)
            ):
                score -= max(180, piece_values[piece.piece_type] - captured_value)

        if (py_board.is_capture(move) or move.promotion is not None) and not self.is_non_losing_tactical_move(py_board, move):
            score -= 2_400

        return score

    def is_non_losing_tactical_move(self, py_board: chess.Board, move: chess.Move) -> bool:
        piece = py_board.piece_at(move.from_square)
        if piece is None:
            return False

        piece_values = self._piece_values()
        moved_value = piece_values[piece.piece_type]
        captured = self._captured_piece(py_board, move)
        captured_value = piece_values[captured.piece_type] if captured is not None else 0

        see_gain = self._see_gain(py_board, move)
        if see_gain is not None:
            # Reject clear tactical losses unless they are checking moves.
            if see_gain < -30 and not py_board.gives_check(move):
                return False
            if see_gain >= 0:
                return True

        after = py_board.copy(stack=False)
        after.push(move)

        opponent = after.turn
        side = not opponent
        dst = move.to_square

        opp_attackers = [
            piece_values.get(after.piece_at(sq).piece_type, 0)
            for sq in after.attackers(opponent, dst)
            if after.piece_at(sq) is not None
        ]
        our_defenders = [
            piece_values.get(after.piece_at(sq).piece_type, 0)
            for sq in after.attackers(side, dst)
            if after.piece_at(sq) is not None
        ]

        if not opp_attackers:
            return True
        if not our_defenders:
            return captured_value >= moved_value

        if min(opp_attackers) <= min(our_defenders) and captured_value < moved_value:
            return False
        if len(opp_attackers) > len(our_defenders) and captured_value < moved_value:
            return False
        return True

    def ordered_moves(self, board: Board) -> List[chess.Move]:
        """Tactical move ordering for Alpha-Beta stability at finite depth."""
        moves = self.generate(board)
        py_board = board.to_python_chess()
        return sorted(moves, key=lambda move: self._move_score(py_board, move), reverse=True)
