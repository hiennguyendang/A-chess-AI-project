"""Board abstraction built on top of python-chess."""
from __future__ import annotations

from typing import List, Optional

import chess


class Board:
    """Lightweight wrapper around python-chess Board to keep engine swappable."""

    def __init__(self, fen: Optional[str] = None) -> None:
        self._board = chess.Board(fen=fen) if fen else chess.Board()

    @property
    def turn(self) -> chess.Color:
        """Current side to move."""
        return self._board.turn

    def copy(self) -> "Board":
        """Deep copy of the board state."""
        clone = Board()
        clone._board = self._board.copy()
        return clone

    def push_uci(self, move_uci: str) -> None:
        """Apply a move in UCI format."""
        self._board.push_uci(move_uci)

    def push_move(self, move: chess.Move) -> None:
        """Apply a move object."""
        self._board.push(move)

    def pop(self) -> None:
        """Undo last move."""
        self._board.pop()

    def legal_moves(self) -> List[str]:
        """Return all legal moves in UCI format."""
        return [move.uci() for move in self._board.legal_moves]

    def legal_chess_moves(self) -> List[chess.Move]:
        """Return all legal moves as chess.Move objects."""
        return list(self._board.legal_moves)

    def legal_moves_from(self, file: int, rank: int) -> List[chess.Move]:
        """Return legal moves that start from a given square coordinate."""
        from_square = chess.square(file, rank)
        return [move for move in self._board.legal_moves if move.from_square == from_square]

    def is_game_over(self) -> bool:
        return (
            self.is_checkmate()
            or self.is_stalemate()
            or self.is_draw_by_fifty_move_rule()
            or self.is_draw_by_insufficient_material()
        )

    def result(self) -> str:
        if self.is_checkmate():
            # When side to move is checkmated, that side loses.
            return "0-1" if self._board.turn == chess.WHITE else "1-0"
        if self.is_stalemate() or self.is_draw_by_fifty_move_rule() or self.is_draw_by_insufficient_material():
            return "1/2-1/2"
        return "*"

    def is_check(self) -> bool:
        return self._board.is_check()

    def is_checkmate(self) -> bool:
        return self._board.is_checkmate()

    def is_stalemate(self) -> bool:
        return self._board.is_stalemate()

    def is_draw_by_fifty_move_rule(self) -> bool:
        # 50-move rule means 100 half-moves without pawn move or capture.
        return self._board.halfmove_clock >= 100

    def is_draw_by_insufficient_material(self) -> bool:
        return self._board.is_insufficient_material()

    def fen(self) -> str:
        return self._board.fen()

    def reset(self) -> None:
        """Reset to the standard initial position."""
        self._board.reset()

    def to_python_chess(self) -> chess.Board:
        """Expose underlying board for advanced operations (avoid mutating directly)."""
        return self._board

    def __str__(self) -> str:  # pragma: no cover - delegated to python-chess
        return str(self._board)
