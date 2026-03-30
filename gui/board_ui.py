"""Board UI widget using PyQt5."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

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
        min_size: int = 480,
        coord_font_scale: float = 0.14,
        coord_font_min: int = 8,
    ):
        super().__init__()
        self.board = board
        self.theme = theme
        self.move_made_callback = move_made_callback
        self.can_human_move = can_human_move
        self.is_flipped = False
        self.selected_square: Optional[Square] = None
        self.highlight_targets: List[Square] = []
        self.pending_promotion: Optional[dict[str, Any]] = None
        self.coord_font_scale = coord_font_scale
        self.coord_font_min = coord_font_min
        self.piece_pixmaps = self._load_piece_pixmaps()
        self.setMinimumSize(min_size, min_size)

    def set_board(self, board: Board) -> None:
        self.board = board
        self.selected_square = None
        self.highlight_targets = []
        self.pending_promotion = None
        self.update()

    def update_board(self) -> None:
        self.update()

    def set_flipped(self, flipped: bool) -> None:
        self.is_flipped = flipped
        self.selected_square = None
        self.highlight_targets = []
        self.pending_promotion = None
        self.update()

    def begin_promotion_selection(
        self,
        src: Square,
        dst: Square,
        piece_color: chess.Color,
        options: List[str],
        on_selected: Callable[[str], None],
    ) -> None:
        normalized = [opt.lower() for opt in options if opt.lower() in {"q", "r", "b", "n"}]
        if not normalized:
            return

        self.pending_promotion = {
            "src": src,
            "dst": dst,
            "color": piece_color,
            "options": normalized,
            "on_selected": on_selected,
        }
        self.selected_square = None
        self.highlight_targets = []
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # pragma: no cover - UI interaction
        board_rect, square_size, _ = self._board_geometry()
        if square_size <= 0:
            return

        if self.pending_promotion is not None:
            self._handle_promotion_click(event.x(), event.y(), board_rect, square_size)
            return

        if not self.can_human_move():
            return

        if not board_rect.contains(event.x(), event.y()):
            return

        rel_x = event.x() - board_rect.left()
        rel_y = event.y() - board_rect.top()
        display_col = int(rel_x // square_size)
        display_row = int(rel_y // square_size)

        if display_col < 0 or display_col > 7 or display_row < 0 or display_row > 7:
            return

        file, rank = self._from_display_coords(display_col, display_row)

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

        src = self.selected_square
        move_uci = self._square_to_uci(src, clicked)
        legal_uci = self.board.legal_moves()

        promotion_options = [opt for opt in ("q", "r", "b", "n") if (move_uci + opt) in legal_uci]
        if promotion_options:
            piece = self.board.to_python_chess().piece_at(chess.square(src[0], src[1]))
            if piece is not None:
                self.begin_promotion_selection(
                    src=src,
                    dst=clicked,
                    piece_color=piece.color,
                    options=promotion_options,
                    on_selected=lambda suffix, base=move_uci: self.move_made_callback(base + suffix),
                )
            return

        if move_uci in legal_uci:
            self.move_made_callback(move_uci)
        self.selected_square = None
        self.highlight_targets = []
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # pragma: no cover - UI drawing
        painter = QtGui.QPainter(self)
        board_rect, square_size, _ = self._board_geometry()
        if square_size <= 0:
            return

        board_left = board_rect.left()
        board_top = board_rect.top()
        coord_font = QtGui.QFont("Segoe UI", max(self.coord_font_min, int(square_size * self.coord_font_scale)))
        coord_font.setBold(True)
        painter.setFont(coord_font)

        for file in range(8):
            for rank in range(8):
                display_col, display_row = self._to_display_coords(file, rank)
                color = self.theme.light_square if (file + rank) % 2 == 0 else self.theme.dark_square
                if self.selected_square == (file, rank):
                    color = self.theme.highlight
                square_rect = QtCore.QRectF(
                    board_left + display_col * square_size,
                    board_top + display_row * square_size,
                    square_size,
                    square_size,
                )
                painter.fillRect(square_rect, QtGui.QColor(color))

                if (file, rank) in self.highlight_targets:
                    painter.setBrush(QtGui.QColor(self.theme.move_hint))
                    painter.setPen(QtCore.Qt.NoPen)
                    center_x = board_left + display_col * square_size + square_size / 2
                    center_y = board_top + display_row * square_size + square_size / 2
                    radius = square_size * 0.12
                    painter.drawEllipse(QtCore.QPointF(center_x, center_y), radius, radius)

                piece = self._piece_at(file, rank)
                if piece is not None:
                    if not self._draw_piece_image(
                        painter,
                        piece,
                        display_col,
                        display_row,
                        square_size,
                        board_left,
                        board_top,
                    ):
                        piece_symbol = UNICODE_PIECES[piece.symbol()]
                        self._draw_piece_fallback(
                            painter,
                            piece_symbol,
                            display_col,
                            display_row,
                            square_size,
                            board_left,
                            board_top,
                        )

                # Draw coordinate labels inside edge squares (as in the reference).
                is_light_square = (file + rank) % 2 == 0
                coord_color = self.theme.coord_dark if is_light_square else self.theme.coord_light
                painter.setPen(QtGui.QColor(coord_color))

                inset = square_size * 0.08
                if display_row == 7:
                    file_char = chr(ord("a") + file)
                    file_rect = QtCore.QRectF(
                        board_left + display_col * square_size,
                        board_top + display_row * square_size,
                        square_size - inset,
                        square_size - inset,
                    )
                    painter.drawText(file_rect, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom, file_char)

                if display_col == 0:
                    rank_char = str(rank + 1)
                    rank_rect = QtCore.QRectF(
                        board_left + display_col * square_size + inset,
                        board_top + display_row * square_size,
                        square_size - inset,
                        square_size - inset,
                    )
                    painter.drawText(rank_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, rank_char)

        result_text = self._game_result_text()
        if result_text:
            painter.fillRect(board_rect, QtGui.QColor(0, 0, 0, 88))

            result_font = QtGui.QFont("Segoe UI", max(24, int(square_size * 0.72)))
            result_font.setBold(True)
            painter.setFont(result_font)

            # Draw a dark shadow first so yellow text remains readable on any square color.
            painter.setPen(QtGui.QColor(20, 20, 20, 230))
            painter.drawText(board_rect.translated(2.0, 2.0), QtCore.Qt.AlignCenter, result_text)
            painter.setPen(QtGui.QColor("#F5D547"))
            painter.drawText(board_rect, QtCore.Qt.AlignCenter, result_text)

        if self.pending_promotion is not None:
            self._draw_promotion_overlay(painter, board_rect, square_size)

    def _piece_at(self, file: int, rank: int) -> Optional[chess.Piece]:
        sq = chess.square(file, rank)
        return self.board.to_python_chess().piece_at(sq)

    def _load_piece_pixmaps(self) -> dict[str, QtGui.QPixmap]:
        base_dir = Path(__file__).resolve().parent.parent / "imgs" / "piece"
        pixmaps: dict[str, QtGui.QPixmap] = {}
        keys = ["wp", "wn", "wb", "wr", "wq", "wk", "bp", "bn", "bb", "br", "bq", "bk"]
        for key in keys:
            file_path = base_dir / f"{key}.png"
            if not file_path.exists():
                continue
            pixmap = QtGui.QPixmap(str(file_path))
            if not pixmap.isNull():
                pixmaps[key] = pixmap
        return pixmaps

    def _piece_key(self, piece: chess.Piece) -> str:
        color = "w" if piece.color == chess.WHITE else "b"
        return f"{color}{piece.symbol().lower()}"

    def _draw_piece_image(
        self,
        painter: QtGui.QPainter,
        piece: chess.Piece,
        display_col: int,
        display_row: int,
        square_size: float,
        board_left: float,
        board_top: float,
    ) -> bool:
        key = self._piece_key(piece)
        pixmap = self.piece_pixmaps.get(key)
        if pixmap is None:
            return False

        target_size = int(square_size * 0.86)
        if target_size <= 0:
            return False

        x = int(board_left + display_col * square_size + (square_size - target_size) / 2)
        y = int(board_top + display_row * square_size + (square_size - target_size) / 2)
        target_rect = QtCore.QRect(x, y, target_size, target_size)
        scaled = pixmap.scaled(target_size, target_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        painter.drawPixmap(target_rect, scaled)
        return True

    def _draw_piece_fallback(
        self,
        painter: QtGui.QPainter,
        piece_symbol: str,
        display_col: int,
        display_row: int,
        square_size: float,
        board_left: float,
        board_top: float,
    ) -> None:
        piece_font = QtGui.QFont("Segoe UI Symbol", int(square_size / 2.0))
        piece_font.setStyleStrategy(QtGui.QFont.PreferAntialias)
        piece_rect = QtCore.QRectF(
            board_left + display_col * square_size,
            board_top + display_row * square_size,
            square_size,
            square_size,
        )
        painter.setFont(piece_font)
        painter.setPen(QtGui.QColor(self.theme.black_piece))
        painter.drawText(piece_rect, QtCore.Qt.AlignCenter, piece_symbol)

    def _to_display_coords(self, file: int, rank: int) -> Tuple[int, int]:
        if self.is_flipped:
            return 7 - file, rank
        return file, 7 - rank

    def _from_display_coords(self, display_col: int, display_row: int) -> Tuple[int, int]:
        if self.is_flipped:
            return 7 - display_col, display_row
        return display_col, 7 - display_row

    def _board_geometry(self) -> Tuple[QtCore.QRectF, float, float]:
        outer_margin = max(2.0, min(self.width(), self.height()) * 0.01)
        board_size = min(self.width() - outer_margin * 2, self.height() - outer_margin * 2)
        if board_size <= 0:
            return QtCore.QRectF(), 0.0, outer_margin

        board_left = (self.width() - board_size) / 2
        board_top = (self.height() - board_size) / 2
        board_rect = QtCore.QRectF(board_left, board_top, board_size, board_size)
        return board_rect, board_size / 8, outer_margin

    def _game_result_text(self) -> str:
        board = self.board.to_python_chess()
        if not board.is_game_over():
            return ""

        if board.is_checkmate():
            winner = "Black" if board.turn == chess.WHITE else "White"
            return f"{winner} Win"
        return "Draw"

    def _promotion_option_rects(self, board_rect: QtCore.QRectF, square_size: float) -> List[QtCore.QRectF]:
        assert self.pending_promotion is not None
        options = self.pending_promotion["options"]
        count = len(options)
        box_size = max(32.0, square_size * 0.9)
        gap = max(6.0, square_size * 0.12)
        total_width = count * box_size + (count - 1) * gap
        start_x = board_rect.left() + (board_rect.width() - total_width) / 2
        y = board_rect.top() + (board_rect.height() - box_size) / 2

        return [
            QtCore.QRectF(start_x + idx * (box_size + gap), y, box_size, box_size)
            for idx in range(count)
        ]

    def _piece_key_from_choice(self, color: chess.Color, choice: str) -> str:
        prefix = "w" if color == chess.WHITE else "b"
        return f"{prefix}{choice}"

    def _draw_promotion_overlay(
        self,
        painter: QtGui.QPainter,
        board_rect: QtCore.QRectF,
        square_size: float,
    ) -> None:
        assert self.pending_promotion is not None
        painter.fillRect(board_rect, QtGui.QColor(12, 10, 18, 168))

        title_rect = QtCore.QRectF(board_rect.left(), board_rect.top() + board_rect.height() * 0.33, board_rect.width(), 24)
        title_font = QtGui.QFont("Segoe UI", max(11, int(square_size * 0.2)))
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QtGui.QColor("#F6F0FF"))
        painter.drawText(title_rect, QtCore.Qt.AlignCenter, "Choose promotion")

        option_rects = self._promotion_option_rects(board_rect, square_size)
        color = self.pending_promotion["color"]
        options = self.pending_promotion["options"]

        for idx, rect in enumerate(option_rects):
            painter.setPen(QtGui.QColor("#C7B9F1"))
            painter.setBrush(QtGui.QColor("#2F2450"))
            painter.drawRoundedRect(rect, 6, 6)

            key = self._piece_key_from_choice(color, options[idx])
            pixmap = self.piece_pixmaps.get(key)
            if pixmap is not None:
                target_size = int(rect.height() * 0.78)
                x = int(rect.left() + (rect.width() - target_size) / 2)
                y = int(rect.top() + (rect.height() - target_size) / 2)
                scaled = pixmap.scaled(target_size, target_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                painter.drawPixmap(QtCore.QRect(x, y, target_size, target_size), scaled)
            else:
                symbol = options[idx].upper() if color == chess.WHITE else options[idx].lower()
                text = UNICODE_PIECES.get(symbol, options[idx].upper())
                icon_font = QtGui.QFont("Segoe UI Symbol", int(rect.height() * 0.62))
                painter.setFont(icon_font)
                painter.setPen(QtGui.QColor(self.theme.text_primary if hasattr(self.theme, "text_primary") else "#F6F0FF"))
                painter.drawText(rect, QtCore.Qt.AlignCenter, text)

    def _handle_promotion_click(
        self,
        x: float,
        y: float,
        board_rect: QtCore.QRectF,
        square_size: float,
    ) -> None:
        assert self.pending_promotion is not None
        option_rects = self._promotion_option_rects(board_rect, square_size)
        click_point = QtCore.QPointF(x, y)
        for idx, rect in enumerate(option_rects):
            if rect.contains(click_point):
                callback = self.pending_promotion["on_selected"]
                choice = self.pending_promotion["options"][idx]
                self.pending_promotion = None
                callback(choice)
                self.update()
                return

    @staticmethod
    def _square_to_uci(src: Square, dst: Square) -> str:
        def to_square(square: Square) -> str:
            file, rank = square
            return f"{chr(ord('a') + file)}{rank + 1}"

        return to_square(src) + to_square(dst)
