"""Plain minimax search (no pruning)."""
from __future__ import annotations

import chess
from typing import Optional, Tuple

from ai import search_parallel as parallel
from engine.board import Board
from engine.evaluator import Evaluator
from engine.move_generator import MoveGenerator


class MinimaxAI:
    """Basic minimax engine. Suitable as a baseline or teaching reference."""

    def __init__(self, depth: int = 2, num_processes: int = 1) -> None:
        self.depth = depth
        self.num_processes = max(1, num_processes)
        self.move_generator = MoveGenerator()

    def choose_move(self, board: Board) -> chess.Move:
        """Return the best move for the current player."""
        if parallel.should_parallelize_minimax(self.depth, self.num_processes, len(board.legal_chess_moves())):
            move = parallel.choose_minimax_move_parallel(board, self.depth, self.num_processes)
            if move is not None:
                return move

        _, best_move = self._minimax(board, self.depth, maximizing=board.turn == chess.WHITE)
        if best_move is None:
            raise ValueError("No legal moves available")
        return best_move

    def _minimax(self, board: Board, depth: int, maximizing: bool) -> Tuple[int, Optional[chess.Move]]:
        if depth == 0 or board.is_game_over():
            return Evaluator.evaluate(board.to_python_chess()), None

        best_score = -10_000_000 if maximizing else 10_000_000
        best_move = None
        for move in self.move_generator.generate(board):
            board.push_move(move)
            score, _ = self._minimax(board, depth - 1, not maximizing)
            board.pop()

            if maximizing and score > best_score:
                best_score, best_move = score, move
            if not maximizing and score < best_score:
                best_score, best_move = score, move
        return best_score, best_move
