"""Application settings and defaults."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Settings:
    default_depth: int = 3
    default_simulations: int = 500
    default_alphabeta_processes: int = 6
    default_minimax_processes: int = 6
    default_mcts_use_heuristic: bool = True
    default_mcts_processes: int = 6
    default_mcts_rollout_eval_mix_alpha: float = 0.35
    default_mcts_use_biased_rollout: bool = True
    default_mcts_rollout_mix_extra_depth: int = 6
    ai_turn_interval_ms: int = 180
    use_opening_book: bool = False
