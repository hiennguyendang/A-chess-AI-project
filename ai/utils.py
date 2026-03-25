"""Common utilities for AI algorithms."""
from __future__ import annotations

import math
from typing import Optional


def ucb1(mean_reward: float, parent_visits: int, node_visits: int, c_param: float = math.sqrt(2.0)) -> float:
    """Compute UCB1 score."""
    if node_visits == 0:
        return math.inf
    exploration = c_param * math.sqrt(math.log(parent_visits) / node_visits)
    return mean_reward + exploration


def negate(score: int) -> int:
    """Negate a centipawn score for the opposing side."""
    return -score
