"""Minimax with alpha-beta pruning."""
from __future__ import annotations

import chess
from typing import Optional, Tuple

from ai import search_parallel as parallel
from ai.opening_book import choose_italian_castling_move
from engine.board import Board
from engine.evaluator import Evaluator, MATE_SCORE
from engine.move_generator import MoveGenerator


class AlphaBetaAI:
    """Alpha-beta pruned minimax with configurable depth."""

    INF_SCORE = 10_000_000
    QUIESCENCE_MAX_DEPTH = 12

    def __init__(self, depth: int = 3, num_processes: int = 1, use_opening_book: bool = False) -> None:
        self.depth = depth
        self.num_processes = max(1, num_processes)
        self.use_opening_book = use_opening_book
        self.move_generator = MoveGenerator()

    def choose_move(self, board: Board) -> chess.Move:
        if self.use_opening_book:
            opening_move = choose_italian_castling_move(board, board.legal_chess_moves())
            if opening_move is not None:
                return opening_move

        if parallel.should_parallelize_alphabeta(self.depth, self.num_processes, len(board.legal_chess_moves())):
            move = parallel.choose_alphabeta_move_parallel(board, self.depth, self.num_processes)
            if move is not None:
                return move

        score, best_move = self._alphabeta(
            board,
            self.depth,
            -self.INF_SCORE,
            self.INF_SCORE,
            maximizing=board.turn == chess.WHITE,
            ply_from_root=0,
        )
        if best_move is None:
            raise ValueError("No legal moves available")
        return best_move

    def _evaluate_with_mate_distance(self, board: Board, ply_from_root: int) -> int:
        score = Evaluator.evaluate(board.to_python_chess())
        if score >= MATE_SCORE:
            return score - ply_from_root
        if score <= -MATE_SCORE:
            return score + ply_from_root
        return score

    def _quiescence_moves(self, board: Board) -> list[chess.Move]:
        py_board = board.to_python_chess()
        ordered = self.move_generator.ordered_moves(board)
        if py_board.is_check():
            return ordered

        tactical_moves: list[chess.Move] = []
        for move in ordered:
            if py_board.gives_check(move):
                tactical_moves.append(move)
                continue
            if py_board.is_capture(move) or move.promotion is not None:
                if self.move_generator.is_non_losing_tactical_move(py_board, move):
                    tactical_moves.append(move)
        return tactical_moves

    def _quiescence(
        self,
        board: Board,
        alpha: int,
        beta: int,
        maximizing: bool,
        qdepth: int,
        ply_from_root: int,
    ) -> Tuple[int, Optional[chess.Move]]:
        if board.is_game_over():
            return self._evaluate_with_mate_distance(board, ply_from_root), None

        stand_pat = self._evaluate_with_mate_distance(board, ply_from_root)
        best_move = None

        if maximizing:
            if stand_pat >= beta:
                return stand_pat, None
            alpha = max(alpha, stand_pat)
            best_score = stand_pat
        else:
            if stand_pat <= alpha:
                return stand_pat, None
            beta = min(beta, stand_pat)
            best_score = stand_pat

        if qdepth <= 0:
            return best_score, None

        moves = self._quiescence_moves(board)
        if not moves:
            return best_score, None

        if maximizing:
            for move in moves:
                board.push_move(move)
                score, _ = self._quiescence(board, alpha, beta, False, qdepth - 1, ply_from_root + 1)
                board.pop()
                if score > best_score:
                    best_score, best_move = score, move
                alpha = max(alpha, best_score)
                if alpha >= beta:
                    break
            return best_score, best_move

        for move in moves:
            board.push_move(move)
            score, _ = self._quiescence(board, alpha, beta, True, qdepth - 1, ply_from_root + 1)
            board.pop()
            if score < best_score:
                best_score, best_move = score, move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return best_score, best_move

    def _alphabeta(
        self,
        board: Board,
        depth: int,
        alpha: int,
        beta: int,
        maximizing: bool,
        ply_from_root: int = 0,
    ) -> Tuple[int, Optional[chess.Move]]:
        if board.is_game_over():
            return self._evaluate_with_mate_distance(board, ply_from_root), None
        if depth == 0:
            return self._quiescence(
                board,
                alpha,
                beta,
                maximizing,
                self.QUIESCENCE_MAX_DEPTH,
                ply_from_root,
            )

        best_move = None
        moves = self.move_generator.ordered_moves(board)

        if maximizing:
            value = -self.INF_SCORE
            for move in moves:
                board.push_move(move)
                score, _ = self._alphabeta(board, depth - 1, alpha, beta, False, ply_from_root + 1)
                board.pop()
                if score > value:
                    value, best_move = score, move
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value, best_move

        value = self.INF_SCORE
        for move in moves:
            board.push_move(move)
            score, _ = self._alphabeta(board, depth - 1, alpha, beta, True, ply_from_root + 1)
            board.pop()
            if score < value:
                value, best_move = score, move
            beta = min(beta, value)
            if beta <= alpha:
                break
        return value, best_move
