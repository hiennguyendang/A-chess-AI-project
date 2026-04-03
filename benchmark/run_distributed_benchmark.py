from __future__ import annotations

import argparse
import csv
import math
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import chess
import chess.engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.alphabeta import AlphaBetaAI
from ai.mcts import MCTS as StandardMCTS
from ai.mcts_heuristic import MCTS as HeuristicMCTS
from ai.minimax import MinimaxAI
from engine.board import Board
from engine.Rating_AI import configure_uci_strength, find_stockfish_executable, choose_uci_move


CSV_HEADER = [
    "game_id",
    "block_id",
    "engine_white",
    "engine_black",
    "opening_white",
    "opening_black",
    "heuristic_white",
    "heuristic_black",
    "depth_white",
    "depth_black",
    "sim_white",
    "sim_black",
    "stockfish_elo",
    "result_white",
    "result_black",
    "plies",
    "avg_move_ms_white",
    "p95_move_ms_white",
    "max_move_ms_white",
    "avg_move_ms_black",
    "p95_move_ms_black",
    "max_move_ms_black",
    "max_material_swing_cp",
    "blunder_white",
    "blunder_black",
    "white_castled_before_10",
    "black_castled_before_10",
]

PIECE_CP = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
}


@dataclass(frozen=True)
class EngineSpec:
    kind: str
    opening: str = "na"  # on/off/na
    heuristic: str = "na"  # on/off/na
    depth: Optional[int] = None
    simulations: Optional[int] = None
    rollout_depth: int = 5
    stockfish_elo: Optional[int] = None


@dataclass(frozen=True)
class MatchScenario:
    scenario_id: str
    games: int
    a: EngineSpec
    b: EngineSpec


def p95(values: List[float]) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    idx = max(0, min(len(values_sorted) - 1, math.ceil(0.95 * len(values_sorted)) - 1))
    return values_sorted[idx]


def avg(values: List[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


def material_balance_cp(board: chess.Board) -> int:
    white = 0
    black = 0
    for piece_type, cp in PIECE_CP.items():
        white += cp * len(board.pieces(piece_type, chess.WHITE))
        black += cp * len(board.pieces(piece_type, chess.BLACK))
    return white - black


def outcome_white(board: chess.Board) -> str:
    result = board.result(claim_draw=False)
    if result == "1-0":
        return "W"
    if result == "0-1":
        return "L"
    return "D"


def invert_outcome(outcome: str) -> str:
    if outcome == "W":
        return "L"
    if outcome == "L":
        return "W"
    return "D"


def format_float(v: float) -> str:
    return f"{v:.2f}"


def format_duration(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def make_bot(spec: EngineSpec, alphabeta_processes: int, minimax_processes: int, mcts_threads: int):
    if spec.kind == "alphabeta":
        return AlphaBetaAI(
            depth=max(1, int(spec.depth or 3)),
            num_processes=max(1, int(alphabeta_processes)),
            use_opening_book=(spec.opening == "on"),
        )
    if spec.kind == "minimax":
        return MinimaxAI(depth=max(1, int(spec.depth or 3)), num_processes=max(1, int(minimax_processes)))
    if spec.kind == "mcts":
        return StandardMCTS(
            simulations=max(1, int(spec.simulations or 500)),
            rollout_depth=max(1, int(spec.rollout_depth)),
            use_heuristic_eval=False,
            num_threads=max(1, int(mcts_threads)),
            use_opening_book=(spec.opening == "on"),
        )
    if spec.kind == "mcts_heuristic":
        return HeuristicMCTS(
            simulations=max(1, int(spec.simulations or 500)),
            rollout_depth=max(1, int(spec.rollout_depth)),
            use_heuristic_eval=True,
            num_threads=max(1, int(mcts_threads)),
            use_opening_book=(spec.opening == "on"),
        )
    if spec.kind in {"random", "stockfish"}:
        return None
    raise ValueError(f"Unsupported engine kind: {spec.kind}")


def choose_move(
    spec: EngineSpec,
    bot,
    board: chess.Board,
    stockfish_engine: Optional[chess.engine.SimpleEngine],
    move_time_ms: int,
) -> chess.Move:
    if spec.kind == "random":
        moves = list(board.legal_moves)
        if not moves:
            raise RuntimeError("No legal moves for random engine")
        return random.choice(moves)
    if spec.kind == "stockfish":
        if stockfish_engine is None:
            raise RuntimeError("Stockfish engine is required")
        return choose_uci_move(stockfish_engine, board, move_time_ms=move_time_ms, depth=None)
    if bot is None:
        raise RuntimeError("Bot instance is missing")
    return bot.choose_move(Board(fen=board.fen()))


def write_rows(csv_path: Path, rows: List[Dict[str, str]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def scenario_output_name(scenario_id: str) -> str:
    safe = scenario_id.replace(".", "_").replace(" ", "_")
    return f"results_{safe}.csv"


def build_all_scenarios() -> List[MatchScenario]:
    scenarios: List[MatchScenario] = []

    # I. AlphaBeta - Khong Opening
    scenarios.append(MatchScenario("I.1", 10, EngineSpec("alphabeta", opening="off", depth=3), EngineSpec("random")))
    scenarios.append(MatchScenario("I.2.d3", 10, EngineSpec("alphabeta", opening="off", depth=3), EngineSpec("minimax", depth=3)))
    scenarios.append(MatchScenario("I.2.d5", 2, EngineSpec("alphabeta", opening="off", depth=5), EngineSpec("minimax", depth=5)))
    for d in (3, 5):
        for elo in range(100, 1201, 100):
            scenarios.append(MatchScenario(f"I.3.d{d}.elo{elo}", 2, EngineSpec("alphabeta", opening="off", depth=d), EngineSpec("stockfish", stockfish_elo=elo)))

    # II. AlphaBeta - Co Opening
    scenarios.append(MatchScenario("II.1", 10, EngineSpec("alphabeta", opening="on", depth=3), EngineSpec("random")))
    scenarios.append(MatchScenario("II.2.d3", 10, EngineSpec("alphabeta", opening="on", depth=3), EngineSpec("minimax", depth=3)))
    scenarios.append(MatchScenario("II.2.d5", 2, EngineSpec("alphabeta", opening="on", depth=5), EngineSpec("minimax", depth=5)))
    for d in (3, 5):
        for elo in range(100, 1201, 100):
            scenarios.append(MatchScenario(f"II.3.d{d}.elo{elo}", 2, EngineSpec("alphabeta", opening="on", depth=d), EngineSpec("stockfish", stockfish_elo=elo)))

    # III. AlphaBeta on vs off
    scenarios.append(MatchScenario("III.d3", 10, EngineSpec("alphabeta", opening="on", depth=3), EngineSpec("alphabeta", opening="off", depth=3)))
    scenarios.append(MatchScenario("III.d5", 2, EngineSpec("alphabeta", opening="on", depth=5), EngineSpec("alphabeta", opening="off", depth=5)))

    # IV. MCTS no heuristic, no opening
    scenarios.append(MatchScenario("IV.1", 10, EngineSpec("mcts", opening="off", heuristic="off", simulations=1000, rollout_depth=5), EngineSpec("random")))
    for sim in (500, 1000, 2000):
        for elo in range(100, 1201, 100):
            scenarios.append(MatchScenario(f"IV.2.sim{sim}.elo{elo}", 2, EngineSpec("mcts", opening="off", heuristic="off", simulations=sim, rollout_depth=5), EngineSpec("stockfish", stockfish_elo=elo)))

    # V. MCTS heuristic on, opening off
    for sim in (500, 1000, 2000):
        for elo in range(100, 1201, 100):
            scenarios.append(MatchScenario(f"V.1.sim{sim}.elo{elo}", 2, EngineSpec("mcts_heuristic", opening="off", heuristic="on", simulations=sim, rollout_depth=5), EngineSpec("stockfish", stockfish_elo=elo)))

    # VI. MCTS heuristic on, opening on
    for sim in (500, 1000, 2000):
        for elo in range(100, 1201, 100):
            scenarios.append(MatchScenario(f"VI.1.sim{sim}.elo{elo}", 2, EngineSpec("mcts_heuristic", opening="on", heuristic="on", simulations=sim, rollout_depth=5), EngineSpec("stockfish", stockfish_elo=elo)))

    # VII. MCTS self-play light
    scenarios.append(MatchScenario("VII.1", 10, EngineSpec("mcts", opening="off", heuristic="off", simulations=1000, rollout_depth=5), EngineSpec("mcts_heuristic", opening="off", heuristic="on", simulations=1000, rollout_depth=5)))
    scenarios.append(MatchScenario("VII.2", 10, EngineSpec("mcts", opening="off", heuristic="off", simulations=1000, rollout_depth=5), EngineSpec("mcts", opening="on", heuristic="off", simulations=1000, rollout_depth=5)))
    scenarios.append(MatchScenario("VII.3", 10, EngineSpec("mcts_heuristic", opening="off", heuristic="on", simulations=1000, rollout_depth=5), EngineSpec("mcts_heuristic", opening="on", heuristic="on", simulations=1000, rollout_depth=5)))

    # VIII. AlphaBeta vs MCTS fixed configs
    scenarios.append(MatchScenario("VIII.1", 20, EngineSpec("alphabeta", opening="off", depth=3), EngineSpec("mcts", opening="off", heuristic="off", simulations=750, rollout_depth=5)))
    scenarios.append(MatchScenario("VIII.2", 20, EngineSpec("alphabeta", opening="off", depth=3), EngineSpec("mcts", opening="on", heuristic="off", simulations=750, rollout_depth=5)))
    scenarios.append(MatchScenario("VIII.3", 20, EngineSpec("alphabeta", opening="off", depth=3), EngineSpec("mcts_heuristic", opening="off", heuristic="on", simulations=750, rollout_depth=5)))
    scenarios.append(MatchScenario("VIII.4", 20, EngineSpec("alphabeta", opening="off", depth=3), EngineSpec("mcts_heuristic", opening="on", heuristic="on", simulations=750, rollout_depth=5)))
    scenarios.append(MatchScenario("VIII.5", 20, EngineSpec("alphabeta", opening="on", depth=3), EngineSpec("mcts_heuristic", opening="on", heuristic="on", simulations=750, rollout_depth=5)))

    return scenarios


def assign_scenarios(machine_id: str, scenarios: List[MatchScenario]) -> List[MatchScenario]:
    by_prefix: Dict[str, List[MatchScenario]] = {}
    for sc in scenarios:
        prefix = sc.scenario_id.split(".")[0]
        by_prefix.setdefault(prefix, []).append(sc)

    if machine_id == "hien":
        chosen = by_prefix.get("I", []) + by_prefix.get("V", []) + [s for s in by_prefix.get("VIII", []) if s.scenario_id == "VIII.1"]
    elif machine_id == "huy":
        chosen = by_prefix.get("II", []) + by_prefix.get("VI", []) + [s for s in by_prefix.get("VIII", []) if s.scenario_id == "VIII.2"]
    elif machine_id == "nam":
        chosen = by_prefix.get("III", []) + by_prefix.get("IV", []) + by_prefix.get("VII", []) + [s for s in by_prefix.get("VIII", []) if s.scenario_id in {"VIII.3", "VIII.4", "VIII.5"}]
    else:
        raise ValueError("machine-id must be one of: hien, huy, nam")

    return sorted(chosen, key=lambda x: x.scenario_id)


def run_scenario(
    scenario: MatchScenario,
    out_dir: Path,
    stockfish_path: Optional[Path],
    move_time_ms: int,
    max_plies: int,
    seed: int,
    alphabeta_processes: int,
    minimax_processes: int,
    mcts_threads: int,
) -> int:
    random.seed(seed)
    rows: List[Dict[str, str]] = []

    bot_a = make_bot(
        scenario.a,
        alphabeta_processes=alphabeta_processes,
        minimax_processes=minimax_processes,
        mcts_threads=mcts_threads,
    )
    bot_b = make_bot(
        scenario.b,
        alphabeta_processes=alphabeta_processes,
        minimax_processes=minimax_processes,
        mcts_threads=mcts_threads,
    )

    for game_idx in range(1, scenario.games + 1):
        # Split colors 50/50.
        a_is_white = game_idx <= (scenario.games // 2)
        white_spec = scenario.a if a_is_white else scenario.b
        black_spec = scenario.b if a_is_white else scenario.a
        white_bot = bot_a if a_is_white else bot_b
        black_bot = bot_b if a_is_white else bot_a

        board = chess.Board()
        white_times: List[float] = []
        black_times: List[float] = []
        plies = 0
        white_castled_before_10 = 0
        black_castled_before_10 = 0

        balance = material_balance_cp(board)
        min_balance = balance
        max_balance = balance

        sf_engine: Optional[chess.engine.SimpleEngine] = None
        sf_side_specs = [spec for spec in (white_spec, black_spec) if spec.kind == "stockfish"]
        sf_elo = sf_side_specs[0].stockfish_elo if sf_side_specs else None

        try:
            if sf_side_specs:
                if stockfish_path is None:
                    raise RuntimeError("Stockfish path is required for stockfish scenarios")
                sf_engine = chess.engine.SimpleEngine.popen_uci(str(stockfish_path))
                configure_uci_strength(sf_engine, int(sf_elo or 1200))

            while not board.is_game_over(claim_draw=False) and plies < max_plies:
                turn_is_white = board.turn == chess.WHITE
                spec = white_spec if turn_is_white else black_spec
                bot = white_bot if turn_is_white else black_bot
                t0 = time.perf_counter()
                move = choose_move(spec, bot, board, sf_engine, move_time_ms=move_time_ms)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0

                if move not in board.legal_moves:
                    raise RuntimeError(f"Illegal move produced: {move.uci()}")

                if turn_is_white:
                    white_times.append(elapsed_ms)
                else:
                    black_times.append(elapsed_ms)

                board.push(move)
                plies += 1

                curr_balance = material_balance_cp(board)
                min_balance = min(min_balance, curr_balance)
                max_balance = max(max_balance, curr_balance)

                if plies <= 20:
                    if not white_castled_before_10:
                        ksq_w = board.king(chess.WHITE)
                        if ksq_w in (chess.G1, chess.C1):
                            white_castled_before_10 = 1
                    if not black_castled_before_10:
                        ksq_b = board.king(chess.BLACK)
                        if ksq_b in (chess.G8, chess.C8):
                            black_castled_before_10 = 1

            result_w = outcome_white(board)
            result_b = invert_outcome(result_w)
            max_swing = max_balance - min_balance

            row = {
                "game_id": f"{scenario.scenario_id}-{game_idx:03d}",
                "block_id": scenario.scenario_id,
                "engine_white": white_spec.kind,
                "engine_black": black_spec.kind,
                "opening_white": white_spec.opening,
                "opening_black": black_spec.opening,
                "heuristic_white": white_spec.heuristic,
                "heuristic_black": black_spec.heuristic,
                "depth_white": "" if white_spec.depth is None else str(white_spec.depth),
                "depth_black": "" if black_spec.depth is None else str(black_spec.depth),
                "sim_white": "" if white_spec.simulations is None else str(white_spec.simulations),
                "sim_black": "" if black_spec.simulations is None else str(black_spec.simulations),
                "stockfish_elo": "" if sf_elo is None else str(sf_elo),
                "result_white": result_w,
                "result_black": result_b,
                "plies": str(plies),
                "avg_move_ms_white": format_float(avg(white_times)),
                "p95_move_ms_white": format_float(p95(white_times)),
                "max_move_ms_white": format_float(max(white_times) if white_times else 0.0),
                "avg_move_ms_black": format_float(avg(black_times)),
                "p95_move_ms_black": format_float(p95(black_times)),
                "max_move_ms_black": format_float(max(black_times) if black_times else 0.0),
                "max_material_swing_cp": str(int(max_swing)),
                "blunder_white": "0",
                "blunder_black": "0",
                "white_castled_before_10": str(white_castled_before_10),
                "black_castled_before_10": str(black_castled_before_10),
            }
            rows.append(row)
        finally:
            if sf_engine is not None:
                sf_engine.quit()

    out_csv = out_dir / scenario_output_name(scenario.scenario_id)
    write_rows(out_csv, rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Distributed benchmark runner for 3 machines")
    parser.add_argument("--machine-id", required=True, choices=["hien", "huy", "nam"], help="Assignment target")
    parser.add_argument("--out-dir", default="benchmark_results", help="Output directory for scenario CSV files")
    parser.add_argument("--stockfish-path", default=None, help="Path to stockfish executable (optional, auto-detect if omitted or invalid)")
    parser.add_argument("--move-time-ms", type=int, default=100, help="Stockfish move time in milliseconds")
    parser.add_argument("--max-plies", type=int, default=240, help="Max plies before draw")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--alphabeta-processes", type=int, default=6, help="Worker processes for AlphaBeta")
    parser.add_argument("--minimax-processes", type=int, default=6, help="Worker processes for Minimax")
    parser.add_argument("--mcts-threads", type=int, default=6, help="Worker threads for MCTS variants")
    args = parser.parse_args()

    out_dir = (PROJECT_ROOT / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    stockfish_path: Optional[Path] = None
    path_from_arg: Optional[Path] = None

    if args.stockfish_path:
        candidate = Path(args.stockfish_path).expanduser().resolve()
        if candidate.exists():
            path_from_arg = candidate
        else:
            print(f"[warn] Provided --stockfish-path does not exist: {candidate}")
            print("[warn] Falling back to STOCKFISH_PATH env var and auto-detection...")

    path_from_env: Optional[Path] = None
    env_raw = os.environ.get("STOCKFISH_PATH", "").strip()
    if env_raw:
        env_candidate = Path(env_raw).expanduser().resolve()
        if env_candidate.exists():
            path_from_env = env_candidate
        else:
            print(f"[warn] STOCKFISH_PATH is set but invalid: {env_candidate}")

    auto_detected = find_stockfish_executable()
    stockfish_path = path_from_arg or path_from_env or auto_detected

    if stockfish_path is None:
        raise FileNotFoundError(
            "Could not find Stockfish. Set --stockfish-path, or set STOCKFISH_PATH, "
            "or install via winget: winget install Stockfish.Stockfish"
        )

    print(f"Using Stockfish: {stockfish_path}")
    print(
        "Engine parallelism: "
        f"alphabeta_processes={max(1, args.alphabeta_processes)}, "
        f"minimax_processes={max(1, args.minimax_processes)}, "
        f"mcts_threads={max(1, args.mcts_threads)}"
    )

    scenarios = build_all_scenarios()
    assigned = assign_scenarios(args.machine_id, scenarios)

    total_games = sum(s.games for s in assigned)
    print(f"Machine={args.machine_id} | Scenarios={len(assigned)} | Planned games={total_games}")

    run_started = time.perf_counter()
    completed = 0
    for idx, sc in enumerate(assigned, start=1):
        sc_started = time.perf_counter()
        print(f"[{idx}/{len(assigned)}] Running {sc.scenario_id} ({sc.games} games)")
        n = run_scenario(
            sc,
            out_dir=out_dir,
            stockfish_path=stockfish_path,
            move_time_ms=max(1, args.move_time_ms),
            max_plies=max(20, args.max_plies),
            seed=args.seed + idx,
            alphabeta_processes=max(1, args.alphabeta_processes),
            minimax_processes=max(1, args.minimax_processes),
            mcts_threads=max(1, args.mcts_threads),
        )
        completed += n
        sc_elapsed = time.perf_counter() - sc_started
        total_elapsed = time.perf_counter() - run_started

        games_done = completed
        games_left = max(0, total_games - games_done)
        avg_sec_per_game = (total_elapsed / games_done) if games_done > 0 else 0.0
        eta_sec = avg_sec_per_game * games_left

        print(
            "  -> wrote "
            f"{n} rows | cumulative={completed} | "
            f"scenario_elapsed={format_duration(sc_elapsed)} | "
            f"total_elapsed={format_duration(total_elapsed)} | "
            f"ETA={format_duration(eta_sec)}"
        )

    total_elapsed = time.perf_counter() - run_started
    print(f"Done. Total rows written: {completed} | total_runtime={format_duration(total_elapsed)}")


if __name__ == "__main__":
    main()
