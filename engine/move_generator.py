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

    def ordered_moves(self, board: Board) -> List[chess.Move]:
        """Basic move ordering: captures first, then others."""
        moves = self.generate(board)
        captures = [m for m in moves if board.to_python_chess().is_capture(m)]
        quiets = [m for m in moves if not board.to_python_chess().is_capture(m)]
        return captures + quiets
