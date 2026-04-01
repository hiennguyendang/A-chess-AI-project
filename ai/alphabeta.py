"""Minimax with alpha-beta pruning."""
from __future__ import annotations

import chess
from typing import Optional, Tuple

from ai import search_parallel as parallel
from engine.board import Board
from engine.evaluator import Evaluator
from engine.move_generator import MoveGenerator


class AlphaBetaAI:
    """Alpha-beta pruned minimax with configurable depth."""

    def __init__(self, depth: int = 3, num_processes: int = 1) -> None:
        self.depth = depth
        self.num_processes = max(1, num_processes)
        self.move_generator = MoveGenerator()

    def choose_move(self, board: Board) -> chess.Move:
        if parallel.should_parallelize_alphabeta(self.depth, self.num_processes, len(board.legal_chess_moves())):
            move = parallel.choose_alphabeta_move_parallel(board, self.depth, self.num_processes)
            if move is not None:
                return move

        score, best_move = self._alphabeta(board, self.depth, -10_000_000, 10_000_000, maximizing=board.turn == chess.WHITE)
        if best_move is None:
            raise ValueError("No legal moves available")
        return best_move

    def _alphabeta(
        self,
        board: Board,
        depth: int,
        alpha: int,
        beta: int,
        maximizing: bool,
    ) -> Tuple[int, Optional[chess.Move]]:
        if depth == 0 or board.is_game_over():
            return Evaluator.evaluate(board.to_python_chess()), None

        best_move = None
        moves = self.move_generator.ordered_moves(board)

        if maximizing:
            value = -10_000_000
            for move in moves:
                board.push_move(move)
                score, _ = self._alphabeta(board, depth - 1, alpha, beta, False)
                board.pop()
                if score > value:
                    value, best_move = score, move
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value, best_move

        value = 10_000_000
        for move in moves:
            board.push_move(move)
            score, _ = self._alphabeta(board, depth - 1, alpha, beta, True)
            board.pop()
            if score < value:
                value, best_move = score, move
            beta = min(beta, value)
            if beta <= alpha:
                break
        return value, best_move
