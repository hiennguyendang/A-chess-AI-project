from __future__ import annotations

from typing import Optional

import chess
from PyQt5 import QtCore, QtWidgets

from engine.board import Board
from gui.board_ui import BoardWidget
from gui.themes import Theme


class DistributedBenchmarkMonitor:
    """Small live window to observe the currently running benchmark game."""

    def __init__(self) -> None:
        self.qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        self.theme = Theme.chesscom()

        self.window = QtWidgets.QMainWindow()
        self.window.setWindowTitle("Distributed Benchmark Monitor")
        self.window.resize(900, 720)

        root = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        root.setLayout(layout)
        self.window.setCentralWidget(root)

        self.header_label = QtWidgets.QLabel("Benchmark Monitor")
        self.header_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(self.header_label)

        self.meta_label = QtWidgets.QLabel("Waiting for first game...")
        self.meta_label.setWordWrap(True)
        layout.addWidget(self.meta_label)

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.live_board = Board()
        self.board_widget = BoardWidget(
            board=self.live_board,
            theme=self.theme,
            move_made_callback=lambda _: None,
            can_human_move=lambda: False,
            min_size=560,
        )
        layout.addWidget(self.board_widget, 1)

        self.window.show()
        self._pump()

    def _pump(self) -> None:
        self.qt_app.processEvents(QtCore.QEventLoop.AllEvents, 10)

    def on_game_start(self, scenario_id: str, game_idx: int, game_total: int, white_engine: str, black_engine: str) -> None:
        self.header_label.setText(f"Scenario {scenario_id} | game {game_idx}/{game_total}")
        self.meta_label.setText(f"White: {white_engine}    vs    Black: {black_engine}")
        self.status_label.setText("Game started")
        self._pump()

    def on_move(self, board: chess.Board, plies: int) -> None:
        self.live_board = Board(fen=board.fen())
        self.board_widget.set_board(self.live_board)
        side = "White" if board.turn == chess.WHITE else "Black"
        check = " (check)" if board.is_check() else ""
        self.status_label.setText(f"Plies: {plies} | Turn: {side}{check}")
        self._pump()

    def on_game_finish(self, board: chess.Board) -> None:
        result = board.result(claim_draw=False)
        self.live_board = Board(fen=board.fen())
        self.board_widget.set_board(self.live_board)
        self.status_label.setText(f"Finished: {result}")
        self._pump()

    def close(self) -> None:
        if self.window is not None:
            self.window.close()
            self._pump()


def maybe_create_monitor(enabled: bool) -> Optional[DistributedBenchmarkMonitor]:
    if not enabled:
        return None
    return DistributedBenchmarkMonitor()
