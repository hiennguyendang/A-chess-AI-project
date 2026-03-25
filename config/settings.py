"""Application settings and defaults."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Settings:
    default_depth: int = 3
    default_simulations: int = 500
    ai_turn_interval_ms: int = 180
    use_opening_book: bool = False
