"""CLI tool to estimate this project bot Elo via matches against fixed-Elo UCI engines.

The tool supports two ways of entering values:
1. Command-line flags for fully automated runs.
2. Interactive prompts when you want the terminal to show fill-in spots.

Example interactive run:
  python engine/Rating_AI.py --interactive

Example non-interactive run:
  python engine/Rating_AI.py --bot alphabeta --bot-param depth=3 --opponent-path C:/engine/stockfish.exe --opponent-elo 3600
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Callable, Dict, Iterable, List, Optional

import chess
import chess.engine

try:
	from PyQt5 import QtCore, QtWidgets
except Exception:  # pragma: no cover - UI is optional when Qt is unavailable
	QtCore = None
	QtWidgets = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from ai.alphabeta import AlphaBetaAI
from ai.mcts import MCTS as StandardMCTS
from ai.mcts_heuristic import MCTS as HeuristicMCTS
from ai.minimax import MinimaxAI
from engine.board import Board
from gui.board_ui import BoardWidget
from gui.themes import Theme


@dataclass
class OpponentSpec:
	name: str
	path: Path
	elo: float


@dataclass
class MatchStats:
	wins: int = 0
	draws: int = 0
	losses: int = 0

	@property
	def total(self) -> int:
		return self.wins + self.draws + self.losses


def split_games_across_opponents(game_count: int, opponent_count: int) -> List[int]:
	if opponent_count <= 0:
		return []
	base = game_count // opponent_count
	extra = game_count % opponent_count
	return [base + (1 if index < extra else 0) for index in range(opponent_count)]


def find_stockfish_executable() -> Optional[Path]:
	stockfish_path = shutil.which("stockfish")
	if stockfish_path:
		return Path(stockfish_path)

	local_appdata = os.environ.get("LOCALAPPDATA")
	if not local_appdata:
		return None

	packages_root = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
	if not packages_root.exists():
		return None

	for exe_path in packages_root.rglob("stockfish*.exe"):
		if exe_path.is_file():
			return exe_path
	return None


def parse_opponent(raw: str) -> OpponentSpec:
	parts = raw.split("|")
	if len(parts) != 3:
		raise argparse.ArgumentTypeError("Opponent format must be: name|path_to_engine|elo")

	name, path_text, elo_text = parts
	path = Path(path_text).expanduser()
	if not path.exists():
		raise argparse.ArgumentTypeError(f"Engine path does not exist: {path}")

	try:
		e = float(elo_text)
	except ValueError as exc:
		raise argparse.ArgumentTypeError(f"Invalid Elo value: {elo_text}") from exc

	return OpponentSpec(name=name.strip(), path=path, elo=e)


def parse_value(raw: str) -> Any:
	value = raw.strip()
	lower = value.lower()
	if lower in {"true", "false"}:
		return lower == "true"
	try:
		return int(value)
	except ValueError:
		pass
	try:
		return float(value)
	except ValueError:
		pass
	return value


def elo_to_skill_level(elo: int) -> int:
	bounded = max(100, min(3200, int(elo)))
	return max(0, min(20, int(round((bounded - 100) * 20 / 3100))))


def configure_uci_strength(engine: chess.engine.SimpleEngine, requested_elo: int) -> int:
	options = engine.options
	has_limit = "UCI_LimitStrength" in options
	has_elo = "UCI_Elo" in options
	has_skill = "Skill Level" in options

	if has_elo:
		elo_option = options["UCI_Elo"]
		min_elo = getattr(elo_option, "min", None)
		max_elo = getattr(elo_option, "max", None)
		applied = int(requested_elo)
		if isinstance(min_elo, int):
			applied = max(applied, min_elo)
		if isinstance(max_elo, int):
			applied = min(applied, max_elo)

		cfg: Dict[str, Any] = {"UCI_Elo": applied}
		if has_limit:
			cfg["UCI_LimitStrength"] = True
		if has_skill and applied != int(requested_elo):
			cfg["Skill Level"] = elo_to_skill_level(int(requested_elo))
		engine.configure(cfg)
		return applied

	if has_skill:
		cfg_skill: Dict[str, Any] = {"Skill Level": elo_to_skill_level(int(requested_elo))}
		if has_limit:
			cfg_skill["UCI_LimitStrength"] = False
		engine.configure(cfg_skill)
		return int(requested_elo)

	if has_limit:
		engine.configure({"UCI_LimitStrength": False})

	raise chess.engine.EngineError("Engine does not expose UCI_Elo or Skill Level options")


def parse_key_value(raw: str) -> tuple[str, Any]:
	if "=" not in raw:
		raise argparse.ArgumentTypeError("Bot parameter must use key=value format")
	key, value = raw.split("=", 1)
	key = key.strip()
	if not key:
		raise argparse.ArgumentTypeError("Bot parameter key cannot be empty")
	return key, parse_value(value)


def prompt_text(label: str, default: Optional[str] = None) -> str:
	if default is None:
		text = input(f"{label}: ").strip()
	else:
		text = input(f"{label} [{default}]: ").strip()
	if text:
		return text
	if default is None:
		raise ValueError(f"{label} is required")
	return default


def prompt_int(label: str, default: int) -> int:
	return int(prompt_text(label, str(default)))


def prompt_float(label: str, default: float) -> float:
	return float(prompt_text(label, str(default)))


def prompt_bool(label: str, default: bool) -> bool:
	default_text = "y" if default else "n"
	text = prompt_text(f"{label} (y/n)", default_text).lower()
	if text in {"y", "yes", "true", "1"}:
		return True
	if text in {"n", "no", "false", "0"}:
		return False
	raise ValueError(f"Invalid boolean value for {label}")


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Estimate project bot Elo by playing UCI engines with known Elo."
	)
	parser.add_argument("--interactive", action="store_true", help="Prompt for values in the terminal")
	parser.add_argument("--cli", action="store_true", help="Force command-line mode instead of the UI")
	parser.add_argument("--games", type=int, default=100, help="Total games across all opponents")
	parser.add_argument(
		"--bot",
		choices=["minimax", "alphabeta", "mcts", "mcts_heuristic"],
		default=None,
		help="AI type to benchmark",
	)
	parser.add_argument(
		"--bot-param",
		action="append",
		default=[],
		metavar="KEY=VALUE",
		help="Override bot parameters, repeatable",
	)
	parser.add_argument("--depth", type=int, default=None, help="Depth for minimax/alphabeta")
	parser.add_argument("--simulations", type=int, default=None, help="Simulations for MCTS variants")
	parser.add_argument("--rollout-depth", type=int, default=None, help="Rollout depth for MCTS variants")
	parser.add_argument("--threads", type=int, default=None, help="Threads/processes for project bot")
	parser.add_argument("--exploration", type=float, default=None, help="UCB1 exploration constant")
	parser.add_argument("--heuristic-scale", type=float, default=None, help="Heuristic scaling factor for MCTS")
	parser.add_argument(
		"--rollout-eval-mix-alpha",
		type=float,
		default=None,
		help="Blend ratio for rollout evaluation",
	)
	parser.add_argument("--use-heuristic-eval", action="store_true", help="Enable heuristic eval in MCTS")
	parser.add_argument("--use-biased-rollout", action="store_true", help="Enable move-biased rollouts")
	parser.add_argument(
		"--rollout-mix-extra-depth",
		type=int,
		default=None,
		help="Extra depth used in rollout mixing",
	)
	parser.add_argument(
		"--opponent",
		action="append",
		type=parse_opponent,
		default=[],
		help="Opponent spec: name|path_to_engine|elo (repeatable)",
	)
	parser.add_argument("--opponent-path", type=str, default=None, help="Path to one UCI engine executable")
	parser.add_argument("--opponent-name", type=str, default=None, help="Optional name for --opponent-path")
	parser.add_argument("--opponent-elo", type=float, default=None, help="Elo of the opponent engine")
	parser.add_argument("--uci-move-time-ms", type=int, default=100, help="Move time for the opponent engine (ms)")
	parser.add_argument("--uci-depth", type=int, default=None, help="Optional fixed depth for the opponent engine")
	parser.add_argument("--max-plies", type=int, default=240, help="Declare draw if game exceeds this many plies")
	return parser


def get_ui_defaults(args: argparse.Namespace) -> Dict[str, Any]:
	return {
		"bot": args.bot or "alphabeta",
		"games": args.games if args.games > 0 else 100,
		"depth": args.depth if args.depth is not None else 3,
		"simulations": args.simulations if args.simulations is not None else 300,
		"rollout_depth": args.rollout_depth if args.rollout_depth is not None else 80,
		"opponent_path": args.opponent_path or str(find_stockfish_executable() or ""),
		"opponent_elo": args.opponent_elo if args.opponent_elo is not None else 3600.0,
	}


def parse_params_text(text: str) -> Dict[str, Any]:
	result: Dict[str, Any] = {}
	chunks = text.replace("\n", ",").split(",")
	for chunk in chunks:
		chunk = chunk.strip()
		if not chunk:
			continue
		key, value = parse_key_value(chunk)
		result[key] = value
	return result


def apply_overrides(base: Dict[str, Any], raw_params: List[str]) -> Dict[str, Any]:
	result = dict(base)
	for raw_param in raw_params:
		key, value = parse_key_value(raw_param)
		result[key] = value
	return result


class RatingUiDialog(QtWidgets.QDialog):
	def __init__(self, defaults: Dict[str, Any]) -> None:
		super().__init__()
		self.defaults = defaults
		self.setWindowTitle("Rating AI")
		self.resize(900, 620)
		self._thread: Optional[QtCore.QThread] = None
		self._worker: Optional[QtCore.QObject] = None
		self.preview_board = Board()
		self.preview_theme = Theme.chesscom()
		self._build_ui()

	def _build_ui(self) -> None:
		layout = QtWidgets.QVBoxLayout(self)

		title = QtWidgets.QLabel("Rating AI Benchmark")
		title.setStyleSheet("font-size: 18px; font-weight: 700;")
		layout.addWidget(title)

		form = QtWidgets.QFormLayout()
		self.bot_combo = QtWidgets.QComboBox()
		self.bot_combo.addItems(["alphabeta", "minimax", "mcts", "mcts_heuristic"])
		self.bot_combo.setCurrentText(str(self.defaults["bot"]))
		self.bot_combo.currentTextChanged.connect(self._update_parameter_visibility)
		form.addRow("Loai AI", self.bot_combo)

		self.depth_spin = QtWidgets.QSpinBox()
		self.depth_spin.setRange(1, 100)
		self.depth_spin.setValue(int(self.defaults["depth"]))
		form.addRow("AI Depth", self.depth_spin)

		self.simulations_spin = QtWidgets.QSpinBox()
		self.simulations_spin.setRange(1, 100000)
		self.simulations_spin.setValue(int(self.defaults["simulations"]))
		form.addRow("MCTS Simulations", self.simulations_spin)

		self.rollout_depth_spin = QtWidgets.QSpinBox()
		self.rollout_depth_spin.setRange(1, 1000)
		self.rollout_depth_spin.setValue(int(self.defaults["rollout_depth"]))
		form.addRow("MCTS Rollout Depth", self.rollout_depth_spin)

		self.opponent_elo_combo = QtWidgets.QComboBox()
		self.opponent_elo_combo.setEditable(True)
		for elo in [1200, 1600, 2000, 2400, 2800, 3200, 3400, 3600]:
			self.opponent_elo_combo.addItem(str(elo))
		self.opponent_elo_combo.setCurrentText(str(int(float(self.defaults["opponent_elo"]))))
		form.addRow("Elo doi thu", self.opponent_elo_combo)

		layout.addLayout(form)

		self.param_hint = QtWidgets.QLabel("Tham so hien tai se tu an/loi theo loai AI")
		self.param_hint.setStyleSheet("color: #999;")
		layout.addWidget(self.param_hint)

		content = QtWidgets.QHBoxLayout()
		content.setSpacing(12)
		layout.addLayout(content, 1)

		self.board_widget = BoardWidget(
			board=self.preview_board,
			theme=self.preview_theme,
			move_made_callback=lambda _move: None,
			can_human_move=lambda: False,
			min_size=520,
			coord_font_scale=0.07,
			coord_font_min=5,
		)
		content.addWidget(self.board_widget, 3)

		side_panel = QtWidgets.QVBoxLayout()
		content.addLayout(side_panel, 2)

		self.status_label = QtWidgets.QLabel("San sang")
		self.status_label.setWordWrap(True)
		self.status_label.setObjectName("status")
		side_panel.addWidget(self.status_label)

		history_title = QtWidgets.QLabel("Move History")
		history_title.setObjectName("history_title")
		side_panel.addWidget(history_title)

		self.history_box = QtWidgets.QPlainTextEdit()
		self.history_box.setReadOnly(True)
		self.history_box.setObjectName("history_box")
		self.history_box.setPlaceholderText("Moves will appear here")
		side_panel.addWidget(self.history_box, 1)

		right_box = QtWidgets.QGroupBox("Tien trinh va log realtime")
		right_layout = QtWidgets.QVBoxLayout(right_box)

		self.progress_label = QtWidgets.QLabel("San sang")
		right_layout.addWidget(self.progress_label)

		self.progress_bar = QtWidgets.QProgressBar()
		self.progress_bar.setRange(0, 1)
		self.progress_bar.setValue(0)
		right_layout.addWidget(self.progress_bar)

		self.output = QtWidgets.QPlainTextEdit()
		self.output.setReadOnly(True)
		self.output.setPlaceholderText("Ket qua benchmark se hien o day...")
		right_layout.addWidget(self.output, 1)
		side_panel.addWidget(right_box, 1)

		button_row = QtWidgets.QHBoxLayout()
		self.run_button = QtWidgets.QPushButton("Run")
		self.run_button.clicked.connect(self.run_benchmark)
		button_row.addWidget(self.run_button)

		self.close_button = QtWidgets.QPushButton("Close")
		self.close_button.clicked.connect(self.reject)
		button_row.addWidget(self.close_button)
		button_row.addStretch(1)
		layout.addLayout(button_row)

		self._update_parameter_visibility(self.bot_combo.currentText())

	def _update_parameter_visibility(self, bot_name: str) -> None:
		is_mcts = bot_name in {"mcts", "mcts_heuristic"}
		self.depth_spin.setVisible(not is_mcts)
		self.simulations_spin.setVisible(is_mcts)
		self.rollout_depth_spin.setVisible(is_mcts)

	def _selected_opponent_path(self) -> Path:
		path_text = str(self.defaults.get("opponent_path", "")).strip()
		if not path_text:
			raise ValueError("Khong tim thay engine doi thu. Hay cai Stockfish hoac cung cap duong dan engine.")
		path = Path(path_text).expanduser()
		if not path.exists():
			raise ValueError(f"Engine path does not exist: {path}")
		return path

	def _collect_options(self) -> tuple[str, Dict[str, Any], List[OpponentSpec], int, int, Optional[int], int]:
		bot_name = self.bot_combo.currentText().strip()
		params: Dict[str, Any] = {}
		if bot_name in {"minimax", "alphabeta"}:
			params["depth"] = int(self.depth_spin.value())
		elif bot_name in {"mcts", "mcts_heuristic"}:
			params["simulations"] = int(self.simulations_spin.value())
			params["rollout_depth"] = int(self.rollout_depth_spin.value())

		opponent_elo_text = self.opponent_elo_combo.currentText().strip()
		if not opponent_elo_text:
			raise ValueError("Hay chon Elo doi thu")
		opponent_elo = float(opponent_elo_text)
		opponent_path = self._selected_opponent_path()
		opponent = OpponentSpec(name=opponent_path.stem, path=opponent_path, elo=opponent_elo)

		return (
			bot_name,
			params,
			[opponent],
			int(self.defaults["games"]),
			int(self.defaults.get("max_plies", 240)),
			None,
			int(self.defaults.get("uci_move_time_ms", 100)),
		)

	def _set_running(self, running: bool) -> None:
		self.run_button.setEnabled(not running)
		self.bot_combo.setEnabled(not running)
		self.depth_spin.setEnabled(not running)
		self.simulations_spin.setEnabled(not running)
		self.rollout_depth_spin.setEnabled(not running)
		self.opponent_elo_combo.setEnabled(not running)

	def _finish_thread(self) -> None:
		self._worker = None
		if self._thread is not None:
			self._thread.quit()
			self._thread.wait(2000)
			self._thread = None
		self._set_running(False)

	def _on_progress(self, current: int, total: int) -> None:
		self.progress_bar.setMaximum(max(1, total))
		self.progress_bar.setValue(current)
		self.progress_label.setText(f"Progress: {current}/{total}")

	def _on_position(self, board_state: chess.Board, history_lines: List[str], game_index: int, total_games: int) -> None:
		self.preview_board = Board(fen=board_state.fen())
		self.board_widget.set_board(self.preview_board)
		self.status_label.setText(f"Game {game_index}/{total_games}<br/>{board_status_text(board_state)}")
		self.history_box.setPlainText("\n".join(history_lines))
		self.history_box.verticalScrollBar().setValue(self.history_box.verticalScrollBar().maximum())

	def _on_failed(self, message: str) -> None:
		self.output.appendPlainText(f"Error: {message}")
		self._finish_thread()

	def _on_finished(self, message: str) -> None:
		self.output.appendPlainText(message)
		self._finish_thread()

	def run_benchmark(self) -> None:
		try:
			bot_name, bot_params, opponents, games, max_plies, uci_depth, uci_move_time_ms = self._collect_options()
		except Exception as exc:
			QtWidgets.QMessageBox.critical(self, "Invalid input", str(exc))
			return

		self.output.clear()
		self.output.appendPlainText(f"Bot: {bot_name}")
		self.output.appendPlainText(f"Opponent Elo: {opponents[0].elo}")
		self.output.appendPlainText(f"Opponent engine: {opponents[0].path}")
		self._set_running(True)
		self.progress_bar.setMaximum(max(1, games))
		self.progress_bar.setValue(0)
		self.progress_label.setText(f"Progress: 0/{games}")

		worker = BenchmarkWorker(
			bot_name=bot_name,
			bot_params=bot_params,
			opponents=opponents,
			games=games,
			max_plies=max_plies,
			uci_move_time_ms=uci_move_time_ms,
			uci_depth=uci_depth,
		)
		thread = QtCore.QThread(self)
		worker.moveToThread(thread)
		thread.started.connect(worker.run)
		worker.log.connect(self.output.appendPlainText)
		worker.progress.connect(self._on_progress)
		worker.position.connect(self._on_position)
		worker.failed.connect(self._on_failed)
		worker.finished.connect(self._on_finished)
		worker.failed.connect(thread.quit)
		worker.finished.connect(thread.quit)
		thread.finished.connect(worker.deleteLater)
		thread.finished.connect(thread.deleteLater)
		self._worker = worker
		self._thread = thread
		thread.start()


class BenchmarkWorker(QtCore.QObject):
	log = QtCore.pyqtSignal(str)
	progress = QtCore.pyqtSignal(int, int)
	position = QtCore.pyqtSignal(object, object, int, int)
	failed = QtCore.pyqtSignal(str)
	finished = QtCore.pyqtSignal(str)

	def __init__(
		self,
		*,
		bot_name: str,
		bot_params: Dict[str, Any],
		opponents: List[OpponentSpec],
		games: int,
		max_plies: int,
		uci_move_time_ms: int,
		uci_depth: Optional[int],
	) -> None:
		super().__init__()
		self.bot_name = bot_name
		self.bot_params = bot_params
		self.opponents = opponents
		self.games = games
		self.max_plies = max_plies
		self.uci_move_time_ms = uci_move_time_ms
		self.uci_depth = uci_depth

	def run(self) -> None:
		try:
			project_bot = build_project_bot(self.bot_name, self.bot_params)
			global_stats = MatchStats()
			completed = 0
			games_per_opponent = split_games_across_opponents(self.games, len(self.opponents))

			for opp_index, (opponent, opponent_games) in enumerate(zip(self.opponents, games_per_opponent), start=1):
				if opponent_games <= 0:
					continue
				self.log.emit(f"=== Opponent {opp_index}/{len(self.opponents)}: {opponent.name} | Elo={opponent.elo} | Games={opponent_games} ===")
				opp_stats = MatchStats()
				with chess.engine.SimpleEngine.popen_uci(str(opponent.path)) as uci_engine:
					try:
						applied_elo = configure_uci_strength(uci_engine, int(round(opponent.elo)))
						self.log.emit(f"Configured opponent strength: requested Elo={int(round(opponent.elo))}, applied={applied_elo}")
					except chess.engine.EngineError as exc:
						self.log.emit(f"Warning: could not apply opponent Elo ({exc}); engine may play at default strength.")
					for game_idx, project_is_white in enumerate(iter_color_assignment(opponent_games), start=1):
						current_game_no = completed + 1
						outcome = run_single_game(
							project_bot=project_bot,
							uci_engine=uci_engine,
							project_is_white=project_is_white,
							max_plies=self.max_plies,
							uci_move_time_ms=self.uci_move_time_ms,
							uci_depth=self.uci_depth,
							on_position=lambda board_state, history_lines, plies, max_plies, game_no=current_game_no: self.position.emit(
								board_state,
								history_lines,
								game_no,
								self.games,
							),
						)
						update_stats(opp_stats, outcome)
						update_stats(global_stats, outcome)
						completed += 1
						self.progress.emit(completed, self.games)
						side = "White" if project_is_white else "Black"
						self.log.emit(
							f"Game {completed:03d}/{self.games} | Opponent={opponent.name} | Side={side:<5} | Result={outcome} | W/D/L={global_stats.wins}/{global_stats.draws}/{global_stats.losses}"
						)
				opp_elo = performance_elo(opponent.elo, opp_stats)
				self.log.emit(f"Summary vs {opponent.name}: W={opp_stats.wins}, D={opp_stats.draws}, L={opp_stats.losses}, N={opp_stats.total}, PerfElo={opp_elo:.2f}")

			overall_elo = performance_elo(sum(o.elo * g for o, g in zip(self.opponents, games_per_opponent)) / max(1, global_stats.total), global_stats)
			win_rate = global_stats.wins / global_stats.total if global_stats.total else 0.0
			self.finished.emit(
				f"Overall: W={global_stats.wins}, D={global_stats.draws}, L={global_stats.losses}, N={global_stats.total}, PerfElo={overall_elo:.2f}\n"
				f"Win rate: {100.0 * win_rate:.1f}%"
			)
		except Exception as exc:
			self.failed.emit(str(exc))

def launch_ui(defaults: Dict[str, Any]) -> None:
	if QtWidgets is None:
		raise RuntimeError("PyQt5 is not available in this environment")
	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
	dialog = RatingUiDialog(defaults)
	dialog.exec_()


def prompt_for_bot_and_params(args: argparse.Namespace) -> tuple[str, Dict[str, Any]]:
	bot = args.bot or prompt_text("Loai AI", "alphabeta")
	if bot not in {"minimax", "alphabeta", "mcts", "mcts_heuristic"}:
		raise ValueError(f"Unsupported bot: {bot}")

	params: Dict[str, Any] = {}
	if bot in {"minimax", "alphabeta"}:
		params["depth"] = args.depth if args.depth is not None else prompt_int("Depth", 3)
		params["threads"] = args.threads if args.threads is not None else prompt_int("Threads", 1)
	elif bot in {"mcts", "mcts_heuristic"}:
		params["simulations"] = args.simulations if args.simulations is not None else prompt_int("Simulations", 300)
		params["rollout_depth"] = args.rollout_depth if args.rollout_depth is not None else prompt_int("Rollout depth", 80)
		params["threads"] = args.threads if args.threads is not None else prompt_int("Threads", 1)
		params["exploration"] = args.exploration if args.exploration is not None else prompt_float("Exploration", 1.4142135623730951)
		params["heuristic_scale"] = args.heuristic_scale if args.heuristic_scale is not None else prompt_float("Heuristic scale", 400.0)
		params["rollout_eval_mix_alpha"] = (
			args.rollout_eval_mix_alpha if args.rollout_eval_mix_alpha is not None else prompt_float("Rollout eval mix alpha", 0.35)
		)
		params["rollout_mix_extra_depth"] = (
			args.rollout_mix_extra_depth if args.rollout_mix_extra_depth is not None else prompt_int("Rollout mix extra depth", 6)
		)
		params["use_heuristic_eval"] = bool(args.use_heuristic_eval)
		params["use_biased_rollout"] = bool(args.use_biased_rollout)

	params = apply_overrides(params, args.bot_param)
	return bot, params


def prompt_for_opponents(args: argparse.Namespace) -> List[OpponentSpec]:
	if args.opponent:
		return list(args.opponent)

	if args.opponent_path is not None and args.opponent_elo is not None:
		name = args.opponent_name or Path(args.opponent_path).stem
		path = Path(args.opponent_path).expanduser()
		if not path.exists():
			raise ValueError(f"Engine path does not exist: {path}")
		return [OpponentSpec(name=name, path=path, elo=float(args.opponent_elo))]

	path_text = prompt_text("Duong dan engine doi thu")
	elo_text = prompt_float("Elo doi thu", 3600.0)
	name = prompt_text("Ten doi thu", Path(path_text).stem)
	path = Path(path_text).expanduser()
	if not path.exists():
		raise ValueError(f"Engine path does not exist: {path}")
	return [OpponentSpec(name=name, path=path, elo=float(elo_text))]


def build_project_bot(bot_name: str, params: Dict[str, Any]):
	if bot_name == "minimax":
		return MinimaxAI(depth=max(1, int(params.get("depth", 3))), num_processes=max(1, int(params.get("threads", 1))))
	if bot_name == "alphabeta":
		return AlphaBetaAI(
			depth=max(1, int(params.get("depth", 3))),
			num_processes=max(1, int(params.get("threads", 1))),
			use_opening_book=bool(params.get("use_opening_book", False)),
		)
	if bot_name == "mcts":
		return StandardMCTS(
			simulations=max(1, int(params.get("simulations", 300))),
			rollout_depth=max(1, int(params.get("rollout_depth", 80))),
			exploration=float(params.get("exploration", 1.4142135623730951)),
			heuristic_scale=float(params.get("heuristic_scale", 400.0)),
			use_heuristic_eval=bool(params.get("use_heuristic_eval", True)),
			num_threads=max(1, int(params.get("threads", 1))),
			rollout_eval_mix_alpha=float(params.get("rollout_eval_mix_alpha", 0.35)),
			use_biased_rollout=bool(params.get("use_biased_rollout", True)),
			rollout_mix_extra_depth=max(1, int(params.get("rollout_mix_extra_depth", 6))),
			use_opening_book=bool(params.get("use_opening_book", False)),
		)
	if bot_name == "mcts_heuristic":
		return HeuristicMCTS(
			simulations=max(1, int(params.get("simulations", 300))),
			rollout_depth=max(1, int(params.get("rollout_depth", 80))),
			exploration=float(params.get("exploration", 1.4142135623730951)),
			heuristic_scale=float(params.get("heuristic_scale", 400.0)),
			use_heuristic_eval=bool(params.get("use_heuristic_eval", True)),
			num_threads=max(1, int(params.get("threads", 1))),
			rollout_eval_mix_alpha=float(params.get("rollout_eval_mix_alpha", 0.35)),
			use_biased_rollout=bool(params.get("use_biased_rollout", True)),
			rollout_mix_extra_depth=max(1, int(params.get("rollout_mix_extra_depth", 6))),
			use_opening_book=bool(params.get("use_opening_book", False)),
		)
	raise ValueError(f"Unsupported bot: {bot_name}")


def choose_project_move(bot, board: chess.Board) -> chess.Move:
	wrapped = Board(fen=board.fen())
	return bot.choose_move(wrapped)


def choose_uci_move(
	engine: chess.engine.SimpleEngine,
	board: chess.Board,
	*,
	move_time_ms: Optional[int],
	depth: Optional[int],
) -> chess.Move:
	limit_kwargs: Dict[str, float | int] = {}
	if move_time_ms is not None and move_time_ms > 0:
		limit_kwargs["time"] = move_time_ms / 1000.0
	if depth is not None and depth > 0:
		limit_kwargs["depth"] = depth
	limit = chess.engine.Limit(**limit_kwargs) if limit_kwargs else chess.engine.Limit(time=0.1)
	result = engine.play(board, limit)
	if result.move is None:
		raise RuntimeError("UCI engine returned no move")
	return result.move


def evaluate_result(board: chess.Board, project_is_white: bool) -> str:
	result = board.result(claim_draw=False)
	if result == "1-0":
		return "W" if project_is_white else "L"
	if result == "0-1":
		return "L" if project_is_white else "W"
	return "D"


def update_stats(stats: MatchStats, outcome: str) -> None:
	if outcome == "W":
		stats.wins += 1
	elif outcome == "L":
		stats.losses += 1
	else:
		stats.draws += 1


def run_single_game(
	*,
	project_bot,
	uci_engine: chess.engine.SimpleEngine,
	project_is_white: bool,
	max_plies: int,
	uci_move_time_ms: Optional[int],
	uci_depth: Optional[int],
	on_position: Optional[Callable[[chess.Board, List[str], int, int], None]] = None,
) -> str:
	board = chess.Board()
	history_lines: List[str] = []
	plies = 0
	if on_position is not None:
		on_position(board.copy(), list(history_lines), 0, max_plies)
	while not board.is_game_over(claim_draw=False) and plies < max_plies:
		project_turn = board.turn == chess.WHITE if project_is_white else board.turn == chess.BLACK
		if project_turn:
			move = choose_project_move(project_bot, board)
		else:
			move = choose_uci_move(
				uci_engine,
				board,
				move_time_ms=uci_move_time_ms,
				depth=uci_depth,
			)

		if move not in board.legal_moves:
			raise RuntimeError(f"Illegal move produced: {move.uci()}")
		append_san_history(history_lines, board, move)
		board.push(move)
		plies += 1
		if on_position is not None:
			on_position(board.copy(), list(history_lines), plies, max_plies)

	if plies >= max_plies and not board.is_game_over(claim_draw=False):
		return "D"
	return evaluate_result(board, project_is_white=project_is_white)


def performance_elo(opponent_elo: float, stats: MatchStats) -> float:
	if stats.total == 0:
		raise ValueError("Cannot compute Elo with zero games")
	return opponent_elo + 400.0 * ((stats.wins - stats.losses) / stats.total)


def iter_color_assignment(game_count: int) -> Iterable[bool]:
	white_games = game_count // 2
	black_games = game_count - white_games
	for _ in range(white_games):
		yield True
	for _ in range(black_games):
		yield False


def print_summary(title: str, stats: MatchStats, opponent_elo: float) -> None:
	elo = performance_elo(opponent_elo, stats)
	print(f"{title}: W={stats.wins}, D={stats.draws}, L={stats.losses}, N={stats.total}, PerfElo={elo:.2f}")


def board_status_text(board: chess.Board) -> str:
	if board.is_checkmate():
		winner = "Black" if board.turn == chess.WHITE else "White"
		return f"Checkmate. {winner} wins."
	if board.is_stalemate():
		return "Draw. Reason: stalemate"
	if board.is_game_over(claim_draw=False) and board.result(claim_draw=False) == "1/2-1/2":
		return "Draw."
	side = "White" if board.turn == chess.WHITE else "Black"
	check = " (check)" if board.is_check() else ""
	return f"Turn: {side}{check}"


def append_san_history(history_lines: List[str], board: chess.Board, move: chess.Move) -> None:
	san = board.san(move)
	if board.turn == chess.WHITE:
		history_lines.append(f"{board.fullmove_number}. {san}")
	else:
		if not history_lines:
			history_lines.append(f"{board.fullmove_number}... {san}")
		else:
			history_lines[-1] = history_lines[-1] + f" {san}"


def main() -> None:
	parser = build_parser()
	args = parser.parse_args()
	defaults = get_ui_defaults(args)

	if not args.cli and QtWidgets is not None:
		launch_ui(defaults)
		return

	if args.interactive or (args.bot is None and not args.opponent and args.opponent_path is None):
		print("Nhap thong tin ben duoi, nhan Enter de dung gia tri mac dinh trong ngoac.")

	bot_name, bot_params = prompt_for_bot_and_params(args)
	opponents = prompt_for_opponents(args)

	games = args.games if args.games > 0 else prompt_int("So van", 100)
	max_plies = args.max_plies if args.max_plies > 0 else prompt_int("Max plies", 240)
	uci_move_time_ms = args.uci_move_time_ms if args.uci_move_time_ms > 0 else prompt_int("Thoi gian moi nuoc doi thu (ms)", 100)
	uci_depth = args.uci_depth

	project_bot = build_project_bot(bot_name, bot_params)
	opponent = opponents[0]

	if games < 2:
		raise ValueError("Use at least 2 games to split colors")

	print(f"\n=== Bot: {bot_name} ===")
	print(f"=== Opponent: {opponent.name} | Elo={opponent.elo} | Games={games} ===")

	stats = MatchStats()
	with chess.engine.SimpleEngine.popen_uci(str(opponent.path)) as uci_engine:
		for game_idx, project_is_white in enumerate(iter_color_assignment(games), start=1):
			outcome = run_single_game(
				project_bot=project_bot,
				uci_engine=uci_engine,
				project_is_white=project_is_white,
				max_plies=max_plies,
				uci_move_time_ms=uci_move_time_ms,
				uci_depth=uci_depth,
			)
			update_stats(stats, outcome)
			side = "White" if project_is_white else "Black"
			print(f"Game {game_idx:03d}/{games} | Side={side:<5} | Result={outcome} | W/D/L={stats.wins}/{stats.draws}/{stats.losses}")

	print_summary(title="Summary", stats=stats, opponent_elo=opponent.elo)
	win_rate = stats.wins / stats.total if stats.total else 0.0
	print(f"Win rate: {100.0 * win_rate:.1f}%")
	if not 0.30 <= win_rate <= 0.70:
		print("Note: win-rate is outside 30%-70%, so this linear Performance Elo estimate may be less stable.")


if __name__ == "__main__":
	main()