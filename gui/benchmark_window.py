"""Visualization window for running multiple AI-vs-random games in parallel."""
from __future__ import annotations

import os
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List

import chess
from PyQt5 import QtCore, QtWidgets

from ai.mcts import MCTS as StandardMCTS
from ai.mcts_heuristic import MCTS as HeuristicMCTS
from ai.minimax import MinimaxAI
from config.settings import Settings
from engine.board import Board
from gui.board_ui import BoardWidget
from gui.themes import Theme


class RandomBot:
    """Simple seeded random bot used for repeatable matchups."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def choose_move(self, board: Board) -> chess.Move:
        legal = board.legal_chess_moves()
        if not legal:
            raise ValueError("No legal moves available")
        return self._rng.choice(legal)


@dataclass
class MatchView:
    board: Board
    ai_player: object
    random_bot: RandomBot
    ai_color: chess.Color
    board_widget: BoardWidget
    status_label: QtWidgets.QLabel
    plies: int = 0
    done: bool = False


class BaseBatchWindow(QtWidgets.QMainWindow):
    """Reusable window for showing 10 simultaneous AI-vs-Random games."""

    GAME_COUNT = 10
    MAX_PLIES = 200
    AI_NAME = "AI"

    def __init__(self, settings: Settings, theme: Theme) -> None:
        super().__init__()
        self.settings = settings
        self.theme = theme
        self.setWindowTitle(f"10 Games: {self.AI_NAME} vs Random")
        self.matches: List[MatchView] = []
        worker_count = max(1, os.cpu_count() or 1)
        self._executor = ThreadPoolExecutor(max_workers=worker_count)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(max(80, self.settings.ai_turn_interval_ms))
        self.timer.timeout.connect(self._tick_all_games)

        self.summary_label = QtWidgets.QLabel("Ready")
        self.start_btn = QtWidgets.QPushButton("Start")
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.reset_btn = QtWidgets.QPushButton("Reset")

        self._init_ui()
        self._apply_theme()
        self._build_matches()
        self._refresh_summary()

    def _init_ui(self) -> None:
        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout()
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        central.setLayout(root)
        self.setCentralWidget(central)

        top_row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel(f"{self.AI_NAME} vs 10 Random Bots (random side per game)")
        title.setObjectName("batch_title")
        top_row.addWidget(title)
        top_row.addStretch(1)

        self.start_btn.clicked.connect(self.start)
        self.pause_btn.clicked.connect(self.pause)
        self.reset_btn.clicked.connect(self.reset_all)

        top_row.addWidget(self.start_btn)
        top_row.addWidget(self.pause_btn)
        top_row.addWidget(self.reset_btn)
        root.addLayout(top_row)

        self.summary_label.setObjectName("batch_summary")
        root.addWidget(self.summary_label)

        self.grid = QtWidgets.QGridLayout()
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(10)
        root.addLayout(self.grid)

    def _make_ai(self):
        """Create one AI player instance for each board."""
        raise NotImplementedError("Subclasses must implement _make_ai")

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow {{ background-color: {self.theme.app_bg}; }}
            QWidget {{ color: {self.theme.text_primary}; }}
            QLabel#batch_title {{ font-size: 16px; font-weight: 700; }}
            QLabel#batch_summary {{ color: {self.theme.text_muted}; padding: 6px 8px; background: {self.theme.panel_bg}; border-radius: 6px; }}
            QPushButton {{ background: {self.theme.panel_bg}; border: 1px solid {self.theme.accent}; border-radius: 6px; padding: 6px 10px; }}
            QPushButton:hover {{ background: {self.theme.accent}; color: #111; }}
            """
        )

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _build_matches(self) -> None:
        self._clear_grid()
        self.matches.clear()

        side_rng = random.Random(2026)
        minimax_sides = [chess.WHITE] * (self.GAME_COUNT // 2) + [chess.BLACK] * (self.GAME_COUNT - (self.GAME_COUNT // 2))
        side_rng.shuffle(minimax_sides)

        for idx in range(self.GAME_COUNT):
            board = Board()
            ai_player = self._make_ai()
            random_bot = RandomBot(seed=idx)
            ai_color = minimax_sides[idx]

            container = QtWidgets.QFrame()
            box = QtWidgets.QVBoxLayout()
            box.setContentsMargins(8, 8, 8, 8)
            box.setSpacing(6)
            container.setLayout(box)

            ai_side_name = "White" if ai_color == chess.WHITE else "Black"
            title = QtWidgets.QLabel(f"Game {idx + 1} (seed={idx}) | {self.AI_NAME}: {ai_side_name}")
            box.addWidget(title)

            board_widget = BoardWidget(
                board=board,
                theme=self.theme,
                move_made_callback=lambda _move: None,
                can_human_move=lambda: False,
                min_size=200,
                coord_font_scale=0.07,
                coord_font_min=4,
            )
            box.addWidget(board_widget)

            status = QtWidgets.QLabel("Running...")
            box.addWidget(status)

            row = idx // 5
            col = idx % 5
            self.grid.addWidget(container, row, col)

            self.matches.append(
                MatchView(
                    board=board,
                    ai_player=ai_player,
                    random_bot=random_bot,
                    ai_color=ai_color,
                    board_widget=board_widget,
                    status_label=status,
                )
            )

    def _update_match_status(self, match: MatchView) -> None:
        if not match.done:
            return

        ai_side = "White" if match.ai_color == chess.WHITE else "Black"

        if match.board.is_checkmate():
            winner = "Black" if match.board.turn == chess.WHITE else "White"
            match.status_label.setText(f"Checkmate: {winner} wins | {self.AI_NAME}: {ai_side}")
            return
        if match.board.is_stalemate():
            match.status_label.setText(f"Stalemate | {self.AI_NAME}: {ai_side}")
            return
        if match.board.is_game_over():
            match.status_label.setText(f"Result: {match.board.result()} | {self.AI_NAME}: {ai_side}")
            return
        match.status_label.setText(f"Reached max plies | {self.AI_NAME}: {ai_side}")

    def _use_parallel_ai_moves(self) -> bool:
        return False

    def _apply_move(self, match: MatchView, move: chess.Move) -> None:
        match.board.push_move(move)
        match.plies += 1
        match.board_widget.update_board()

        if match.board.is_game_over() or match.plies >= self.MAX_PLIES:
            match.done = True
            self._update_match_status(match)

    def _tick_all_games(self) -> None:
        active = 0
        pending_parallel: List[MatchView] = []
        for match in self.matches:
            if match.done:
                continue

            if match.board.is_game_over() or match.plies >= self.MAX_PLIES:
                match.done = True
                self._update_match_status(match)
                continue

            is_ai_turn = match.board.turn == match.ai_color
            if is_ai_turn and self._use_parallel_ai_moves():
                pending_parallel.append(match)
                continue

            actor = match.ai_player if is_ai_turn else match.random_bot
            move = actor.choose_move(match.board)
            self._apply_move(match, move)
            if not match.done:
                active += 1

        if pending_parallel:
            futures = [
                (self._executor.submit(match.ai_player.choose_move, match.board.copy()), match)
                for match in pending_parallel
            ]
            for future, match in futures:
                move = future.result()
                self._apply_move(match, move)
                if not match.done:
                    active += 1

        if active == 0:
            for match in self.matches:
                if not match.done and not match.board.is_game_over() and match.plies < self.MAX_PLIES:
                    active = 1
                    break

        self._refresh_summary()
        if active == 0 and all(match.done for match in self.matches):
            self.timer.stop()

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self._executor.shutdown(wait=False)
        super().closeEvent(event)

    def _refresh_summary(self) -> None:
        wins = 0
        draws = 0
        losses = 0
        finished = 0
        ai_white = sum(1 for m in self.matches if m.ai_color == chess.WHITE)
        ai_black = len(self.matches) - ai_white

        for match in self.matches:
            if not match.done:
                continue
            finished += 1
            if match.board.is_checkmate():
                winner = chess.BLACK if match.board.turn == chess.WHITE else chess.WHITE
                if winner == match.ai_color:
                    wins += 1
                else:
                    losses += 1
            elif match.board.is_game_over() and match.board.result() == "1-0":
                if match.ai_color == chess.WHITE:
                    wins += 1
                else:
                    losses += 1
            elif match.board.is_game_over() and match.board.result() == "0-1":
                if match.ai_color == chess.BLACK:
                    wins += 1
                else:
                    losses += 1
            else:
                draws += 1

        self.summary_label.setText(
            f"Finished: {finished}/{self.GAME_COUNT} | {self.AI_NAME} as White: {ai_white}, Black: {ai_black} | "
            f"Wins: {wins} | Draws: {draws} | Losses: {losses}"
        )

    def start(self) -> None:
        if not self.timer.isActive():
            self.timer.start()

    def pause(self) -> None:
        self.timer.stop()

    def reset_all(self) -> None:
        self.timer.stop()
        self._build_matches()
        self._refresh_summary()


class MinimaxBatchWindow(BaseBatchWindow):
    """Show 10 simultaneous Minimax-vs-Random games in one window."""

    AI_NAME = "Minimax"

    def _make_ai(self) -> MinimaxAI:
        return MinimaxAI(depth=max(1, self.settings.default_depth))


class MCTSBatchWindow(BaseBatchWindow):
    """Show 10 simultaneous MCTS-vs-Random games in one window."""

    AI_NAME = "MCTS"

    def _use_parallel_ai_moves(self) -> bool:
        return True

    def _make_ai(self) -> StandardMCTS:
        simulations = max(1, self.settings.default_simulations)
        rollout_depth = max(1, self.settings.default_depth)
        return StandardMCTS(
            simulations=simulations,
            rollout_depth=rollout_depth,
            use_heuristic_eval=self.settings.default_mcts_use_heuristic,
            num_threads=max(1, self.settings.default_mcts_processes),
            rollout_eval_mix_alpha=self.settings.default_mcts_rollout_eval_mix_alpha,
            use_biased_rollout=self.settings.default_mcts_use_biased_rollout,
            rollout_mix_extra_depth=max(1, self.settings.default_mcts_rollout_mix_extra_depth),
            use_opening_book=self.settings.use_opening_book or self.settings.use_opening_book_mcts,
        )


class MCTSHeuristicBatchWindow(BaseBatchWindow):
    """Show 10 simultaneous MCTS-Heuristic-vs-Random games in one window."""

    AI_NAME = "MCTS Heuristic"

    def _use_parallel_ai_moves(self) -> bool:
        return True

    def _make_ai(self) -> HeuristicMCTS:
        simulations = max(1, self.settings.default_simulations)
        rollout_depth = max(1, self.settings.default_depth)
        return HeuristicMCTS(
            simulations=simulations,
            rollout_depth=rollout_depth,
            use_heuristic_eval=self.settings.default_mcts_use_heuristic,
            num_threads=max(1, self.settings.default_mcts_processes),
            rollout_eval_mix_alpha=self.settings.default_mcts_rollout_eval_mix_alpha,
            use_biased_rollout=self.settings.default_mcts_use_biased_rollout,
            rollout_mix_extra_depth=max(1, self.settings.default_mcts_rollout_mix_extra_depth),
            use_opening_book=self.settings.use_opening_book or self.settings.use_opening_book_mcts,
        )
