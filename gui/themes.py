"""Color palettes for the GUI."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Theme:
    light_square: str
    dark_square: str
    highlight: str
    move_hint: str
    white_piece: str
    black_piece: str
    coord_light: str
    coord_dark: str
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
            white_piece="#F4F4F2",
            black_piece="#212121",
            coord_light="#DCE3CD",
            coord_dark="#4B573A",
            panel_bg="#232824",
            app_bg="#161A16",
            text_primary="#F1F3EE",
            text_muted="#ADB7A8",
            accent="#9FB36B",
        )

    @staticmethod
    def chesscom() -> "Theme":
        # Lavender-gray board palette matching the requested style.
        return Theme(
            light_square="#E2E4EA",
            dark_square="#8277B9",
            highlight="#F6F669",
            move_hint="#DDE39E",
            white_piece="#ECECDF",
            black_piece="#3A3A3A",
            coord_light="#B7AFDD",
            coord_dark="#7C73B5",
            panel_bg="#1F2A24",
            app_bg="#101713",
            text_primary="#F0F4F1",
            text_muted="#A6B6AD",
            accent="#B3C77A",
        )
