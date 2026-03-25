"""Rule helpers and end-state detection."""
from __future__ import annotations

from engine.board import Board


class Rules:
    """Expose convenience checks for game state."""

    @staticmethod
    def is_check(board: Board) -> bool:
        return board.is_check()

    @staticmethod
    def is_checkmate(board: Board) -> bool:
        return board.is_checkmate()

    @staticmethod
    def is_stalemate(board: Board) -> bool:
        return board.is_stalemate()

    @staticmethod
    def is_game_over(board: Board) -> bool:
        return board.is_game_over()

    @staticmethod
    def result(board: Board) -> str:
        return board.result()
