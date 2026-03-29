"""Monte Carlo Tree Search implementation."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

import chess

from engine.board import Board
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
    ) -> None:
        self.simulations = simulations
        self.rollout_depth = max(1, rollout_depth)
        self.exploration = exploration

    def choose_move(self, board: Board) -> chess.Move:
        root = MCTSNode(board=board.copy(), move=None, parent=None)
        root_player = board.turn

        if root.is_terminal():
            raise ValueError("No legal moves available")

        for _ in range(self.simulations):
            leaf = self._select(root)
            child = self._expand(leaf)
            winner = self._simulate(child)
            self._backpropagate(child, winner, root_player)

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

    def _simulate(self, node: MCTSNode) -> Optional[chess.Color]:
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
            return chess.WHITE
        if result == "0-1":
            return chess.BLACK
        return None

    def _backpropagate(self, node: MCTSNode, winner: Optional[chess.Color], root_player: chess.Color) -> None:
        current = node
        while current is not None:
            current.visits += 1
            if winner is None:
                current.wins += 0.5
            elif winner == root_player:
                current.wins += 1.0
            current = current.parent
