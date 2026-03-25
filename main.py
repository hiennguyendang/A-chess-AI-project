"""
Entry point for the Chess AI project. Launches the GUI and wires game state to selected AI engines.
"""
from gui.app import ChessAIApplication
from config.settings import Settings


def main() -> None:
    """Start the Chess AI application."""
    settings = Settings()
    app = ChessAIApplication(settings=settings)
    app.run()


if __name__ == "__main__":
    main()
