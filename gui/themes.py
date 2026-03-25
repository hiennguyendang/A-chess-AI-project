"""Color palettes for the GUI."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Theme:
    light_square: str
    dark_square: str
    highlight: str
    move_hint: str
    piece_color: str
    panel_bg: str
    app_bg: str
    text_primary: str
    text_muted: str
    accent: str

    @staticmethod
    def dark() -> "Theme":
        # Colors roughly inspired by chess.com dark mode
        return Theme(
            light_square="#818D67",
            dark_square="#5A6548",
            highlight="#CCD26A",
            move_hint="#E8EC9A",
            piece_color="#F4F4F2",
            panel_bg="#232824",
            app_bg="#161A16",
            text_primary="#F1F3EE",
            text_muted="#ADB7A8",
            accent="#9FB36B",
        )
