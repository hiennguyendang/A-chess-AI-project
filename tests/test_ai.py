"""Smoke tests for AI components."""
import chess

from ai.alphabeta import AlphaBetaAI
from ai.mcts import MCTS
from engine.board import Board
from engine.evaluator import Evaluator


def test_alphabeta_returns_move():
    board = Board()
    ai = AlphaBetaAI(depth=1)
    move = ai.choose_move(board)
    assert isinstance(move, chess.Move)


def test_mcts_returns_move():
    board = Board()
    ai = MCTS(simulations=50)
    move = ai.choose_move(board)
    assert isinstance(move, chess.Move)


def test_board_push_and_pop_restores_state():
    board = Board()
    start_fen = board.fen()
    board.push_uci("e2e4")
    board.pop()
    assert board.fen() == start_fen


def test_evaluator_checkmate_score_sign():
    # Black to move in a checkmated position.
    board = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    score = Evaluator.evaluate(board)
    assert score > 0


def test_ai_returns_legal_move_in_middle_game():
    fen = "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 2 3"
    board = Board(fen=fen)
    ai = AlphaBetaAI(depth=2)
    move = ai.choose_move(board)
    assert move.uci() in board.legal_moves()
