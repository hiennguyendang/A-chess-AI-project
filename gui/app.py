"""PyQt5 application bootstrap."""
from __future__ import annotations

import sys
from typing import List

import chess
from PyQt5 import QtCore, QtWidgets

from ai.alphabeta import AlphaBetaAI
from ai.mcts import MCTS
from config.settings import Settings
from engine.board import Board
from gui.benchmark_window import MCTSBatchWindow, MinimaxBatchWindow
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
    """Main window with layered setup flow and gameplay page."""

    GAME_HUMAN_VS_AI = "human_vs_ai"
    GAME_AI_VS_AI = "ai_vs_ai"
    GAME_TEST_AB = "test_alphabeta"
    GAME_TEST_MCTS = "test_mcts"

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.setWindowTitle("Chess AI")
        self.settings = settings
        self.theme = Theme.chesscom()

        self.board = Board()
        self.alpha_beta = AlphaBetaAI(depth=settings.default_depth)
        self.mcts = MCTS(simulations=settings.default_simulations, rollout_depth=settings.default_depth)
        self.human_color = chess.WHITE
        self.game_mode = self.GAME_HUMAN_VS_AI
        self.active_ai = "alphabeta"
        self.human_ai_depth = settings.default_depth
        self.white_ai = "alphabeta"
        self.white_ai_depth = settings.default_depth
        self.black_ai = "mcts"
        self.black_ai_depth = settings.default_depth
        self.move_history_lines: List[str] = []
        self.selected_mode = self.GAME_HUMAN_VS_AI

        self.minimax_batch_window = None
        self.mcts_batch_window = None

        self.ai_timer = QtCore.QTimer(self)
        self.ai_timer.setInterval(self.settings.ai_turn_interval_ms)
        self.ai_timer.timeout.connect(self._on_ai_timer_tick)

        self._init_ui()
        self._apply_theme()
        self._refresh_status()

    def _init_ui(self) -> None:
        self.stacked = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stacked)

        self.menu_page = self._build_menu_page()
        self.game_page = self._build_game_page()

        self.stacked.addWidget(self.menu_page)
        self.stacked.addWidget(self.game_page)
        self.stacked.setCurrentWidget(self.menu_page)

    def _build_menu_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout()
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(10)
        page.setLayout(root)

        self.setup_layers = QtWidgets.QStackedWidget()
        root.addWidget(self.setup_layers)

        self.mode_layer = self._build_mode_layer()
        self.options_layer = self._build_options_layer()

        self.setup_layers.addWidget(self.mode_layer)
        self.setup_layers.addWidget(self.options_layer)
        self.setup_layers.setCurrentWidget(self.mode_layer)
        return page

    def _build_mode_layer(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(2)
        page.setLayout(layout)

        center = QtWidgets.QFrame()
        center.setObjectName("mode_card")
        card_layout = QtWidgets.QVBoxLayout()
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(14)
        center.setLayout(card_layout)

        title = QtWidgets.QLabel("Choose Game Mode")
        title.setObjectName("menu_title")
        title.setAlignment(QtCore.Qt.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Start with one choice only. Other settings appear next.")
        subtitle.setObjectName("menu_subtitle")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        card_layout.addWidget(subtitle)

        self.menu_mode_selector = QtWidgets.QComboBox()
        self.menu_mode_selector.setObjectName("menu_mode_big")
        self.menu_mode_selector.addItem("Human vs AI", self.GAME_HUMAN_VS_AI)
        self.menu_mode_selector.addItem("AI vs AI", self.GAME_AI_VS_AI)
        self.menu_mode_selector.addItem("Test Alpha-Beta (10 games)", self.GAME_TEST_AB)
        self.menu_mode_selector.addItem("Test Monte Carlo (10 games)", self.GAME_TEST_MCTS)
        card_layout.addWidget(self.menu_mode_selector)

        continue_btn = QtWidgets.QPushButton("Continue")
        continue_btn.setObjectName("mode_continue_btn")
        continue_btn.clicked.connect(self._go_to_options_step)
        card_layout.addWidget(continue_btn)

        layout.addWidget(center, alignment=QtCore.Qt.AlignCenter)
        layout.addStretch(3)
        return page

    def _build_options_layer(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        page.setLayout(root)

        root.addStretch(1)

        card = QtWidgets.QFrame()
        card.setObjectName("options_card")
        card.setMinimumWidth(620)
        card.setMaximumWidth(760)
        card_layout = QtWidgets.QVBoxLayout()
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)
        card.setLayout(card_layout)

        top_row = QtWidgets.QHBoxLayout()
        back_btn = QtWidgets.QPushButton("Back")
        back_btn.clicked.connect(lambda: self.setup_layers.setCurrentWidget(self.mode_layer))
        top_row.addWidget(back_btn)

        self.options_title = QtWidgets.QLabel("Options")
        self.options_title.setObjectName("menu_title")
        top_row.addWidget(self.options_title)
        top_row.addStretch(1)
        card_layout.addLayout(top_row)

        self.options_hint = QtWidgets.QLabel("")
        self.options_hint.setObjectName("menu_hint")
        card_layout.addWidget(self.options_hint)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(8, 8, 8, 8)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.option_rows = {}

        self.row_depth = QtWidgets.QWidget()
        row_depth_layout = QtWidgets.QHBoxLayout()
        row_depth_layout.setContentsMargins(0, 0, 0, 0)
        self.options_depth_selector = QtWidgets.QSpinBox()
        self.options_depth_selector.setRange(1, 24)
        self.options_depth_selector.setValue(self.settings.default_depth)
        self.options_depth_selector.setSuffix(" plies")
        row_depth_layout.addWidget(self.options_depth_selector)
        self.row_depth.setLayout(row_depth_layout)
        self.label_depth = QtWidgets.QLabel("AI Depth")
        form.addRow(self.label_depth, self.row_depth)
        self.option_rows["depth"] = (self.label_depth, self.row_depth)

        self.row_side = QtWidgets.QWidget()
        row_side_layout = QtWidgets.QHBoxLayout()
        row_side_layout.setContentsMargins(0, 0, 0, 0)
        self.options_side_selector = QtWidgets.QComboBox()
        self.options_side_selector.addItem("White", "white")
        self.options_side_selector.addItem("Black", "black")
        row_side_layout.addWidget(self.options_side_selector)
        self.row_side.setLayout(row_side_layout)
        self.label_side = QtWidgets.QLabel("Your Side")
        form.addRow(self.label_side, self.row_side)
        self.option_rows["side"] = (self.label_side, self.row_side)

        self.row_ai = QtWidgets.QWidget()
        row_ai_layout = QtWidgets.QHBoxLayout()
        row_ai_layout.setContentsMargins(0, 0, 0, 0)
        self.options_ai_selector = QtWidgets.QComboBox()
        self.options_ai_selector.addItem("Alpha-Beta", "alphabeta")
        self.options_ai_selector.addItem("Monte Carlo", "mcts")
        row_ai_layout.addWidget(self.options_ai_selector)
        self.row_ai.setLayout(row_ai_layout)
        self.label_ai = QtWidgets.QLabel("AI Engine")
        form.addRow(self.label_ai, self.row_ai)
        self.option_rows["ai"] = (self.label_ai, self.row_ai)

        self.row_white_ai = QtWidgets.QWidget()
        row_white_layout = QtWidgets.QHBoxLayout()
        row_white_layout.setContentsMargins(0, 0, 0, 0)
        self.options_white_ai_selector = QtWidgets.QComboBox()
        self.options_white_ai_selector.addItem("Alpha-Beta", "alphabeta")
        self.options_white_ai_selector.addItem("Monte Carlo", "mcts")
        row_white_layout.addWidget(self.options_white_ai_selector)
        self.row_white_ai.setLayout(row_white_layout)
        self.label_white_ai = QtWidgets.QLabel("White AI")
        form.addRow(self.label_white_ai, self.row_white_ai)
        self.option_rows["white_ai"] = (self.label_white_ai, self.row_white_ai)

        self.row_white_depth = QtWidgets.QWidget()
        row_white_depth_layout = QtWidgets.QHBoxLayout()
        row_white_depth_layout.setContentsMargins(0, 0, 0, 0)
        self.options_white_depth_selector = QtWidgets.QSpinBox()
        self.options_white_depth_selector.setRange(1, 24)
        self.options_white_depth_selector.setValue(self.settings.default_depth)
        self.options_white_depth_selector.setSuffix(" plies")
        row_white_depth_layout.addWidget(self.options_white_depth_selector)
        self.row_white_depth.setLayout(row_white_depth_layout)
        self.label_white_depth = QtWidgets.QLabel("White AI Depth")
        form.addRow(self.label_white_depth, self.row_white_depth)
        self.option_rows["white_depth"] = (self.label_white_depth, self.row_white_depth)

        self.row_black_ai = QtWidgets.QWidget()
        row_black_layout = QtWidgets.QHBoxLayout()
        row_black_layout.setContentsMargins(0, 0, 0, 0)
        self.options_black_ai_selector = QtWidgets.QComboBox()
        self.options_black_ai_selector.addItem("Alpha-Beta", "alphabeta")
        self.options_black_ai_selector.addItem("Monte Carlo", "mcts")
        self.options_black_ai_selector.setCurrentText("mcts")
        row_black_layout.addWidget(self.options_black_ai_selector)
        self.row_black_ai.setLayout(row_black_layout)
        self.label_black_ai = QtWidgets.QLabel("Black AI")
        form.addRow(self.label_black_ai, self.row_black_ai)
        self.option_rows["black_ai"] = (self.label_black_ai, self.row_black_ai)

        self.row_black_depth = QtWidgets.QWidget()
        row_black_depth_layout = QtWidgets.QHBoxLayout()
        row_black_depth_layout.setContentsMargins(0, 0, 0, 0)
        self.options_black_depth_selector = QtWidgets.QSpinBox()
        self.options_black_depth_selector.setRange(1, 24)
        self.options_black_depth_selector.setValue(self.settings.default_depth)
        self.options_black_depth_selector.setSuffix(" plies")
        row_black_depth_layout.addWidget(self.options_black_depth_selector)
        self.row_black_depth.setLayout(row_black_depth_layout)
        self.label_black_depth = QtWidgets.QLabel("Black AI Depth")
        form.addRow(self.label_black_depth, self.row_black_depth)
        self.option_rows["black_depth"] = (self.label_black_depth, self.row_black_depth)

        card_layout.addLayout(form)

        action_row = QtWidgets.QHBoxLayout()
        action_row.addStretch(1)
        self.options_start_btn = QtWidgets.QPushButton("Start")
        self.options_start_btn.setMinimumWidth(180)
        self.options_start_btn.clicked.connect(self._on_start_from_options)
        action_row.addWidget(self.options_start_btn)
        action_row.addStretch(1)
        card_layout.addLayout(action_row)

        root.addWidget(card, alignment=QtCore.Qt.AlignCenter)
        root.addStretch(1)
        return page

    def _build_game_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)
        page.setLayout(layout)

        self.board_widget = BoardWidget(
            board=self.board,
            theme=self.theme,
            move_made_callback=self.on_human_move,
            can_human_move=self._can_human_move,
            min_size=640,
        )
        layout.addWidget(self.board_widget, 4)

        side_panel = QtWidgets.QVBoxLayout()
        side_panel.setSpacing(10)
        layout.addLayout(side_panel, 2)

        self.game_title_label = QtWidgets.QLabel("Game")
        self.game_title_label.setObjectName("title")
        side_panel.addWidget(self.game_title_label)

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("status")
        side_panel.addWidget(self.status_label)

        history_title = QtWidgets.QLabel("Move History")
        history_title.setObjectName("history_title")
        side_panel.addWidget(history_title)

        self.history_box = QtWidgets.QPlainTextEdit()
        self.history_box.setReadOnly(True)
        self.history_box.setObjectName("history_box")
        self.history_box.setPlaceholderText("Moves will appear here, e.g. 1. e4 e5")
        side_panel.addWidget(self.history_box, 1)

        self.toggle_ai_btn = QtWidgets.QPushButton("Start AI vs AI")
        self.toggle_ai_btn.clicked.connect(self.on_toggle_ai_vs_ai)
        side_panel.addWidget(self.toggle_ai_btn)

        restart_btn = QtWidgets.QPushButton("Restart Game")
        restart_btn.clicked.connect(self.on_restart)
        side_panel.addWidget(restart_btn)

        menu_btn = QtWidgets.QPushButton("Back To Menu")
        menu_btn.clicked.connect(self.on_back_to_menu)
        side_panel.addWidget(menu_btn)

        side_panel.addStretch(1)
        return page

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow {{ background-color: {self.theme.app_bg}; }}
            QWidget {{ color: {self.theme.text_primary}; font-size: 13px; }}
            QFrame#mode_card, QFrame#options_card {{
                background: #2A2143;
                border: 1px solid #8D7ACF;
                border-radius: 12px;
            }}
            QLabel#menu_title {{ font-size: 28px; font-weight: 700; color: {self.theme.text_primary}; }}
            QLabel#menu_subtitle {{ color: #D8D1F4; font-size: 14px; }}
            QLabel#menu_hint {{ color: #D8D1F4; background: #35295A; border: 1px solid #5F4D9A; padding: 8px; border-radius: 6px; }}
            QLabel#title {{ font-size: 18px; font-weight: 700; color: {self.theme.text_primary}; }}
            QLabel#status {{ color: {self.theme.text_muted}; background: {self.theme.panel_bg}; padding: 8px; border-radius: 6px; }}
            QLabel#history_title {{ font-size: 15px; font-weight: 600; }}
            QComboBox, QPushButton, QPlainTextEdit {{
                background: {self.theme.panel_bg};
                border: 1px solid {self.theme.accent};
                border-radius: 6px;
                padding: 6px;
            }}
            QSpinBox {{
                background: {self.theme.panel_bg};
                border: 1px solid {self.theme.accent};
                border-radius: 6px;
                padding: 6px;
            }}
            QFrame#options_card QComboBox, QFrame#options_card QSpinBox {{
                background: #ECE8FA;
                color: #281F47;
                border: 1px solid #C7B9F1;
            }}
            QFrame#options_card QComboBox QAbstractItemView {{
                background: #F2EEFF;
                color: #281F47;
                selection-background-color: #DCD1FA;
                selection-color: #281F47;
            }}
            QComboBox#menu_mode_big {{
                min-height: 54px;
                font-size: 17px;
                font-weight: 600;
                background: #ECE8FA;
                color: #281F47;
                border: 2px solid #C7B9F1;
                padding-left: 14px;
            }}
            QComboBox#menu_mode_big QAbstractItemView {{
                background: #F2EEFF;
                color: #281F47;
                selection-background-color: #DCD1FA;
                selection-color: #281F47;
            }}
            QPushButton#mode_continue_btn {{
                min-height: 50px;
                font-size: 17px;
                font-weight: 700;
                background: #7E66C8;
                color: #F7F4FF;
                border: 2px solid #B9A7F0;
             }}
             QPushButton#mode_continue_btn:hover {{ background: #6E58B2; color: #FFFFFF; }}
             QPlainTextEdit#history_box {{ font-family: Consolas; font-size: 13px; }}
             QPushButton:hover {{ background: {self.theme.accent}; color: #111; }}
             """
         )

    def _go_to_options_step(self) -> None:
        self.selected_mode = self.menu_mode_selector.currentData()
        self._update_options_for_mode(self.selected_mode)
        self.setup_layers.setCurrentWidget(self.options_layer)

    def _set_option_row_visible(self, key: str, visible: bool) -> None:
        label, widget = self.option_rows[key]
        label.setVisible(visible)
        widget.setVisible(visible)

    def _update_options_for_mode(self, mode: str) -> None:
        self.options_title.setText(f"Options - {self.menu_mode_selector.currentText()}")

        is_hva = mode == self.GAME_HUMAN_VS_AI
        is_aiva = mode == self.GAME_AI_VS_AI

        self._set_option_row_visible("depth", not is_aiva)
        self._set_option_row_visible("side", is_hva)
        self._set_option_row_visible("ai", is_hva)
        self._set_option_row_visible("white_ai", is_aiva)
        self._set_option_row_visible("white_depth", is_aiva)
        self._set_option_row_visible("black_ai", is_aiva)
        self._set_option_row_visible("black_depth", is_aiva)

        if is_hva:
            self.label_depth.setText("AI Depth")
            self.options_hint.setText("Choose side, AI engine, and depth. In game screen, only board + move history are shown.")
            self.options_start_btn.setText("Start Game")
        elif is_aiva:
            self.label_depth.setText("AI Depth")
            self.options_hint.setText("Select white/black engines and set depth separately for each AI.")
            self.options_start_btn.setText("Start Game")
        elif mode == self.GAME_TEST_AB:
            self.label_depth.setText("Alpha-Beta Depth")
            self.options_hint.setText("Open 10-board benchmark window with selected depth (Minimax vs Random).")
            self.options_start_btn.setText("Open Test")
        else:
            self.label_depth.setText("Monte Carlo Rollout Depth")
            self.options_hint.setText("Open 10-board benchmark window for Monte Carlo vs Random with real rollout depth.")
            self.options_start_btn.setText("Open Test")

    def _apply_ai_config_from_options(self) -> None:
        depth = self.options_depth_selector.value()
        sims = self._depth_to_simulations(depth)

        self.settings.default_depth = depth
        self.settings.default_simulations = sims
        self.alpha_beta.depth = depth
        self.mcts.simulations = sims
        self.mcts.rollout_depth = depth

    @staticmethod
    def _depth_to_simulations(depth: int) -> int:
        return max(120, depth * 220)

    def _on_start_from_options(self) -> None:
        mode = self.selected_mode

        if mode == self.GAME_TEST_AB:
            self._apply_ai_config_from_options()
            self.on_open_minimax_batch()
            return
        if mode == self.GAME_TEST_MCTS:
            self._apply_ai_config_from_options()
            self.on_open_mcts_batch()
            return

        self.game_mode = mode

        if mode == self.GAME_HUMAN_VS_AI:
            self._apply_ai_config_from_options()
            self.human_color = chess.WHITE if self.options_side_selector.currentData() == "white" else chess.BLACK
            self.active_ai = self.options_ai_selector.currentData()
            self.human_ai_depth = self.options_depth_selector.value()
        else:
            self.white_ai = self.options_white_ai_selector.currentData()
            self.black_ai = self.options_black_ai_selector.currentData()
            self.white_ai_depth = self.options_white_depth_selector.value()
            self.black_ai_depth = self.options_black_depth_selector.value()

        self._start_game_session()

    def _start_game_session(self) -> None:
        self.ai_timer.stop()
        self.board.reset()
        self.board_widget.set_board(self.board)
        self._clear_move_history()

        if self.game_mode == self.GAME_HUMAN_VS_AI:
            side_name = "White" if self.human_color == chess.WHITE else "Black"
            ai_name = "Alpha-Beta" if self.active_ai == "alphabeta" else "Monte Carlo"
            self.game_title_label.setText(f"Human vs AI ({ai_name}, d={self.human_ai_depth}) | You: {side_name}")
            self.toggle_ai_btn.hide()
        else:
            white_name = "Alpha-Beta" if self.white_ai == "alphabeta" else "Monte Carlo"
            black_name = "Alpha-Beta" if self.black_ai == "alphabeta" else "Monte Carlo"
            self.game_title_label.setText(
                f"AI vs AI | White: {white_name} (d={self.white_ai_depth}) | "
                f"Black: {black_name} (d={self.black_ai_depth})"
            )
            self.toggle_ai_btn.show()
            self.toggle_ai_btn.setText("Stop AI vs AI")
            self.ai_timer.start()

        self.stacked.setCurrentWidget(self.game_page)
        self._refresh_status()
        self._kick_ai_if_needed()

    def _clear_move_history(self) -> None:
        self.move_history_lines = []
        self.history_box.setPlainText("")

    def _record_move(self, move: chess.Move) -> None:
        board = self.board.to_python_chess()
        san = board.san(move)

        if board.turn == chess.WHITE:
            self.move_history_lines.append(f"{board.fullmove_number}. {san}")
        else:
            if not self.move_history_lines:
                self.move_history_lines.append(f"{board.fullmove_number}... {san}")
            else:
                self.move_history_lines[-1] = self.move_history_lines[-1] + f" {san}"

        self.history_box.setPlainText("\n".join(self.move_history_lines))
        self.history_box.verticalScrollBar().setValue(self.history_box.verticalScrollBar().maximum())

    def _can_human_move(self) -> bool:
        return self.game_mode == self.GAME_HUMAN_VS_AI and not self.board.is_game_over() and self.board.turn == self.human_color

    def _current_turn_ai_name(self) -> str:
        if self.game_mode == self.GAME_HUMAN_VS_AI:
            return self.active_ai
        return self.white_ai if self.board.turn == chess.WHITE else self.black_ai

    def _pick_ai_move(self):
        if self.game_mode == self.GAME_HUMAN_VS_AI:
            return self._pick_engine_move(self.active_ai, self.human_ai_depth)

        if self.board.turn == chess.WHITE:
            return self._pick_engine_move(self.white_ai, self.white_ai_depth)
        return self._pick_engine_move(self.black_ai, self.black_ai_depth)

    def _pick_engine_move(self, engine_name: str, depth: int):
        if engine_name == "alphabeta":
            return AlphaBetaAI(depth=max(1, depth)).choose_move(self.board)
        simulations = self._depth_to_simulations(depth)
        return MCTS(simulations=simulations, rollout_depth=max(1, depth)).choose_move(self.board)

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
        self.status_label.setText(f"Turn: {side}{check}")

    def _kick_ai_if_needed(self) -> None:
        if self.board.is_game_over():
            self.ai_timer.stop()
            if self.game_mode == self.GAME_AI_VS_AI:
                self.toggle_ai_btn.setText("Start AI vs AI")
            self._refresh_status()
            return

        if self.game_mode == self.GAME_HUMAN_VS_AI and self.board.turn != self.human_color:
            QtCore.QTimer.singleShot(self.settings.ai_turn_interval_ms, self._play_single_ai_move)

    def _play_single_ai_move(self) -> None:
        if self.board.is_game_over():
            self._refresh_status()
            return
        if self.game_mode != self.GAME_HUMAN_VS_AI or self.board.turn == self.human_color:
            return

        move = self._pick_ai_move()
        self._record_move(move)
        self.board.push_move(move)
        self.board_widget.update_board()
        self._refresh_status()

    def _on_ai_timer_tick(self) -> None:
        if self.game_mode != self.GAME_AI_VS_AI or self.board.is_game_over():
            self.ai_timer.stop()
            self.toggle_ai_btn.setText("Start AI vs AI")
            self._refresh_status()
            return

        move = self._pick_ai_move()
        self._record_move(move)
        self.board.push_move(move)
        self.board_widget.update_board()
        self._refresh_status()

    def on_toggle_ai_vs_ai(self) -> None:
        if self.game_mode != self.GAME_AI_VS_AI:
            return

        if self.ai_timer.isActive():
            self.ai_timer.stop()
            self.toggle_ai_btn.setText("Start AI vs AI")
        else:
            if not self.board.is_game_over():
                self.ai_timer.start()
                self.toggle_ai_btn.setText("Stop AI vs AI")

    def on_restart(self) -> None:
        self._start_game_session()

    def on_back_to_menu(self) -> None:
        self.ai_timer.stop()
        self.setup_layers.setCurrentWidget(self.mode_layer)
        self.stacked.setCurrentWidget(self.menu_page)

    def on_human_move(self, move_uci: str) -> None:
        """Apply human move then trigger AI reply."""
        if not self._can_human_move():
            return

        move = chess.Move.from_uci(move_uci)
        self._record_move(move)
        self.board.push_uci(move_uci)
        self.board_widget.update_board()
        self._refresh_status()
        self._kick_ai_if_needed()

    def on_open_minimax_batch(self) -> None:
        if self.minimax_batch_window is None:
            self.minimax_batch_window = MinimaxBatchWindow(settings=self.settings, theme=self.theme)
        else:
            self.minimax_batch_window.reset_all()
        self.minimax_batch_window.show()
        self.minimax_batch_window.raise_()
        self.minimax_batch_window.activateWindow()

    def on_open_mcts_batch(self) -> None:
        if self.mcts_batch_window is None:
            self.mcts_batch_window = MCTSBatchWindow(settings=self.settings, theme=self.theme)
        else:
            self.mcts_batch_window.reset_all()
        self.mcts_batch_window.show()
        self.mcts_batch_window.raise_()
        self.mcts_batch_window.activateWindow()
