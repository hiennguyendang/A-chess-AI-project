"""Monte Carlo Tree Search implementation."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

import chess

from ai import mcts_evaluator
from ai import search_parallel as parallel
from ai.utils import ucb1
from engine.board import Board


@dataclass
class MCTSNode:
    board: Board
    move: Optional[chess.Move]
    parent: Optional["MCTSNode"]
    children: List["MCTSNode"] = field(default_factory=list)
    untried_moves: List[chess.Move] = field(default_factory=list)
    wins: float = 0.0
    visits: int = 0

    def __post_init__(self) -> None:
        if not self.untried_moves:
            self.untried_moves = self.board.legal_chess_moves()

    def is_fully_expanded(self) -> bool:
        return len(self.untried_moves) == 0

    def is_terminal(self) -> bool:
        return self.board.is_game_over()

    def best_child(self, c_param: float, maximize_for_root: bool) -> "MCTSNode":
        parent_visits = max(1, self.visits)
        scored = []
        for child in self.children:
            mean_root_value = child.wins / max(1, child.visits)
            exploitation = mean_root_value if maximize_for_root else (1.0 - mean_root_value)
            scored.append((ucb1(exploitation, parent_visits, child.visits, c_param), child))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]


class MCTS:
    """MCTS with UCB1 selection and random rollouts."""

    def __init__(
        self,
        simulations: int = 500,
        rollout_depth: int = 200,
        exploration: float = math.sqrt(2.0),
        heuristic_scale: float = 400.0,
        use_heuristic_eval: bool = True,
        num_threads: int = 1,
        rollout_eval_mix_alpha: float = 0.35,
        use_biased_rollout: bool = True,
        rollout_mix_extra_depth: int = 6,
    ) -> None:
        self.simulations = simulations
        self.rollout_depth = max(1, rollout_depth)
        self.exploration = exploration
        self.heuristic_scale = max(1.0, heuristic_scale)
        self.use_heuristic_eval = use_heuristic_eval
        self.num_threads = max(1, num_threads)
        self.rollout_eval_mix_alpha = min(1.0, max(0.0, rollout_eval_mix_alpha))
        self.use_biased_rollout = use_biased_rollout
        self.rollout_mix_extra_depth = max(1, rollout_mix_extra_depth)

    def choose_move(self, board: Board) -> chess.Move:
        legal_moves = board.legal_chess_moves()

        if self.use_heuristic_eval:
            scripted = mcts_evaluator.scripted_castling_move(board, legal_moves)
            if scripted is not None:
                return scripted

        if parallel.should_parallelize(self.simulations, self.num_threads, len(legal_moves)):
            return self._choose_move_parallel(board)

        return self._choose_move_single(board)

    def _choose_move_single(self, board: Board) -> chess.Move:
        root = MCTSNode(board=board.copy(), move=None, parent=None)
        root_player = board.turn

        if root.is_terminal():
            raise ValueError("No legal moves available")

        for _ in range(self.simulations):
            leaf = self._select(root, root_player)
            child = self._expand(leaf, random)
            reward = self._simulate(child, root_player, random)
            self._backpropagate(child, reward)

        # pick most visited child
        if not root.children:
            raise ValueError("No legal moves available")
        best = max(root.children, key=lambda n: n.visits)
        if best.move is None:
            raise ValueError("No legal moves available")
        return best.move

    def _choose_move_parallel(self, board: Board) -> chess.Move:
        move = parallel.choose_move_parallel(
            board=board,
            simulations=self.simulations,
            num_threads=self.num_threads,
            rollout_depth=self.rollout_depth,
            exploration=self.exploration,
            heuristic_scale=self.heuristic_scale,
            use_heuristic_eval=self.use_heuristic_eval,
            rollout_eval_mix_alpha=self.rollout_eval_mix_alpha,
            use_biased_rollout=self.use_biased_rollout,
            rollout_mix_extra_depth=self.rollout_mix_extra_depth,
        )
        if move is None:
            return self._choose_move_single(board)
        return move

    def _select(self, node: MCTSNode, root_player: chess.Color) -> MCTSNode:
        current = node
        while not current.is_terminal() and current.is_fully_expanded() and current.children:
            maximize_for_root = current.board.turn == root_player
            current = current.best_child(self.exploration, maximize_for_root)
        return current

    def _expand(self, node: MCTSNode, rng: random.Random) -> MCTSNode:
        if node.is_terminal() or node.is_fully_expanded():
            return node

        move = rng.choice(node.untried_moves)
        node.untried_moves.remove(move)

        new_board = node.board.copy()
        new_board.push_move(move)
        child = MCTSNode(board=new_board, move=move, parent=node)
        node.children.append(child)
        return child

    def _simulate(self, node: MCTSNode, root_player: chess.Color, rng: random.Random) -> float:
        return mcts_evaluator.simulate_rollout_reward(
            node_board=node.board,
            root_player=root_player,
            rng=rng,
            rollout_depth=self.rollout_depth,
            use_heuristic_eval=self.use_heuristic_eval,
            heuristic_scale=self.heuristic_scale,
            rollout_eval_mix_alpha=self.rollout_eval_mix_alpha,
            rollout_mix_extra_depth=self.rollout_mix_extra_depth,
            use_biased_rollout=self.use_biased_rollout,
        )

    def _backpropagate(self, node: MCTSNode, reward: float) -> None:
        current = node
        while current is not None:
            current.visits += 1
            current.wins += reward
            current = current.parent
