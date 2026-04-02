"""Monte Carlo Tree Search implementation."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

import chess

from ai import mcts_evaluator
from ai.opening_book import choose_italian_castling_move
from ai import search_parallel as parallel
from ai.utils import ucb1
from engine.board import Board


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

CHECK_BONUS = 60.0
CHECKMATE_BONUS = 10_000.0
PROMOTION_BONUS = {
    chess.QUEEN: 80.0,
    chess.ROOK: 45.0,
    chess.BISHOP: 35.0,
    chess.KNIGHT: 30.0,
}
DEFENDED_RISK_MULT = 0.35
UNDEFENDED_RISK_MULT = 1.0
TRADE_WEIGHT = 0.5


def _captured_piece(board: chess.Board, move: chess.Move) -> Optional[chess.Piece]:
    if not board.is_capture(move):
        return None

    if board.is_en_passant(move):
        capture_square = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        return board.piece_at(capture_square)

    return board.piece_at(move.to_square)


def _move_priority(board: chess.Board, move: chess.Move) -> float:
    next_board = board.copy()
    mover_color = board.turn
    next_board.push(move)

    moved_piece = next_board.piece_at(move.to_square)
    if moved_piece is None:
        return 0.0

    moved_value = float(PIECE_VALUES[moved_piece.piece_type])
    captured_piece = _captured_piece(board, move)
    captured_value = float(PIECE_VALUES[captured_piece.piece_type]) if captured_piece is not None else 0.0

    gain = captured_value
    if next_board.is_checkmate():
        gain += CHECKMATE_BONUS
    elif next_board.is_check():
        gain += CHECK_BONUS

    if move.promotion is not None:
        gain += max(0.0, float(PIECE_VALUES.get(move.promotion, 0)) - float(PIECE_VALUES[chess.PAWN]))

    opponent_color = next_board.turn
    attacked = bool(next_board.attackers(opponent_color, move.to_square))
    defended = bool(next_board.attackers(mover_color, move.to_square))
    risk = 0.0
    if attacked:
        risk = moved_value * (DEFENDED_RISK_MULT if defended else UNDEFENDED_RISK_MULT)

    trade_value = 0.0
    if captured_value > 0.0 and attacked:
        trade_value = (captured_value - moved_value) * TRADE_WEIGHT

    return gain + trade_value - risk


def _choose_weighted_move(board: Board, moves: List[chess.Move], rng: random.Random) -> chess.Move:
    if not moves:
        raise ValueError("No legal moves available")

    py_board = board.to_python_chess()
    scores = [_move_priority(py_board, move) for move in moves]
    min_score = min(scores)
    weights = [max(1.0, score - min_score + 1.0) for score in scores]
    return rng.choices(moves, weights=weights, k=1)[0]


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
        use_opening_book: bool = False,
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
        self.use_opening_book = use_opening_book

    def choose_move(self, board: Board) -> chess.Move:
        legal_moves = board.legal_chess_moves()

        if self.use_opening_book:
            opening_move = choose_italian_castling_move(board, legal_moves)
            if opening_move is not None:
                return opening_move

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
            use_heuristic_engine=True,
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

        move = _choose_weighted_move(node.board, node.untried_moves, rng)
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
