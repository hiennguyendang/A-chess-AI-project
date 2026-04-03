"""Process-based parallel helpers for search engines (MCTS and Alpha-Beta)."""
from __future__ import annotations

import os
import random
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional, Tuple

import chess

from engine.board import Board
from engine.move_generator import MoveGenerator


INF_SCORE = 10_000_000
MCTSWorkerTask = Tuple[str, int, int, int, float, float, bool, float, bool, int, bool]
AlphaBetaWorkerTask = Tuple[str, str, int, bool]
MinimaxWorkerTask = Tuple[str, str, int, bool]


def should_parallelize(simulations: int, num_threads: int, legal_move_count: int) -> bool:
    if num_threads <= 1:
        return False
    if simulations < num_threads * 4:
        return False
    return legal_move_count > 1


def should_parallelize_alphabeta(depth: int, num_processes: int, legal_move_count: int) -> bool:
    if num_processes <= 1:
        return False
    if depth <= 1:
        return False
    return legal_move_count > 1


def should_parallelize_minimax(depth: int, num_processes: int, legal_move_count: int) -> bool:
    if num_processes <= 1:
        return False
    if depth <= 1:
        return False
    return legal_move_count > 1


def _run_mcts_worker_task(task: MCTSWorkerTask) -> Dict[str, Tuple[float, int]]:
    """Top-level MCTS worker entrypoint so it can be pickled on Windows spawn."""
    (
        fen,
        simulations,
        worker_id,
        rollout_depth,
        exploration,
        heuristic_scale,
        use_heuristic_eval,
        rollout_eval_mix_alpha,
        use_biased_rollout,
        rollout_mix_extra_depth,
        use_heuristic_engine,
    ) = task

    if use_heuristic_engine:
        # Local import avoids a module-level cycle with ai.mcts_heuristic importing this module.
        from ai.mcts_heuristic import MCTS, MCTSNode
    else:
        # Local import avoids a module-level cycle with ai.mcts importing this module.
        from ai.mcts import MCTS, MCTSNode

    worker_board = Board(fen=fen)
    worker = MCTS(
        simulations=simulations,
        rollout_depth=rollout_depth,
        exploration=exploration,
        heuristic_scale=heuristic_scale,
        use_heuristic_eval=use_heuristic_eval,
        num_threads=1,
        rollout_eval_mix_alpha=rollout_eval_mix_alpha,
        use_biased_rollout=use_biased_rollout,
        rollout_mix_extra_depth=rollout_mix_extra_depth,
    )

    root = MCTSNode(board=worker_board.copy(), move=None, parent=None)
    root_player = worker_board.turn
    rng = random.Random(2026 + worker_id)

    for _ in range(simulations):
        leaf = worker._select(root, root_player)
        child = worker._expand(leaf, rng)
        reward = worker._simulate(child, root_player, rng)
        worker._backpropagate(child, reward)

    result: Dict[str, Tuple[float, int]] = {}
    for child in root.children:
        if child.move is not None:
            result[child.move.uci()] = (child.wins, child.visits)
    return result


def choose_move_parallel(
    board: Board,
    simulations: int,
    num_threads: int,
    rollout_depth: int,
    exploration: float,
    heuristic_scale: float,
    use_heuristic_eval: bool,
    rollout_eval_mix_alpha: float,
    use_biased_rollout: bool,
    rollout_mix_extra_depth: int,
    use_heuristic_engine: bool = False,
) -> Optional[chess.Move]:
    legal_moves = board.legal_chess_moves()
    if not legal_moves:
        raise ValueError("No legal moves available")

    cpu_cap = max(1, os.cpu_count() or 1)
    workers = max(1, min(num_threads, cpu_cap, simulations))
    if workers <= 1:
        return None

    sims_per_worker = [simulations // workers] * workers
    for idx in range(simulations % workers):
        sims_per_worker[idx] += 1

    totals: Dict[str, List[float]] = defaultdict(lambda: [0.0, 0.0])
    fen = board.fen()
    tasks: List[MCTSWorkerTask] = [
        (
            fen,
            sims,
            idx,
            rollout_depth,
            exploration,
            heuristic_scale,
            use_heuristic_eval,
            rollout_eval_mix_alpha,
            use_biased_rollout,
            rollout_mix_extra_depth,
            use_heuristic_engine,
        )
        for idx, sims in enumerate(sims_per_worker)
        if sims > 0
    ]

    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_mcts_worker_task, task) for task in tasks]
            for future in futures:
                worker_stats = future.result()
                for move_uci, (wins, visits) in worker_stats.items():
                    totals[move_uci][0] += wins
                    totals[move_uci][1] += visits
    except Exception:
        return None

    best_move = legal_moves[0]
    best_visits = -1
    best_wins = -1.0
    for move in legal_moves:
        wins, visits = totals.get(move.uci(), [0.0, 0.0])
        visit_count = int(visits)
        if visit_count > best_visits or (visit_count == best_visits and wins > best_wins):
            best_move = move
            best_visits = visit_count
            best_wins = wins
    return best_move


def _run_alphabeta_worker_task(task: AlphaBetaWorkerTask) -> Tuple[str, int]:
    """Evaluate one root move of alpha-beta in a worker process."""
    fen, move_uci, depth, maximizing = task

    # Local import avoids a module-level cycle with ai.alphabeta importing this module.
    from ai.alphabeta import AlphaBetaAI

    worker_board = Board(fen=fen)
    worker_board.push_uci(move_uci)

    worker = AlphaBetaAI(depth=max(1, depth), num_processes=1)
    score, _ = worker._alphabeta(worker_board, depth, -INF_SCORE, INF_SCORE, maximizing)
    return move_uci, score


def choose_alphabeta_move_parallel(board: Board, depth: int, num_processes: int) -> Optional[chess.Move]:
    legal_moves = MoveGenerator().ordered_moves(board)
    if not legal_moves:
        raise ValueError("No legal moves available")

    cpu_cap = max(1, os.cpu_count() or 1)
    workers = max(1, min(num_processes, cpu_cap, len(legal_moves)))
    if workers <= 1:
        return None

    maximizing_root = board.turn == chess.WHITE
    maximizing_child = not maximizing_root
    fen = board.fen()
    tasks: List[AlphaBetaWorkerTask] = [
        (fen, move.uci(), max(0, depth - 1), maximizing_child)
        for move in legal_moves
    ]

    scores: Dict[str, int] = {}
    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_alphabeta_worker_task, task) for task in tasks]
            for future in futures:
                move_uci, score = future.result()
                scores[move_uci] = score
    except Exception:
        return None

    if not scores:
        return None

    best_move = legal_moves[0]
    best_score = scores.get(best_move.uci(), -INF_SCORE if maximizing_root else INF_SCORE)
    for move in legal_moves[1:]:
        score = scores.get(move.uci())
        if score is None:
            continue
        if maximizing_root and score > best_score:
            best_move = move
            best_score = score
        if (not maximizing_root) and score < best_score:
            best_move = move
            best_score = score

    return best_move


def _run_minimax_worker_task(task: MinimaxWorkerTask) -> Tuple[str, int]:
    """Evaluate one root move of minimax in a worker process."""
    fen, move_uci, depth, maximizing = task

    # Local import avoids module-level cycles.
    from ai.minimax import MinimaxAI

    worker_board = Board(fen=fen)
    worker_board.push_uci(move_uci)

    worker = MinimaxAI(depth=max(1, depth), num_processes=1)
    score, _ = worker._minimax(worker_board, depth, maximizing)
    return move_uci, score


def choose_minimax_move_parallel(board: Board, depth: int, num_processes: int) -> Optional[chess.Move]:
    legal_moves = MoveGenerator().ordered_moves(board)
    if not legal_moves:
        raise ValueError("No legal moves available")

    cpu_cap = max(1, os.cpu_count() or 1)
    workers = max(1, min(num_processes, cpu_cap, len(legal_moves)))
    if workers <= 1:
        return None

    maximizing_root = board.turn == chess.WHITE
    maximizing_child = not maximizing_root
    fen = board.fen()
    tasks: List[MinimaxWorkerTask] = [
        (fen, move.uci(), max(0, depth - 1), maximizing_child)
        for move in legal_moves
    ]

    scores: Dict[str, int] = {}
    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_minimax_worker_task, task) for task in tasks]
            for future in futures:
                move_uci, score = future.result()
                scores[move_uci] = score
    except Exception:
        return None

    if not scores:
        return None

    best_move = legal_moves[0]
    best_score = scores.get(best_move.uci(), -INF_SCORE if maximizing_root else INF_SCORE)
    for move in legal_moves[1:]:
        score = scores.get(move.uci())
        if score is None:
            continue
        if maximizing_root and score > best_score:
            best_move = move
            best_score = score
        if (not maximizing_root) and score < best_score:
            best_move = move
            best_score = score

    return best_move
