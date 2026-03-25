"""PyQt5 application bootstrap."""
from __future__ import annotations

import sys

import chess
from PyQt5 import QtCore, QtWidgets

from ai.alphabeta import AlphaBetaAI
from ai.mcts import MCTS
from config.settings import Settings
from engine.board import Board
from gui.board_ui import BoardWidget
from gui.themes import Theme


class ChessAIApplication:
    """High-level GUI orchestrator."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.qt_app = QtWidgets.QApplication(sys.argv)
        self.window = MainWindow(settings=settings)

    def run(self) -> None:
        self.window.show()
        sys.exit(self.qt_app.exec_())


class MainWindow(QtWidgets.QMainWindow):
    """Main window with board and controls."""

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.setWindowTitle("Chess AI")
        self.settings = settings
        self.board = Board()
        self.alpha_beta = AlphaBetaAI(depth=settings.default_depth)
        self.mcts = MCTS(simulations=settings.default_simulations)
        self.human_color = chess.WHITE
        self.game_mode = "human_vs_ai"
        self.active_ai = "alphabeta"
        self.white_ai = "alphabeta"
        self.black_ai = "mcts"
        self.ai_timer = QtCore.QTimer(self)
        self.ai_timer.setInterval(self.settings.ai_turn_interval_ms)
        self.ai_timer.timeout.connect(self._on_ai_timer_tick)

        self.theme = Theme.dark()
        self._init_ui()
        self._apply_theme()
        self._update_control_visibility()
        self._refresh_status()

    def _init_ui(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.board_widget = BoardWidget(
            board=self.board,
            theme=self.theme,
            move_made_callback=self.on_human_move,
            can_human_move=self._can_human_move,
        )
        layout.addWidget(self.board_widget)

        controls = self._build_controls()
        layout.addLayout(controls)

    def _build_controls(self) -> QtWidgets.QVBoxLayout:
        panel = QtWidgets.QVBoxLayout()
        panel.setSpacing(8)

        title = QtWidgets.QLabel("Chess AI Control")
        title.setObjectName("title")
        panel.addWidget(title)

        mode_label = QtWidgets.QLabel("Mode")
        panel.addWidget(mode_label)
        self.mode_selector = QtWidgets.QComboBox()
        self.mode_selector.addItems(["human_vs_ai", "ai_vs_ai"])
        self.mode_selector.currentTextChanged.connect(self.on_mode_changed)
        panel.addWidget(self.mode_selector)

        side_label = QtWidgets.QLabel("Human Side")
        panel.addWidget(side_label)
        self.human_side_selector = QtWidgets.QComboBox()
        self.human_side_selector.addItems(["white", "black"])
        self.human_side_selector.currentTextChanged.connect(self.on_human_side_changed)
        panel.addWidget(self.human_side_selector)

        ai_label = QtWidgets.QLabel("AI Type (Human vs AI)")
        panel.addWidget(ai_label)

        self.ai_selector = QtWidgets.QComboBox()
        self.ai_selector.addItems(["alphabeta", "mcts"])
        self.ai_selector.currentTextChanged.connect(self.on_ai_changed)
        panel.addWidget(self.ai_selector)

        white_ai_label = QtWidgets.QLabel("White AI (AI vs AI)")
        panel.addWidget(white_ai_label)
        self.white_ai_selector = QtWidgets.QComboBox()
        self.white_ai_selector.addItems(["alphabeta", "mcts"])
        self.white_ai_selector.currentTextChanged.connect(self.on_white_ai_changed)
        panel.addWidget(self.white_ai_selector)

        black_ai_label = QtWidgets.QLabel("Black AI (AI vs AI)")
        panel.addWidget(black_ai_label)
        self.black_ai_selector = QtWidgets.QComboBox()
        self.black_ai_selector.addItems(["alphabeta", "mcts"])
        self.black_ai_selector.setCurrentText("mcts")
        self.black_ai_selector.currentTextChanged.connect(self.on_black_ai_changed)
        panel.addWidget(self.black_ai_selector)

        depth_label = QtWidgets.QLabel("Depth (Alpha-Beta)")
        panel.addWidget(depth_label)
        self.depth_slider = QtWidgets.QSlider()
        self.depth_slider.setOrientation(QtCore.Qt.Horizontal)
        self.depth_slider.setMinimum(1)
        self.depth_slider.setMaximum(5)
        self.depth_slider.setValue(self.settings.default_depth)
        self.depth_slider.valueChanged.connect(self.on_depth_changed)
        panel.addWidget(self.depth_slider)

        sim_label = QtWidgets.QLabel("Simulations (MCTS)")
        panel.addWidget(sim_label)
        self.sim_slider = QtWidgets.QSlider()
        self.sim_slider.setOrientation(QtCore.Qt.Horizontal)
        self.sim_slider.setMinimum(50)
        self.sim_slider.setMaximum(2000)
        self.sim_slider.setSingleStep(50)
        self.sim_slider.setValue(self.settings.default_simulations)
        self.sim_slider.valueChanged.connect(self.on_sim_changed)
        panel.addWidget(self.sim_slider)

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("status")
        panel.addWidget(self.status_label)

        restart_btn = QtWidgets.QPushButton("Restart")
        restart_btn.clicked.connect(self.on_restart)
        panel.addWidget(restart_btn)

        self.toggle_ai_btn = QtWidgets.QPushButton("Start AI vs AI")
        self.toggle_ai_btn.clicked.connect(self.on_toggle_ai_vs_ai)
        panel.addWidget(self.toggle_ai_btn)

        panel.addStretch(1)
        return panel

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow {{ background-color: {self.theme.app_bg}; }}
            QWidget {{ color: {self.theme.text_primary}; font-size: 13px; }}
            QLabel#title {{ font-size: 18px; font-weight: 700; color: {self.theme.text_primary}; }}
            QLabel#status {{ color: {self.theme.text_muted}; background: {self.theme.panel_bg}; padding: 8px; border-radius: 6px; }}
            QComboBox, QSlider, QPushButton {{ background: {self.theme.panel_bg}; border: 1px solid {self.theme.accent}; border-radius: 6px; padding: 6px; }}
            QPushButton:hover {{ background: {self.theme.accent}; color: #111; }}
            """
        )

    def _can_human_move(self) -> bool:
        return self.game_mode == "human_vs_ai" and not self.board.is_game_over() and self.board.turn == self.human_color

    def _current_turn_ai_name(self) -> str:
        if self.game_mode == "human_vs_ai":
            return self.active_ai
        return self.white_ai if self.board.turn == chess.WHITE else self.black_ai

    def _pick_ai_move(self):
        ai_name = self._current_turn_ai_name()
        if ai_name == "alphabeta":
            return self.alpha_beta.choose_move(self.board)
        return self.mcts.choose_move(self.board)

    def _refresh_status(self) -> None:
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            self.status_label.setText(f"Checkmate. {winner} wins.")
            return
        if self.board.is_stalemate():
            self.status_label.setText("Stalemate.")
            return
        side = "White" if self.board.turn == chess.WHITE else "Black"
        check = " (check)" if self.board.is_check() else ""
        self.status_label.setText(f"Turn: {side}{check}.")

    def _update_control_visibility(self) -> None:
        is_hva = self.game_mode == "human_vs_ai"
        self.human_side_selector.setEnabled(is_hva)
        self.ai_selector.setEnabled(is_hva)
        self.white_ai_selector.setEnabled(not is_hva)
        self.black_ai_selector.setEnabled(not is_hva)
        self.toggle_ai_btn.setEnabled(not is_hva)

    def _kick_ai_if_needed(self) -> None:
        if self.board.is_game_over():
            self.ai_timer.stop()
            self.toggle_ai_btn.setText("Start AI vs AI")
            self._refresh_status()
            return

        if self.game_mode == "human_vs_ai":
            self.ai_timer.stop()
            self.toggle_ai_btn.setText("Start AI vs AI")
            if self.board.turn != self.human_color:
                QtCore.QTimer.singleShot(self.settings.ai_turn_interval_ms, self._play_single_ai_move)

    def _play_single_ai_move(self) -> None:
        if self.board.is_game_over():
            self._refresh_status()
            return
        if self.game_mode != "human_vs_ai" or self.board.turn == self.human_color:
            return
        move = self._pick_ai_move()
        self.board.push_move(move)
        self.board_widget.update_board()
        self._refresh_status()

    def _on_ai_timer_tick(self) -> None:
        if self.game_mode != "ai_vs_ai" or self.board.is_game_over():
            self.ai_timer.stop()
            self.toggle_ai_btn.setText("Start AI vs AI")
            self._refresh_status()
            return
        move = self._pick_ai_move()
        self.board.push_move(move)
        self.board_widget.update_board()
        self._refresh_status()

    def on_ai_changed(self, value: str) -> None:
        self.active_ai = value

    def on_white_ai_changed(self, value: str) -> None:
        self.white_ai = value

    def on_black_ai_changed(self, value: str) -> None:
        self.black_ai = value

    def on_mode_changed(self, value: str) -> None:
        self.game_mode = value
        self.ai_timer.stop()
        self.toggle_ai_btn.setText("Start AI vs AI")
        self._update_control_visibility()
        self._refresh_status()
        self._kick_ai_if_needed()

    def on_human_side_changed(self, value: str) -> None:
        self.human_color = chess.WHITE if value == "white" else chess.BLACK
        self._refresh_status()
        self._kick_ai_if_needed()

    def on_depth_changed(self, value: int) -> None:
        self.alpha_beta.depth = value

    def on_sim_changed(self, value: int) -> None:
        self.mcts.simulations = value

    def on_restart(self) -> None:
        self.board.reset()
        self.board_widget.set_board(self.board)
        self._refresh_status()
        self._kick_ai_if_needed()

    def on_toggle_ai_vs_ai(self) -> None:
        if self.game_mode != "ai_vs_ai":
            return
        if self.ai_timer.isActive():
            self.ai_timer.stop()
            self.toggle_ai_btn.setText("Start AI vs AI")
            self._refresh_status()
            return
        if not self.board.is_game_over():
            self.ai_timer.start()
            self.toggle_ai_btn.setText("Stop AI vs AI")

    def on_human_move(self, move_uci: str) -> None:
        """Apply human move then trigger AI reply."""
        if not self._can_human_move():
            return
        self.board.push_uci(move_uci)
        self.board_widget.update_board()
        self._refresh_status()
        self._kick_ai_if_needed()
