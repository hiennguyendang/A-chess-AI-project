"""Board UI widget using PyQt5."""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import chess
from PyQt5 import QtCore, QtGui, QtWidgets

from engine.board import Board
from gui.themes import Theme

Square = Tuple[int, int]

UNICODE_PIECES = {
    "P": "♙",
    "N": "♘",
    "B": "♗",
    "R": "♖",
    "Q": "♕",
    "K": "♔",
    "p": "♟",
    "n": "♞",
    "b": "♝",
    "r": "♜",
    "q": "♛",
    "k": "♚",
}


class BoardWidget(QtWidgets.QWidget):
    """Simple grid-based board widget with click-to-move."""

    def __init__(
        self,
        board: Board,
        theme: Theme,
        move_made_callback: Callable[[str], None],
        can_human_move: Callable[[], bool],
    ):
        super().__init__()
        self.board = board
        self.theme = theme
        self.move_made_callback = move_made_callback
        self.can_human_move = can_human_move
        self.selected_square: Optional[Square] = None
        self.highlight_targets: List[Square] = []
        self.setMinimumSize(480, 480)

    def set_board(self, board: Board) -> None:
        self.board = board
        self.selected_square = None
        self.highlight_targets = []
        self.update()

    def update_board(self) -> None:
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # pragma: no cover - UI interaction
        if not self.can_human_move():
            return

        size = min(self.width(), self.height())
        square_size = size / 8
        file = int(event.x() // square_size)
        rank = 7 - int(event.y() // square_size)

        if file < 0 or file > 7 or rank < 0 or rank > 7:
            return

        clicked = (file, rank)

        if self.selected_square is None:
            piece = self.board.to_python_chess().piece_at(chess.square(file, rank))
            if piece is None or piece.color != self.board.turn:
                return
            self.selected_square = clicked
            self.highlight_targets = [
                (chess.square_file(move.to_square), chess.square_rank(move.to_square))
                for move in self.board.legal_moves_from(file, rank)
            ]
            self.update()
            return

        move_uci = self._square_to_uci(self.selected_square, clicked)
        legal_uci = self.board.legal_moves()
        if move_uci not in legal_uci and (move_uci + "q") in legal_uci:
            move_uci = move_uci + "q"

        if move_uci in legal_uci:
            self.move_made_callback(move_uci)
        self.selected_square = None
        self.highlight_targets = []
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # pragma: no cover - UI drawing
        painter = QtGui.QPainter(self)
        size = min(self.width(), self.height())
        square_size = size / 8

        for file in range(8):
            for rank in range(8):
                color = self.theme.light_square if (file + rank) % 2 == 0 else self.theme.dark_square
                if self.selected_square == (file, rank):
                    color = self.theme.highlight
                painter.fillRect(file * square_size, (7 - rank) * square_size, square_size, square_size, QtGui.QColor(color))

                if (file, rank) in self.highlight_targets:
                    painter.setBrush(QtGui.QColor(self.theme.move_hint))
                    painter.setPen(QtCore.Qt.NoPen)
                    center_x = file * square_size + square_size / 2
                    center_y = (7 - rank) * square_size + square_size / 2
                    radius = square_size * 0.12
                    painter.drawEllipse(QtCore.QPointF(center_x, center_y), radius, radius)

                piece = self._piece_symbol_at(file, rank)
                if piece:
                    painter.setFont(QtGui.QFont("Segoe UI Symbol", int(square_size / 2.1)))
                    painter.setPen(QtGui.QColor(self.theme.piece_color))
                    painter.drawText(QtCore.QRectF(file * square_size, (7 - rank) * square_size, square_size, square_size),
                                     QtCore.Qt.AlignCenter, piece)

    def _piece_symbol_at(self, file: int, rank: int) -> str:
        sq = chess.square(file, rank)
        piece = self.board.to_python_chess().piece_at(sq)
        if piece is None:
            return ""
        return UNICODE_PIECES[piece.symbol()]

    @staticmethod
    def _square_to_uci(src: Square, dst: Square) -> str:
        def to_square(square: Square) -> str:
            file, rank = square
            return f"{chr(ord('a') + file)}{rank + 1}"

        return to_square(src) + to_square(dst)
