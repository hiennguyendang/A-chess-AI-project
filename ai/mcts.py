"""Monte Carlo Tree Search implementation."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

import chess

from engine.board import Board
from engine.evaluator import Evaluator
from ai.utils import ucb1


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

    def best_child(self, c_param: float) -> "MCTSNode":
        parent_visits = max(1, self.visits)
        scored = [(
            ucb1(child.wins / max(1, child.visits), parent_visits, child.visits, c_param),
            child,
        ) for child in self.children]
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
    ) -> None:
        self.simulations = simulations
        self.rollout_depth = max(1, rollout_depth)
        self.exploration = exploration
        self.heuristic_scale = max(1.0, heuristic_scale)
        self.use_heuristic_eval = use_heuristic_eval

    def choose_move(self, board: Board) -> chess.Move:
        root = MCTSNode(board=board.copy(), move=None, parent=None)
        root_player = board.turn

        if root.is_terminal():
            raise ValueError("No legal moves available")

        for _ in range(self.simulations):
            leaf = self._select(root)
            child = self._expand(leaf)
            reward = self._simulate(child, root_player)
            self._backpropagate(child, reward)

        # pick most visited child
        if not root.children:
            raise ValueError("No legal moves available")
        best = max(root.children, key=lambda n: n.visits)
        if best.move is None:
            raise ValueError("No legal moves available")
        return best.move

    def _select(self, node: MCTSNode) -> MCTSNode:
        current = node
        while not current.is_terminal() and current.is_fully_expanded() and current.children:
            current = current.best_child(self.exploration)
        return current

    def _expand(self, node: MCTSNode) -> MCTSNode:
        if node.is_terminal() or node.is_fully_expanded():
            return node

        move = random.choice(node.untried_moves)
        node.untried_moves.remove(move)

        new_board = node.board.copy()
        new_board.push_move(move)
        child = MCTSNode(board=new_board, move=move, parent=node)
        node.children.append(child)
        return child

    def _simulate(self, node: MCTSNode, root_player: chess.Color) -> float:
        rollout_board = node.board.copy()
        depth = 0
        while not rollout_board.is_game_over() and depth < self.rollout_depth:
            moves = rollout_board.legal_chess_moves()
            if not moves:
                break
            move = random.choice(moves)
            rollout_board.push_move(move)
            depth += 1

        result = rollout_board.result()
        if result == "1-0":
            return 1.0 if root_player == chess.WHITE else 0.0
        if result == "0-1":
            return 1.0 if root_player == chess.BLACK else 0.0
        if result == "1/2-1/2":
            return 0.5

        if not self.use_heuristic_eval:
            return 0.5

        # Rollout depth cutoff: use static evaluation instead of treating as draw.
        eval_cp = Evaluator.evaluate(rollout_board.to_python_chess())
        eval_for_root = eval_cp if root_player == chess.WHITE else -eval_cp
        return 0.5 + 0.5 * math.tanh(eval_for_root / self.heuristic_scale)

    def _backpropagate(self, node: MCTSNode, reward: float) -> None:
        current = node
        while current is not None:
            current.visits += 1
            current.wins += reward
            current = current.parent
